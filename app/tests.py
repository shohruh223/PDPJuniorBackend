from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from app.models import Course, GalleryPost, Module, StudentMark


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
