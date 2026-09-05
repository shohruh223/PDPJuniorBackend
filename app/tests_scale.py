"""500 foydalanuvchi yukiga tayyorgarlik bo'yicha regressiya testlari.

Har bir test aniq bir muammoni qoplaydi: agar kimdir kelajakda o'sha
naqshni qaytarib qo'ysa, test yiqiladi.
"""

from datetime import date, timedelta

from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from app.models.auth import StudentProfile, User
from app.models.branch import Branch
from app.models.coin import CoinProduct
from app.models.gallery import GalleryPost
from app.models.mentors import Mentor
from app.models.month_hero import MonthHero
from app.models.question import Course, Lesson, Module, Question
from app.models.test import TestSession, TestSessionQuestion


def make_student(index, course, branch, *, score=0):
    user = User.objects.create_user(
        phone_number=f"+9989{index:08d}",
        first_name=f"Talaba{index:03d}",
        last_name="Test",
        role=User.RoleChoices.STUDENT,
    )
    profile = StudentProfile.objects.create(
        user=user,
        course=course,
        branch=branch,
        group_name="P-1",
        api_score=score,
        total_score=score,
    )
    return user, profile


class RankingQueryCountTests(TestCase):
    """N+1: har bir o'quvchi uchun alohida mentor so'rovi bo'lmasin."""

    @classmethod
    def setUpTestData(cls):
        cls.course = Course.objects.create(name="Python")
        cls.branches = [
            Branch.objects.create(
                name=f"Filial {i}", address="a", phone="+998900000000",
                map_url="https://maps.example/x",
            )
            for i in range(5)
        ]
        for i, branch in enumerate(cls.branches):
            Mentor.objects.create(
                name=f"Mentor {i}", role="Python", branch=branch,
                exp="3", students_count="10", working_period_start=date(2024, 1, 1),
            )
        cls.students = [
            make_student(i, cls.course, cls.branches[i % 5], score=100 - i)
            for i in range(40)
        ]

    def setUp(self):
        cache.clear()

    def test_public_ranking_query_count_does_not_grow_with_students(self):
        client = APIClient()
        with CaptureQueriesContext(connection) as ctx:
            response = client.get("/api/ranking")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()["data"]["students"]), 40)
        # 40 o'quvchi uchun ham so'rovlar soni bir nechta bo'lib qolishi kerak.
        self.assertLessEqual(
            len(ctx), 6,
            f"Reyting {len(ctx)} ta so'rov bajardi — N+1 qaytib kelgan ko'rinadi.",
        )

    def test_ranking_is_served_from_cache_on_second_call(self):
        client = APIClient()
        client.get("/api/ranking")
        with CaptureQueriesContext(connection) as ctx:
            response = client.get("/api/ranking")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(ctx), 0, "Ikkinchi so'rov keshdan kelishi kerak edi.")

    def test_cached_ranking_matches_uncached(self):
        client = APIClient()
        cache.clear()
        first = client.get("/api/ranking").json()
        second = client.get("/api/ranking").json()
        self.assertEqual(first, second, "Keshlangan javob asl javobdan farq qilmasligi kerak.")

    def test_my_rank_is_computed_without_loading_everyone(self):
        user, profile = self.students[3]
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
        with CaptureQueriesContext(connection) as ctx:
            response = client.get("/api/student/ranking/me")
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            len(ctx), 12,
            f"/ranking/me {len(ctx)} ta so'rov bajardi — u 500 profilni yuklamasligi kerak.",
        )

    def test_my_rank_value_is_correct(self):
        from app.services.portal.ranking_service import get_student_rank

        # Ballari: 100, 99, 98 ... -> 0-indeks eng yuqori
        _, top = self.students[0]
        _, third = self.students[2]
        self.assertEqual(get_student_rank(top), 1)
        self.assertEqual(get_student_rank(third), 3)


