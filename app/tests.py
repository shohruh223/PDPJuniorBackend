import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from app.models import Course, GalleryPost, Module, StudentMark
from app.models.auth import StudentProfile
from app.models.branch import Branch
from app.models.coin import CoinOrder, CoinProduct
from app.models.question import Lesson, Question
from app.models.test import TestSession, TestSessionQuestion
from app.services.portal.shop_service import purchase_product


class FrontendDataIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_frontend_data", verbosity=0)

    def setUp(self):
        self.client = APIClient()

    def test_seeded_public_endpoints(self):
        courses = self.client.get("/api/courses")
        gallery = self.client.get("/api/gallery")
        ranking = self.client.get("/api/ranking")

        self.assertEqual(courses.status_code, 200)
        self.assertEqual(len(courses.json()), 4)
        self.assertEqual(len(gallery.json()["data"]["items"]), 7)
        self.assertGreaterEqual(len(ranking.json()["data"]["students"]), 24)

    def test_student_marks_and_curriculum_are_database_backed(self):
        user = get_user_model().objects.get(phone_number="+998914530919")
        self.client.force_authenticate(user=user)

        marks = self.client.get("/api/student/marks")
        modules = self.client.get("/api/student/modules")

        self.assertEqual(marks.status_code, 200)
        self.assertEqual(len(marks.json()["students"]), 9)
        self.assertEqual(len(marks.json()["dates"]), 7)
        self.assertEqual(len(modules.json()["data"]["modules"]), 12)
        self.assertEqual(StudentMark.objects.count(), 63)

    def test_seed_command_is_idempotent(self):
        before = (
            Course.objects.count(),
            Module.objects.count(),
            GalleryPost.objects.count(),
            StudentMark.objects.count(),
        )
        call_command("seed_frontend_data", verbosity=0)
        after = (
            Course.objects.count(),
            Module.objects.count(),
            GalleryPost.objects.count(),
            StudentMark.objects.count(),
        )
        self.assertEqual(after, before)


class StudentTestRewardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.course = Course.objects.create(name="Python")
        cls.module = Module.objects.create(
            course=cls.course,
            name="Python asoslari",
            order=1,
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course,
            module=cls.module,
            name="O‘zgaruvchilar",
            order=1,
        )
        cls.questions = [
            Question.objects.create(
                lesson=cls.lesson,
                text={
                    "uz": f"{number}-savol",
                    "ru": f"{number}-вопрос",
                    "en": f"Question {number}",
                },
                options={
                    "A": {"uz": "To‘g‘ri", "ru": "Верно", "en": "Correct"},
                    "B": {"uz": "Xato", "ru": "Неверно", "en": "Wrong"},
                },
                correct_option="A",
            )
            for number in range(1, 3)
        ]
        cls.second_module = Module.objects.create(
            course=cls.course,
            name="Shart operatorlari",
            order=2,
        )
        cls.second_lesson = Lesson.objects.create(
            course=cls.course,
            module=cls.second_module,
            name="If va else",
            order=1,
        )
        cls.second_question = Question.objects.create(
            lesson=cls.second_lesson,
            text={
                "uz": "Shart operatori qaysi?",
                "ru": "Какой оператор условный?",
                "en": "Which operator is conditional?",
            },
            options={
                "A": {"uz": "if", "ru": "if", "en": "if"},
                "B": {"uz": "for", "ru": "for", "en": "for"},
            },
            correct_option="A",
        )
        cls.user = get_user_model().objects.create_user(
            phone_number="+998901112233",
            password="test-password",
            role="student",
            first_name="Test",
            last_name="Student",
        )
        cls.profile = StudentProfile.objects.create(
            user=cls.user,
            course=cls.course,
            group_name="P-1",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.session = TestSession.objects.create(
            student=self.user,
            lesson=self.lesson,
            total_questions=2,
            duration_minutes=3,
        )
        TestSessionQuestion.objects.bulk_create(
            [
                TestSessionQuestion(
                    session=self.session,
                    question=question,
                    order=order,
                )
                for order, question in enumerate(self.questions, start=1)
            ]
        )

    def submit_answer(self, question, selected_option):
        return self.client.post(
            f"/api/student/tests/during/{self.session.session_id}/answer/",
            {
                "question_id": question.pk,
                "selected_option": selected_option,
            },
            format="json",
        )

    def test_correct_answer_awards_one_score_and_one_coin_once(self):
        first = self.submit_answer(self.questions[0], "A")
        self.assertEqual(first.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.local_test_score, 1)
        self.assertEqual(self.profile.test_coin, 1)
        self.assertEqual(self.profile.total_score, 1)
        self.assertEqual(self.profile.total_coin, 1)

        repeated = self.submit_answer(self.questions[0], "A")
        self.assertEqual(repeated.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.local_test_score, 1)
        self.assertEqual(self.profile.test_coin, 1)

    def test_changing_correct_answer_to_wrong_removes_reward(self):
        self.submit_answer(self.questions[0], "A")
        changed = self.submit_answer(self.questions[0], "B")
        self.assertEqual(changed.status_code, 200)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.local_test_score, 0)
        self.assertEqual(self.profile.test_coin, 0)
        self.assertEqual(self.profile.total_score, 0)
        self.assertEqual(self.profile.total_coin, 0)

    def test_question_list_hides_correct_answer_and_checks_course(self):
        own_lesson = self.client.get(
            f"/api/student/lessons/{self.lesson.pk}/questions"
        )
        self.assertEqual(own_lesson.status_code, 200)
        question_data = own_lesson.json()["data"]["questions"][0]
        self.assertNotIn("correct_index", question_data)
        self.assertNotIn("correctIndex", question_data)

        other_course = Course.objects.create(name="Frontend")
        other_module = Module.objects.create(
            course=other_course,
            name="Frontend asoslari",
            order=1,
        )
        other_lesson = Lesson.objects.create(
            course=other_course,
            module=other_module,
            name="HTML",
            order=1,
        )
        forbidden = self.client.get(
            f"/api/student/lessons/{other_lesson.pk}/questions"
        )
        self.assertEqual(forbidden.status_code, 404)

    def test_only_first_module_is_available_before_completion(self):
        response = self.client.get("/api/student/tests/lessons")
        self.assertEqual(response.status_code, 200)

        module_ids = [
            module["id"]
            for module in response.json()["data"]["modules"]
        ]
        self.assertEqual(module_ids, [self.module.pk])

        locked_start = self.client.post(
            "/api/student/tests/start/",
            {
                "module_id": self.second_module.pk,
                "lesson_id": self.second_lesson.pk,
            },
            format="json",
        )
        self.assertEqual(locked_start.status_code, 400)
        self.assertIn("module_id", locked_start.json())

    def test_second_module_unlocks_after_first_module_is_fully_answered(self):
        self.submit_answer(self.questions[0], "A")
        finished = self.submit_answer(self.questions[1], "B")
        self.assertEqual(finished.status_code, 200)
        self.assertTrue(finished.json()["data"]["finished"])

        response = self.client.get("/api/student/tests/lessons")
        self.assertEqual(response.status_code, 200)
        module_ids = [
            module["id"]
            for module in response.json()["data"]["modules"]
        ]
        self.assertEqual(
            module_ids,
            [self.module.pk, self.second_module.pk],
        )

        unlocked_start = self.client.post(
            "/api/student/tests/start/",
            {
                "module_id": self.second_module.pk,
                "lesson_id": self.second_lesson.pk,
            },
            format="json",
        )
        self.assertEqual(unlocked_start.status_code, 201)


class ShopPurchaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        course = Course.objects.create(name="Python")
        branch = Branch.objects.create(
            name="Chilonzor",
            address="Toshkent",
            phone="+998901234567",
            map_url="https://maps.example.com/chilonzor",
        )
        user = get_user_model().objects.create_user(
            phone_number="+998909998877",
            role="student",
            first_name="Ali",
            last_name="Valiyev",
        )
        cls.profile = StudentProfile.objects.create(
            user=user,
            course=course,
            branch=branch,
            group_name="P-10",
            api_coin=5,
            test_coin=10,
        )
        cls.product = CoinProduct.objects.create(
            name="PDP futbolka",
            description="Test mahsuloti",
            price=12,
            stock=1,
        )

    def test_purchase_deducts_balance_and_saves_order_snapshot(self):
        with self.captureOnCommitCallbacks(execute=True):
            order, error = purchase_product(
                profile=self.profile,
                product_id=self.product.pk,
            )

        self.assertIsNone(error)
        self.profile.refresh_from_db()
        self.product.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(self.profile.test_coin, 0)
        self.assertEqual(self.profile.api_coin, 3)
        self.assertEqual(self.profile.total_coin, 3)
        self.assertEqual(self.product.stock, 0)
        self.assertEqual(order.status, CoinOrder.StatusChoices.PENDING)
        self.assertEqual(order.student_name, "Ali Valiyev")
        self.assertEqual(order.branch_name, "Chilonzor")
        self.assertEqual(order.course_name, "Python")
        self.assertEqual(order.group_name, "P-10")
        self.assertEqual(order.balance_before, 15)
        self.assertEqual(order.balance_after, 3)
        self.assertIn("TELEGRAM_BOT_TOKEN", order.telegram_error)

    def test_failed_purchase_does_not_change_balance_or_stock(self):
        expensive = CoinProduct.objects.create(
            name="Noutbuk",
            description="Qimmat mahsulot",
            price=1000,
            stock=1,
        )
        order, error = purchase_product(
            profile=self.profile,
            product_id=expensive.pk,
        )

        self.profile.refresh_from_db()
        expensive.refresh_from_db()
        self.assertIsNone(order)
        self.assertEqual(error, "Coin yetarli emas.")
        self.assertEqual(self.profile.total_coin, 15)
        self.assertEqual(expensive.stock, 1)

    @override_settings(
        TELEGRAM_BOT_TOKEN="test-bot-token",
        TELEGRAM_SHOP_CHAT_ID="-5326868544",
    )
    @patch("app.services.portal.shop_notification_service.request.urlopen")
    def test_purchase_sends_telegram_message_to_admin_group(self, mocked_urlopen):
        response = MagicMock()
        response.read.return_value = b'{"ok": true}'
        mocked_urlopen.return_value.__enter__.return_value = response

        with self.captureOnCommitCallbacks(execute=True):
            order, error = purchase_product(
                profile=self.profile,
                product_id=self.product.pk,
            )

        self.assertIsNone(error)
        sent_request = mocked_urlopen.call_args.args[0]
        payload = json.loads(sent_request.data.decode("utf-8"))
        self.assertEqual(payload["chat_id"], "-5326868544")
        self.assertIn("Ali Valiyev", payload["text"])
        self.assertIn("Chilonzor", payload["text"])
        self.assertIn("PDP futbolka", payload["text"])

        order.refresh_from_db()
        self.assertIsNotNone(order.telegram_sent_at)
        self.assertEqual(order.telegram_error, "")
