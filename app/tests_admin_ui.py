"""Admin panel interfeysi bo'yicha regressiya testlari.

Bu yerdagi har bir test aniq bir kamchilikni qoplaydi. Kamchiliklar
brauzerda (Playwright bilan) o'lchab topilgan edi; testlar esa ular
kodga qaytib kelmasligini ta'minlaydi.
"""

from django.contrib import admin
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from app.models.auth import StudentProfile, User
from app.models.branch import Branch
from app.models.question import Course, Lesson, Module, Question
from app.models.test import TestSession


def i18n(text):
    """Savol matni uchta tilda bo'lishi majburiy (REQUIRED_LANGUAGE_CODES)."""
    return {"uz": text, "ru": text, "en": text}


def make_admin():
    return User.objects.create_superuser(
        phone_number="+998901112233",
        password="admin-review-2026",
        first_name="Shohruh",
        last_name="Abduraxmonov",
    )


class DashboardTests(TestCase):
    """Bosh sahifa haqiqiy sonlarni ko'rsatishi kerak."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = make_admin()
        cls.course = Course.objects.create(name="Python")
        cls.branch = Branch.objects.create(
            name="Chilonzor", address="Toshkent", phone="+998900000000",
            map_url="https://maps.example/1",
        )
        module = Module.objects.create(course=cls.course, name="Modul 1", order=1)
        for i in range(3):
            Lesson.objects.create(
                course=cls.course, module=module, name=f"Dars {i}", order=i
            )

    def setUp(self):
        cache.clear()
        self.client.force_login(self.admin)

    def test_dashboard_shows_real_counts_not_placeholder(self):
        """Ilgari 19 ta kartochka bir xil matnni takrorlardi."""
        html = self.client.get(reverse("admin:index")).content.decode()
        self.assertNotIn("Ma’lumotlarni ko‘rish va boshqarish", html)
        self.assertIn("3 ta dars", html)
        self.assertIn("1 ta filial", html)

    def test_dashboard_has_summary_row(self):
        html = self.client.get(reverse("admin:index")).content.decode()
        self.assertIn("pdp-kpi-row", html)
        self.assertIn("Kutayotgan buyurtma", html)

    def test_model_counts_are_cached(self):
        from app.templatetags.admin_stats import CACHE_KEY, model_counts

        self.assertIsNone(cache.get(CACHE_KEY))
        first = model_counts()
        self.assertEqual(first["app.lesson"]["value"], 3)
        # Kesh ishlayotganini tekshiramiz: yangi dars qo'shsak ham
        # eski qiymat qaytishi kerak.
        module = Module.objects.first()
        Lesson.objects.create(
            course=self.course, module=module, name="Yangi", order=9
        )
        self.assertEqual(model_counts()["app.lesson"]["value"], 3)
        cache.clear()
        self.assertEqual(model_counts()["app.lesson"]["value"], 4)

    def test_dashboard_query_count_is_bounded(self):
        """Bosh sahifa jadval soniga mutanosib so'rov qilishi kerak.

        Kartochkalar soni 20 dan ortiq, shuning uchun aniq raqamni
        qotirib qo'yish mo'rt bo'ladi; muhimi — har bir kartochka uchun
        alohida so'rovlar to'plami paydo bo'lib, N+1 ga aylanmasligi.
        Chegara: modellar soni + 15 ta xizmat so'rovi.
        """
        limit = len(admin.site._registry) + 15
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("admin:index"))
        self.assertLessEqual(
            len(ctx.captured_queries),
            limit,
            f"bosh sahifa {len(ctx.captured_queries)} ta so'rov qildi",
        )

    def test_dashboard_counts_are_not_repeated_per_card(self):
        """Ikkinchi marta ochilganda sonlar keshdan olinadi."""
        self.client.get(reverse("admin:index"))
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("admin:index"))
        # Filtrsiz `COUNT(*) FROM jadval` — aynan kartochkalar sonini
        # hisoblaydigan so'rovlar. Do'kon bildirishnomasi (bell) o'zining
        # filtrli COUNT'ini qiladi, u bu testga tegishli emas.
        counting = [
            q["sql"]
            for q in ctx.captured_queries
            if 'COUNT(*)' in q["sql"] and "WHERE" not in q["sql"]
        ]
        self.assertEqual(counting, [], "sonlar keshlanmayapti")


class ChangelistTests(TestCase):
    """Ro'yxatlarning birinchi ustuni odam o'qiy oladigan bo'lishi kerak."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = make_admin()

    def setUp(self):
        cache.clear()
        self.client.force_login(self.admin)

    def test_no_changelist_starts_with_raw_id_column(self):
        """Ilgari 11 ta ro'yxatda birinchi ustun 36 belgili UUID edi —
        u to'rt qatorga bo'linib ketardi va qatorning yagona havolasi
        aynan o'sha o'qib bo'lmaydigan matn edi."""
        offenders = []
        for model, model_admin in admin.site._registry.items():
            display = tuple(model_admin.list_display or ())
            if display and display[0] == "id":
                offenders.append(f"{model._meta.label}: {display}")
        self.assertEqual(offenders, [], "list_display 'id' bilan boshlanmasin")

    def test_id_short_renders_a_shortened_uuid(self):
        branch = Branch.objects.create(
            name="Yunusobod", address="Toshkent", phone="+998900000001",
            map_url="https://maps.example/2",
        )
        model_admin = admin.site._registry[Branch]
        html = model_admin.id_short(branch)
        self.assertIn(str(branch.pk)[:8], html)
        self.assertIn('title="%s"' % branch.pk, html)

    def test_question_preview_shows_text_not_uuid(self):
        course = Course.objects.create(name="Python")
        module = Module.objects.create(course=course, name="M1", order=1)
        lesson = Lesson.objects.create(
            course=course, module=module, name="D1", order=1
        )
        question = Question.objects.create(
            lesson=lesson,
            text=i18n("Python'da ro'yxat qanday e'lon qilinadi?"),
            options={"A": i18n("list"), "B": i18n("dict")},
            correct_option="A",
        )
        model_admin = admin.site._registry[Question]
        self.assertIn("ro'yxat", model_admin.question_preview(question))

    def test_question_preview_is_truncated(self):
        course = Course.objects.create(name="Python")
        module = Module.objects.create(course=course, name="M1", order=1)
        lesson = Lesson.objects.create(
            course=course, module=module, name="D1", order=1
        )
        question = Question.objects.create(
            lesson=lesson,
            text=i18n("S" * 200),
            options={"A": i18n("bir"), "B": i18n("ikki")},
            correct_option="A",
        )
        preview = admin.site._registry[Question].question_preview(question)
        self.assertLessEqual(len(preview), 70)
        self.assertTrue(preview.endswith("…"))