class HeroesQueryCountTests(TestCase):
    """Heroes portali 12 oyni qayta hisoblab, so'rov bo'roni yaratmasin."""

    @classmethod
    def setUpTestData(cls):
        course = Course.objects.create(name="Python")
        branches = [
            Branch.objects.create(
                name=f"Filial {i}", address="a", phone="+998900000000",
                map_url="https://maps.example/x",
            )
            for i in range(4)
        ]
        for i, branch in enumerate(branches):
            Mentor.objects.create(
                name=f"Mentor {i}", role="Python", branch=branch,
                exp="3", students_count="10", working_period_start=date(2024, 1, 1),
            )
        heroes = []
        for i in range(20):
            _, profile = make_student(i, course, branches[i % 4], score=200 - i)
            for month in range(1, 7):
                heroes.append(MonthHero(student_profile=profile, period=date(2026, month, 1), points=50 - i))
        MonthHero.objects.bulk_create(heroes)

    def setUp(self):
        cache.clear()

    def test_heroes_query_count_is_bounded(self):
        client = APIClient()
        with CaptureQueriesContext(connection) as ctx:
            response = client.get("/api/heroes")
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            len(ctx), 8,
            f"Heroes {len(ctx)} ta so'rov bajardi — oy boshiga so'rov qaytgan ko'rinadi.",
        )

    def test_heroes_search_does_not_truncate_months_list(self):
        """Regressiya: qidiruv `active` ni joyida o'zgartirib, `months` ni ham kesardi."""
        client = APIClient()
        full = client.get("/api/heroes").json()["data"]
        cache.clear()
        filtered = client.get("/api/heroes?q=Talaba000").json()["data"]
        self.assertEqual(len(full["months"]), len(filtered["months"]))
        first_month = filtered["months"][0]
        self.assertTrue(
            first_month["featured"],
            "Qidiruv `months` ichidagi ma'lumotni o'chirib yubormasligi kerak.",
        )


class PaginationCompatibilityTests(TestCase):
    """Paginatsiya qo'shildi, lekin eski javob shakli saqlanishi shart."""

    @classmethod
    def setUpTestData(cls):
        course = Course.objects.create(name="Python")
        branch = Branch.objects.create(
            name="Chilonzor", address="a", phone="+998900000000",
            map_url="https://maps.example/x",
        )
        cls.user, cls.profile = make_student(1, course, branch)
        from app.models.payment import StudentPaymentHistory

        StudentPaymentHistory.objects.bulk_create([
            StudentPaymentHistory(
                student_profile=cls.profile, external_id=f"ext-{i}", amount=i,
            )
            for i in range(30)
        ])

    def setUp(self):
        self.client = APIClient()
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.user).access_token}"
        )

    def test_without_params_response_shape_is_unchanged(self):
        response = self.client.get("/api/student/payment-histories")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertNotIn("meta", body, "Paginatsiya so'ralmasa `meta` qo'shilmasligi kerak.")
        self.assertEqual(len(body["data"]), 30)

    def test_page_param_enables_pagination(self):
        response = self.client.get("/api/student/payment-histories?page=1&limit=10")
        body = response.json()
        self.assertEqual(len(body["data"]), 10)
        self.assertEqual(body["meta"]["total"], 30)
        self.assertEqual(body["meta"]["pages"], 3)
        self.assertTrue(body["meta"]["has_next"])

    def test_limit_is_capped(self):
        response = self.client.get("/api/student/payment-histories?limit=100000")
        self.assertLessEqual(len(response.json()["data"]), 500)


