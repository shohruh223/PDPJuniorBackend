"""Yuk sinovi uchun sun'iy ma'lumot yaratadi.

Ishlatish (FAQAT staging/lokal bazada!):

    python manage.py seed_load_test --students 500 --modules 8 --lessons 6 --questions 10

Buyruq `--yes` bayrog'isiz production'ga o'xshash bazada ishlamaydi.
Yaratilgan o'quvchilar telefon raqami `+99870000XXXX` shaklida bo'ladi,
shuning uchun ularni keyin oson topib o'chirish mumkin:

    python manage.py seed_load_test --cleanup
"""

from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from app.models.auth import StudentProfile, User
from app.models.branch import Branch
from app.models.mentors import Mentor
from app.models.question import Course, Lesson, Module, Question

PHONE_PREFIX = "+99870000"


class Command(BaseCommand):
    help = "Yuk sinovi uchun o'quvchilar, modullar, darslar va savollar yaratadi."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=500)
        parser.add_argument("--modules", type=int, default=8)
        parser.add_argument("--lessons", type=int, default=6)
        parser.add_argument("--questions", type=int, default=10)
        parser.add_argument("--course", type=str, default="Python")
        parser.add_argument("--cleanup", action="store_true", help="Sinov ma'lumotini o'chiradi.")
        parser.add_argument("--yes", action="store_true", help="Tasdiqlashni o'tkazib yuboradi.")

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["yes"]:
            raise CommandError(
                "DEBUG=0 muhitda ishlatish uchun --yes bayrog'ini bering. "
                "Bu buyruq bazaga sun'iy ma'lumot yozadi!"
            )

        if options["cleanup"]:
            return self._cleanup()

        return self._seed(options)

    def _cleanup(self):
        users = User.objects.filter(phone_number__startswith=PHONE_PREFIX)
        count = users.count()
        users.delete()
        self.stdout.write(self.style.SUCCESS(f"{count} ta sinov foydalanuvchisi o'chirildi."))

    @transaction.atomic
    def _seed(self, options):
        course, _ = Course.objects.get_or_create(
            name=options["course"], defaults={"sort_order": 1}
        )

        branches = []
        for i in range(6):
            branch, _ = Branch.objects.get_or_create(
                name=f"Yuk-sinov filiali {i}",
                defaults={
                    "address": "Test manzil",
                    "phone": "+998900000000",
                    "map_url": "https://maps.example/loadtest",
                },
            )
            branches.append(branch)
            Mentor.objects.get_or_create(
                name=f"Yuk-sinov mentori {i}",
                defaults={
                    "role": course.name,
                    "branch": branch,
                    "exp": "3 yil",
                    "students_count": "20",
                    "working_period_start": date(2024, 1, 1),
                },
            )

        created_questions = 0
        for m in range(1, options["modules"] + 1):
            module, _ = Module.objects.get_or_create(
                course=course, order=m, defaults={"name": f"Yuk-sinov moduli {m}"}
            )
            for l in range(1, options["lessons"] + 1):
                lesson, _ = Lesson.objects.get_or_create(
                    module=module, order=l,
                    defaults={"course": course, "name": f"Dars {m}.{l}"},
                )
                have = Question.objects.filter(lesson=lesson).count()
                for q in range(have, options["questions"]):
                    Question.objects.create(
                        lesson=lesson,
                        text={
                            "uz": f"{m}.{l} moduldagi {q + 1}-savol",
                            "ru": f"Вопрос {q + 1}",
                            "en": f"Question {q + 1}",
                        },
                        options={
                            key: {"uz": f"Variant {key}", "ru": f"Вариант {key}", "en": f"Option {key}"}
                            for key in "ABCD"
                        },
                        correct_option="A",
                    )
                    created_questions += 1

        existing = set(
            User.objects.filter(phone_number__startswith=PHONE_PREFIX)
            .values_list("phone_number", flat=True)
        )
        new_users = []
        for i in range(options["students"]):
            phone = f"{PHONE_PREFIX}{i:04d}"
            if phone in existing:
                continue
            user = User(
                phone_number=phone,
                first_name=f"Yuk{i:04d}",
                last_name="Sinov",
                role=User.RoleChoices.STUDENT,
            )
            user.set_unusable_password()
            new_users.append(user)
        User.objects.bulk_create(new_users, batch_size=500)

        users = list(User.objects.filter(phone_number__startswith=PHONE_PREFIX))
        have_profiles = set(
            StudentProfile.objects.filter(user__in=users).values_list("user_id", flat=True)
        )
        profiles = []
        for i, user in enumerate(users):
            if user.id in have_profiles:
                continue
            profiles.append(StudentProfile(
                user=user,
                course=course,
                branch=branches[i % len(branches)],
                group_name=f"P-{i % 20}",
                api_score=i % 300,
                api_coin=i % 100,
                total_score=i % 300,
                total_coin=i % 100,
                attendance_average_percent=float(i % 100),
            ))
        StudentProfile.objects.bulk_create(profiles, batch_size=500)

        self.stdout.write(self.style.SUCCESS(
            f"Tayyor: {len(users)} o'quvchi, "
            f"{options['modules']} modul, "
            f"{options['modules'] * options['lessons']} dars, "
            f"+{created_questions} savol."
        ))