class ReadableLabelTests(TestCase):
    """Panel to'liq o'zbek tilida bo'lishi kerak."""

    def test_every_admin_field_has_a_custom_verbose_name(self):
        """`verbose_name` berilmagan maydon inglizcha nom bilan chiqadi
        (masalan "group name"). Django'ning o'z modellari (auth) bundan
        mustasno — ular tarjima fayllari orqali o'giriladi."""
        offenders = []
        for model in admin.site._registry:
            if model._meta.app_label != "app":
                continue
            for field in model._meta.get_fields():
                if not hasattr(field, "verbose_name") or not field.concrete:
                    continue
                if field.name in {"id", "groups", "user_permissions"}:
                    continue
                if str(field.verbose_name) == field.name.replace("_", " "):
                    offenders.append(f"{model._meta.label}.{field.name}")
        self.assertEqual(offenders, [], "verbose_name qo‘yilmagan maydonlar")

    def test_choice_labels_are_uzbek(self):
        self.assertEqual(User.RoleChoices.STUDENT.label, "O‘quvchi")
        self.assertEqual(dict(Branch.STATUS_CHOICES)[Branch.OPENED], "Ochiq")

    def test_project_locale_fills_django_gaps(self):
        """Django tarkibidagi `uz` lokalida bir nechta satr tarjimasiz
        qolgan; loyihaning o'z `locale/` katalogi ularni to'ldiradi."""
        with translation.override("uz"):
            self.assertEqual(translation.gettext("History"), "Tarix")
            self.assertEqual(translation.gettext("Home"), "Bosh sahifa")

    def test_model_str_is_human_readable(self):
        user = User.objects.create_user(
            phone_number="+998901234567", first_name="Ali", last_name="Valiyev",
            role=User.RoleChoices.STUDENT,
        )
        self.assertEqual(str(user), "Ali Valiyev · +998901234567")

    def test_user_str_falls_back_to_phone(self):
        user = User.objects.create_user(phone_number="+998901234568")
        self.assertEqual(str(user), "+998901234568")

    def test_test_session_str_has_no_raw_uuid_chain(self):
        course = Course.objects.create(name="Python")
        module = Module.objects.create(course=course, name="M1", order=1)
        lesson = Lesson.objects.create(
            course=course, module=module, name="D1", order=1
        )
        user = User.objects.create_user(
            phone_number="+998901234569", role=User.RoleChoices.STUDENT
        )
        profile = StudentProfile.objects.create(user=user, course=course)
        session = TestSession.objects.create(
            student=user, lesson=lesson, total_questions=1
        )
        text = str(session)
        self.assertTrue(text.startswith("Test · "), text)
        self.assertNotIn(str(profile.pk), text)


class AdminPagesRenderTests(TestCase):
    """Har bir ro'yxat sahifasi 200 qaytarishi kerak — `list_display`
    o'zgargandan keyin biror ustun buzilib qolmaganini tekshiradi."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = make_admin()

    def setUp(self):
        cache.clear()
        self.client.force_login(self.admin)

    def test_all_changelists_render(self):
        failures = []
        for model in admin.site._registry:
            opts = model._meta
            url = reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")
            response = self.client.get(url)
            if response.status_code != 200:
                failures.append(f"{opts.label}: HTTP {response.status_code}")
        self.assertEqual(failures, [])