class ExternalSyncIsNotBlockingTests(TestCase):
    """Dashboard/to'lov endpointlari tashqi API'ni kutmasligi kerak."""

    @classmethod
    def setUpTestData(cls):
        course = Course.objects.create(name="Python")
        branch = Branch.objects.create(
            name="Chilonzor", address="a", phone="+998900000000",
            map_url="https://maps.example/x",
        )
        cls.user, cls.profile = make_student(1, course, branch)
        cls.profile.external_id = "11111111-1111-1111-1111-111111111111"
        cls.profile.pdp_access_token = "Bearer fake"
        cls.profile.last_synced_at = timezone.now()
        cls.profile.external_snapshot = {"lesson_coin": 7, "module_barchart": [{"x": 1}]}
        cls.profile.save(update_fields=[
            "external_id", "pdp_access_token", "last_synced_at", "external_snapshot",
        ])

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.user).access_token}"
        )

    def test_dashboard_serves_snapshot_without_external_call(self):
        import app.services.student.external_student_api as api

        calls = []
        original = api.PDPStudentAPIClient._get

        def spy(self, endpoint, params=None):
            calls.append(endpoint)
            raise AssertionError("Tashqi API chaqirilmasligi kerak edi!")

        api.PDPStudentAPIClient._get = spy
        try:
            response = self.client.get("/api/student/dashboard")
        finally:
            api.PDPStudentAPIClient._get = original

        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, [], "Yangi ma'lumot bo'lsa tashqi so'rov yuborilmasligi kerak.")
        self.assertEqual(response.json()["data"]["coins"]["lesson_coin"], 7)
        self.assertEqual(response.json()["data"]["module_barchart"], [{"x": 1}])

    def test_stale_data_does_not_block_the_response(self):
        """Ma'lumot eskirgan bo'lsa ham javob bazadagi nusxadan quriladi."""
        StudentProfile.objects.filter(pk=self.profile.pk).update(
            last_synced_at=timezone.now() - timedelta(days=3)
        )
        import app.services.student.external_student_api as api

        original = api.PDPStudentAPIClient._get

        def slow(self, endpoint, params=None):
            raise api.PDPStudentAPIError("PDP javob bermadi")

        api.PDPStudentAPIClient._get = slow
        try:
            response = self.client.get("/api/student/dashboard")
        finally:
            api.PDPStudentAPIClient._get = original

        self.assertEqual(response.status_code, 200, "Tashqi servis yiqilsa ham 200 qaytishi kerak.")
        self.assertEqual(response.json()["data"]["coins"]["lesson_coin"], 7)


class MaintenanceTaskTests(TestCase):
    """Ilgari ikkala vazifa ham hech qachon tugamasdi."""

    @classmethod
    def setUpTestData(cls):
        course = Course.objects.create(name="Python")
        branch = Branch.objects.create(
            name="Chilonzor", address="a", phone="+998900000000",
            map_url="https://maps.example/x",
        )
        cls.user, cls.profile = make_student(1, course, branch)
        module = Module.objects.create(course=course, name="M1", order=1)
        cls.lesson = Lesson.objects.create(course=course, module=module, name="D1", order=1)
        cls.question = Question.objects.create(
            lesson=cls.lesson,
            text={"uz": "S", "ru": "S", "en": "S"},
            options={"A": {"uz": "a", "ru": "a", "en": "a"}, "B": {"uz": "b", "ru": "b", "en": "b"}},
            correct_option="A",
        )

    def test_expire_task_does_not_recurse(self):
        """Regressiya: tasks.py oxiridagi alias vazifani o'ziga bog'lardi."""
        from app import tasks

        result = tasks.expire_stale_test_sessions_task()
        self.assertIn("expired_finalized", result)

    def test_purge_old_details_terminates(self):
        """Regressiya: sikl bir xil ID'larni qayta-qayta tanlab, cheksiz aylanardi."""
        from app.services.maintenance.cleanup_service import purge_old_test_session_details

        old = timezone.now() - timedelta(days=365)
        session = TestSession.objects.create(
            student=self.user, lesson=self.lesson, total_questions=1, is_finished=True,
        )
        TestSession.objects.filter(pk=session.pk).update(
            finished_at=old, finalized_at=old,
        )
        TestSessionQuestion.objects.create(session=session, question=self.question, order=1)

        result = purge_old_test_session_details(batch_size=10)

        self.assertEqual(result["session_questions_deleted"], 1)
        self.assertLess(result["batches"], 5, "Sikl bir necha aylanishda tugashi kerak.")
        # Sessiya summary saqlanadi
        self.assertTrue(TestSession.objects.filter(pk=session.pk).exists())

    def test_dedupe_keeps_recent_session(self):
        """Regressiya: eski dublikatlar sababli KECHAGI sessiya o'chib ketardi."""
        from app.services.maintenance.cleanup_service import dedupe_finished_test_sessions

        long_ago = timezone.now() - timedelta(days=200)
        recent = timezone.now() - timedelta(days=1)

        for stamp, percent in ((long_ago, 40), (long_ago, 50)):
            s = TestSession.objects.create(
                student=self.user, lesson=self.lesson, total_questions=1,
                is_finished=True, percent=percent,
            )
            TestSession.objects.filter(pk=s.pk).update(finished_at=stamp, finalized_at=stamp)

        newest = TestSession.objects.create(
            student=self.user, lesson=self.lesson, total_questions=1,
            is_finished=True, percent=100,
        )
        TestSession.objects.filter(pk=newest.pk).update(finished_at=recent, finalized_at=recent)

        dedupe_finished_test_sessions()

        self.assertTrue(
            TestSession.objects.filter(pk=newest.pk).exists(),
            "Yaqinda topshirilgan sessiya o'chirilmasligi kerak.",
        )


class ThrottlingTests(TestCase):
    """Rate limiting haqiqatda ishlayotganini tekshiradi."""

    def setUp(self):
        cache.clear()

    def test_sms_endpoint_is_rate_limited(self):
        # DRF `THROTTLE_RATES` ni klass atributi sifatida import paytida
        # o'qiydi, shuning uchun `override_settings` bu yerda ish bermaydi —
        # klassning o'zini vaqtincha almashtiramiz.
        from unittest.mock import patch

        from app.throttling import SmsThrottle

        client = APIClient()
        payload = {"phone_number": "+998901234567"}
        with patch.object(SmsThrottle, "THROTTLE_RATES", {"sms": "2/min"}):
            statuses = [
                client.post("/auth/forgot-password", payload, format="json").status_code
                for _ in range(5)
            ]
        self.assertIn(429, statuses, f"SMS endpointi cheklanmadi: {statuses}")
        self.assertEqual(statuses[:2].count(429), 0, "Birinchi 2 so'rov o'tishi kerak edi.")

    def test_sms_throttle_key_includes_phone_number(self):
        """Bitta IP ortidagi maktab tarmog'i bir-birini bloklamasligi kerak."""
        from unittest.mock import patch

        from app.throttling import SmsThrottle

        client = APIClient()
        with patch.object(SmsThrottle, "THROTTLE_RATES", {"sms": "2/min"}):
            for _ in range(3):
                client.post("/auth/forgot-password", {"phone_number": "+998901111111"}, format="json")
            other = client.post(
                "/auth/forgot-password", {"phone_number": "+998902222222"}, format="json"
            )
        self.assertNotEqual(
            other.status_code, 429,
            "Boshqa raqam alohida hisoblanishi kerak.",
        )

    def test_throttle_fails_open_when_cache_is_down(self):
        """Redis yiqilsa sayt to'xtamasligi kerak — so'rov o'tkaziladi."""
        from unittest.mock import patch

        from app.throttling import SmsThrottle

        client = APIClient()
        with patch.object(SmsThrottle, "THROTTLE_RATES", {"sms": "1/min"}), \
                patch("rest_framework.throttling.SimpleRateThrottle.allow_request",
                      side_effect=RuntimeError("redis down")):
            response = client.post(
                "/auth/forgot-password", {"phone_number": "+998903333333"}, format="json"
            )
        self.assertNotEqual(response.status_code, 429)
        self.assertNotEqual(response.status_code, 500)


class HealthCheckTests(TestCase):
    def test_liveness_does_not_touch_database(self):
        client = APIClient()
        with CaptureQueriesContext(connection) as ctx:
            response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(ctx), 0, "/health bazaga tegmasligi kerak.")

    def test_readiness_reports_checks(self):
        response = APIClient().get("/health/ready")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["checks"]["database"]["ok"])


class GalleryCounterTests(TestCase):
    def test_view_counter_uses_atomic_update(self):
        post = GalleryPost.objects.create(
            category={"uz": "T", "ru": "T", "en": "T"}, date="01.01.2026",
            title={"uz": "T", "ru": "T", "en": "T"},
            description={"uz": "D", "ru": "D", "en": "D"},
        )
        client = APIClient()
        for _ in range(3):
            client.get(f"/api/gallery/{post.id}/")
        post.refresh_from_db()
        self.assertEqual(post.views_count, 3)


class ProgressCacheInvalidationTests(TestCase):
    """Kurs tarkibi o'zgarsa modul qulfi keshi darhol eskirishi kerak."""

    def test_adding_a_question_bumps_the_cache_generation(self):
        from app.services.student.test_cache_service import (
            progress_generation,
            unlocked_modules_cache_key,
        )

        cache.clear()
        before_key = unlocked_modules_cache_key(1, 1)
        before = progress_generation()

        course = Course.objects.create(name="Python")
        module = Module.objects.create(course=course, name="M1", order=1)
        lesson = Lesson.objects.create(course=course, module=module, name="D1", order=1)
        Question.objects.create(
            lesson=lesson,
            text={"uz": "S", "ru": "S", "en": "S"},
            options={"A": {"uz": "a", "ru": "a", "en": "a"}, "B": {"uz": "b", "ru": "b", "en": "b"}},
            correct_option="A",
        )

        self.assertGreater(progress_generation(), before)
        self.assertNotEqual(before_key, unlocked_modules_cache_key(1, 1))


class ShopCatalogTests(TestCase):
    def test_shop_products_are_listed(self):
        course = Course.objects.create(name="Python")
        branch = Branch.objects.create(
            name="Chilonzor", address="a", phone="+998900000000",
            map_url="https://maps.example/x",
        )
        user, _ = make_student(1, course, branch)
        CoinProduct.objects.create(name="Sovg'a", description="d", price=10, stock=5)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
        response = client.get("/api/student/shop")
        self.assertEqual(response.status_code, 200)


class CourseOwnershipTests(TestCase):
    """IDOR: boshqa kursning modul/dars daraxti ko'rinmasligi kerak."""

    @classmethod
    def setUpTestData(cls):
        cls.python = Course.objects.create(name="Python")
        cls.frontend = Course.objects.create(name="Frontend")
        branch = Branch.objects.create(
            name="Chilonzor", address="a", phone="+998900000000",
            map_url="https://maps.example/x",
        )
        cls.user, cls.profile = make_student(1, cls.python, branch)

        cls.other_module = Module.objects.create(course=cls.frontend, name="Boshqa modul", order=1)
        cls.other_lesson = Lesson.objects.create(
            course=cls.frontend, module=cls.other_module, name="Boshqa dars", order=1
        )
        own_module = Module.objects.create(course=cls.python, name="O'z moduli", order=1)
        cls.own_lesson = Lesson.objects.create(
            course=cls.python, module=own_module, name="O'z darsi", order=1
        )

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.user).access_token}"
        )

    def test_other_course_module_is_forbidden(self):
        response = self.client.get(f"/api/student/modules/{self.other_module.id}/")
        self.assertEqual(response.status_code, 403)

    def test_other_course_lesson_is_forbidden(self):
        response = self.client.get(f"/api/student/lessons/{self.other_lesson.id}/")
        self.assertEqual(response.status_code, 403)

    def test_lesson_list_never_leaks_other_courses(self):
        response = self.client.get(f"/api/student/lessons?module_id={self.other_module.id}")
        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.json()["data"]["lessons"]]
        self.assertNotIn(self.other_lesson.id, ids)

    def test_own_course_still_works(self):
        response = self.client.get(f"/api/student/lessons/{self.own_lesson.id}/")
        self.assertEqual(response.status_code, 200)


class AnswerFlowTests(TestCase):
    """Muddati tugagan sessiya yakunlanishi rollback bo'lmasligi kerak."""

    @classmethod
    def setUpTestData(cls):
        course = Course.objects.create(name="Python")
        branch = Branch.objects.create(
            name="Chilonzor", address="a", phone="+998900000000",
            map_url="https://maps.example/x",
        )
        cls.user, cls.profile = make_student(1, course, branch)
        module = Module.objects.create(course=course, name="M1", order=1)
        cls.lesson = Lesson.objects.create(course=course, module=module, name="D1", order=1)
        for i in range(3):
            Question.objects.create(
                lesson=cls.lesson,
                text={"uz": f"S{i}", "ru": f"S{i}", "en": f"S{i}"},
                options={"A": {"uz": "a", "ru": "a", "en": "a"},
                         "B": {"uz": "b", "ru": "b", "en": "b"}},
                correct_option="A",
            )

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.user).access_token}"
        )

    def test_expired_session_is_actually_finished(self):
        """Regressiya: finish() ValidationError bilan orqaga qaytarilardi."""
        start = self.client.post(
            "/api/student/tests/start/", {"lesson_id": self.lesson.id}, format="json"
        )
        self.assertEqual(start.status_code, 201)
        body = start.json()
        session_id = body["session"]["session_id"]
        question_id = body["questions"][0]["question"]["id"]

        session = TestSession.objects.get(session_id=session_id)
        TestSession.objects.filter(pk=session.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )

        response = self.client.post(
            f"/api/student/tests/during/{session_id}/answer/",
            {"question_id": question_id, "selected_option": "A"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

        session.refresh_from_db()
        self.assertTrue(
            session.is_finished,
            "Muddati tugagan sessiya bazada ham yakunlangan bo'lishi kerak.",
        )
        self.assertIsNotNone(session.finalized_at)

        # Slot bo'shagani uchun yangi test boshlash mumkin
        again = self.client.post(
            "/api/student/tests/start/", {"lesson_id": self.lesson.id}, format="json"
        )
        self.assertEqual(again.status_code, 201)

    def test_answer_flow_query_count_is_bounded(self):
        start = self.client.post(
            "/api/student/tests/start/", {"lesson_id": self.lesson.id}, format="json"
        ).json()
        session_id = start["session"]["session_id"]
        qid = start["questions"][0]["question"]["id"]
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.post(
                f"/api/student/tests/during/{session_id}/answer/",
                {"question_id": qid, "selected_option": "A"},
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            len(ctx), 16,
            f"Javob yuborish {len(ctx)} ta so'rov bajardi — bu eng ko'p takrorlanadigan so'rov.",
        )


class EmptyModuleDoesNotBlockCourseTests(TestCase):
    """Regressiya: savoli yo'q modul butun kursni qulflab qo'yardi."""

    @classmethod
    def setUpTestData(cls):
        cls.course = Course.objects.create(name="Python")
        branch = Branch.objects.create(
            name="Chilonzor", address="a", phone="+998900000000",
            map_url="https://maps.example/x",
        )
        cls.user, cls.profile = make_student(1, cls.course, branch)

        # 1-modul: darsi bor, lekin savollari hali kiritilmagan
        empty_module = Module.objects.create(course=cls.course, name="Kirish", order=1)
        Lesson.objects.create(course=cls.course, module=empty_module, name="Tanishuv", order=1)

        # 2-modul: to'liq
        cls.real_module = Module.objects.create(course=cls.course, name="Asoslar", order=2)
        lesson = Lesson.objects.create(
            course=cls.course, module=cls.real_module, name="O'zgaruvchilar", order=1
        )
        Question.objects.create(
            lesson=lesson,
            text={"uz": "S", "ru": "S", "en": "S"},
            options={"A": {"uz": "a", "ru": "a", "en": "a"},
                     "B": {"uz": "b", "ru": "b", "en": "b"}},
            correct_option="A",
        )
        cls.lesson = lesson

    def setUp(self):
        cache.clear()

    def test_second_module_is_unlocked_despite_empty_first(self):
        from app.services.student.test_progress_service import get_unlocked_module_ids

        unlocked = get_unlocked_module_ids(self.user, self.course)
        self.assertIn(
            self.real_module.pk, unlocked,
            "Savolsiz birinchi modul keyingi modullarni bloklamasligi kerak.",
        )

    def test_student_can_start_a_test_in_the_second_module(self):
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.user).access_token}"
        )
        response = client.post(
            "/api/student/tests/start/", {"lesson_id": self.lesson.id}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.content[:300])


class PreResetTokenSecurityTests(TestCase):
    """Regressiya: SMS kod token ichida ochiq matnda yurardi."""

    def setUp(self):
        cache.clear()

    def test_token_does_not_contain_the_sms_code(self):
        import base64

        from app.services.password_reset_token import make_pre_reset_token

        token = make_pre_reset_token(
            phone_number="+998901234567",
            sms_code_id="abc-123",
            sms_code="987654",
        )
        self.assertNotIn("987654", token)
        self.assertNotIn("998901234567", token)

        # base64 sifatida ochib ko'rsak ham chiqmasligi kerak
        padded = token + "=" * (-len(token) % 4)
        try:
            decoded = base64.urlsafe_b64decode(padded).decode("utf-8", "ignore")
        except Exception:
            decoded = ""
        self.assertNotIn("987654", decoded)

    def test_token_is_single_use(self):
        from app.services.password_reset_token import (
            PreResetTokenError,
            make_pre_reset_token,
            parse_pre_reset_token,
        )

        token = make_pre_reset_token(
            phone_number="+998901234567", sms_code_id="a", sms_code="1"
        )
        data = parse_pre_reset_token(token, consume=True)
        self.assertEqual(data["sms_code"], "1")

        with self.assertRaises(PreResetTokenError):
            parse_pre_reset_token(token)

    def test_forged_token_is_rejected(self):
        from app.services.password_reset_token import PreResetTokenError, parse_pre_reset_token

        with self.assertRaises(PreResetTokenError):
            parse_pre_reset_token("men-oylab-topgan-token")


class LogoutTests(TestCase):
    """Ilgari logout umuman yo'q edi."""

    @classmethod
    def setUpTestData(cls):
        course = Course.objects.create(name="Python")
        branch = Branch.objects.create(
            name="Chilonzor", address="a", phone="+998900000000",
            map_url="https://maps.example/x",
        )
        cls.user, _ = make_student(1, course, branch)

    def test_refresh_token_is_blacklisted(self):
        from rest_framework_simplejwt.exceptions import TokenError

        refresh = RefreshToken.for_user(self.user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = client.post("/auth/logout", {"refresh_token": str(refresh)}, format="json")
        self.assertEqual(response.status_code, 200)

        # Bekor qilingan refresh token endi yangi access bera olmaydi
        with self.assertRaises(TokenError):
            RefreshToken(str(refresh))

    def test_logout_requires_refresh_token(self):
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.user).access_token}"
        )
        self.assertEqual(client.post("/auth/logout", {}, format="json").status_code, 400)


class DurationConsistencyTests(TestCase):
    """Regressiya: dars davomiyligi uch joyda uch xil hisoblanardi."""

    def test_single_formula_everywhere(self):
        from app.serializers.question import StudentCourseLessonsSerializer
        from app.serializers.student_lesson_tree_serializer import StudentLessonItemSerializer
        from app.serializers.test import StudentLessonItemSerializer as TestLessonSerializer
        from app.services.portal.ranking_service import serialize_lesson_item
        from app.utils.text import estimated_test_minutes

        course = Course.objects.create(name="Python")
        module = Module.objects.create(course=course, name="M", order=1)
        lesson = Lesson.objects.create(course=course, module=module, name="D", order=1)
        lesson.questions_count = 10

        expected = estimated_test_minutes(10)
        self.assertEqual(expected, 11)

        values = {
            "tree": StudentLessonItemSerializer(lesson).data["estimated_duration_minutes"],
            "test": TestLessonSerializer(lesson).data["estimated_duration_minutes"],
            "question": StudentCourseLessonsSerializer(lesson).data["estimated_duration_minutes"],
            "ranking": serialize_lesson_item(lesson)["estimated_duration_minutes"],
        }
        self.assertEqual(
            set(values.values()), {expected},
            f"Formulalar hamon farq qilmoqda: {values}",
        )


class ExternalErrorLeakTests(TestCase):
    """Tashqi servis xato matni foydalanuvchiga uzatilmasligi kerak."""

    def test_upstream_body_is_not_exposed(self):
        from unittest.mock import MagicMock, patch

        from app.services.student.external_student_api import (
            PDPStudentAPIClient,
            PDPStudentAPIError,
        )
        import requests

        secret_trace = "java.lang.NullPointerException at com.pdp.internal.Secret"
        response = MagicMock()
        response.status_code = 500
        response.json.side_effect = ValueError
        response.text = secret_trace
        response.raise_for_status.side_effect = requests.exceptions.HTTPError()

        with patch("requests.get", return_value=response):
            with self.assertRaises(PDPStudentAPIError) as ctx:
                PDPStudentAPIClient(token="x").get_student_info("1")

        self.assertNotIn("NullPointer", str(ctx.exception))
        self.assertNotIn("com.pdp.internal", str(ctx.exception))
