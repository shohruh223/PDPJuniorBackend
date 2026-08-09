from calendar import monthrange
from datetime import date

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import Course, StudentMark
from app.models.auth import StudentProfile
from app.permissions import IsStudentUserRole
from app.serializers.marks import MarkRecordSerializer, MarksCourseSerializer
from app.services.profile_image_service import build_profile_image_url


mark_record_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
        "date": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
        "attendance": openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=["present", "absent", "late"],
            description="Davomat holati: qatnashgan, qatnashmagan yoki kechikkan.",
        ),
        "grade": openapi.Schema(
            type=openapi.TYPE_INTEGER,
            x_nullable=True,
            description="1–5 oralig‘idagi baho yoki baholanmagan bo‘lsa null.",
        ),
        "verified": openapi.Schema(
            type=openapi.TYPE_BOOLEAN, description="Yozuv tasdiqlanganligi."
        ),
        "lesson_id": openapi.Schema(type=openapi.TYPE_INTEGER, x_nullable=True),
        "lesson_name": openapi.Schema(type=openapi.TYPE_STRING, x_nullable=True),
    },
)

marks_course_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
        "name": openapi.Schema(type=openapi.TYPE_STRING),
        "description": openapi.Schema(type=openapi.TYPE_STRING),
        "image": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI),
    },
)

marks_student_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
        "name": openapi.Schema(type=openapi.TYPE_STRING),
        "group": openapi.Schema(type=openapi.TYPE_STRING),
        "avatar": openapi.Schema(
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_URI,
            x_nullable=True,
        ),
        "records": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=mark_record_schema,
            description="Sana bo‘yicha o‘sish tartibidagi davomat/baho yozuvlari.",
        ),
    },
)

marks_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "courses": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=marks_course_schema,
            description="Tanlash uchun bazadagi faol kurslar.",
        ),
        "active_course": marks_course_schema,
        "students": openapi.Schema(
            type=openapi.TYPE_ARRAY, items=marks_student_schema
        ),
        "dates": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            description="Natijada yozuvi bor sanalar, o‘sish tartibida.",
        ),
    },
)


class StudentMarksAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]

    @swagger_auto_schema(
        tags=["Student / Baho va davomat"],
        operation_summary="Guruhning oylik baho va davomati",
        operation_description=(
            "Joriy student profilining guruhi va kursini aniqlaydi. `course_id` berilsa "
            "tanlangan faol kurs ishlatiladi, aks holda profil kursi olinadi. Shu guruh va "
            "kursdagi studentlarning ko‘rsatilgan oydagi bazada saqlangan baho/davomat "
            "yozuvlari qaytariladi. `month` berilmasa bazadagi eng so‘nggi yozuv oyi, "
            "yozuv bo‘lmasa joriy oy ishlatiladi. Natijalar "
            "seed yoki statik ma’lumotdan emas, faqat DB yozuvlaridan tuziladi."
        ),
        manual_parameters=[
            openapi.Parameter(
                "course_id",
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description="Ixtiyoriy faol kurs IDsi.",
            ),
            openapi.Parameter(
                "month",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
                required=False,
                description="Oy `YYYY-MM` formatida. Masalan: `2026-08`.",
            ),
        ],
        responses={
            200: openapi.Response(
                description="Tanlangan guruh, kurs va oy uchun natijalar.",
                schema=marks_response_schema,
                examples={
                    "application/json": {
                        "courses": [
                            {
                                "id": 1,
                                "name": "Frontend",
                                "description": "",
                                "image": "",
                            }
                        ],
                        "active_course": {
                            "id": 1,
                            "name": "Frontend",
                            "description": "",
                            "image": "",
                        },
                        "students": [
                            {
                                "id": "1da85586-e1b0-4b44-b62f-e74bd2eb93ed",
                                "name": "Ali Valiyev",
                                "group": "F-12",
                                "avatar": None,
                                "records": [
                                    {
                                        "id": 7,
                                        "date": "2026-08-05",
                                        "attendance": "present",
                                        "grade": 5,
                                        "verified": True,
                                        "lesson_id": 3,
                                        "lesson_name": "HTML",
                                    }
                                ],
                            }
                        ],
                        "dates": ["2026-08-05"],
                    }
                },
            ),
            400: openapi.Response(
                description="`course_id` son emas yoki `month` formati noto‘g‘ri."
            ),
            401: openapi.Response(description="Bearer token talab qilinadi."),
            403: openapi.Response(description="Faqat student roli uchun."),
            404: openapi.Response(
                description="Student profili, profil kursi yoki tanlangan faol kurs topilmadi."
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            return Response(
                {"detail": "Student profili topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        month_value = request.query_params.get("month")
        parsed_month = self._parse_month(month_value)
        if parsed_month is None:
            return Response(
                {"detail": "month `YYYY-MM` formatida bo‘lishi kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        course_id = request.query_params.get("course_id")
        if course_id:
            try:
                course_id = int(course_id)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "course_id butun son bo‘lishi kerak."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            course = Course.objects.filter(pk=course_id, is_active=True).first()
        else:
            course = profile.course

        if course is None or not course.is_active:
            return Response(
                {"detail": "Faol kurs topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not month_value:
            latest_mark = (
                StudentMark.objects.filter(
                    course=course,
                    student_profile__group_name=profile.group_name,
                )
                .order_by("-record_date")
                .values_list("record_date", flat=True)
                .first()
            )
            if latest_mark:
                parsed_month = (latest_mark.year, latest_mark.month)

        year, month = parsed_month
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        students = StudentProfile.objects.filter(
            course=course,
            user__is_active=True,
            marks__course=course,
            marks__record_date__range=(first_day, last_day),
        )
        if profile.group_name:
            students = students.filter(group_name=profile.group_name)
        else:
            # Guruh biriktirilmagan profillarni bitta guruh deb oshkor qilmaymiz.
            students = students.filter(pk=profile.pk)
        students = students.select_related("user").distinct().order_by(
            "user__first_name", "user__last_name", "id"
        )
        marks = (
            StudentMark.objects.filter(
                student_profile__in=students,
                course=course,
                record_date__range=(first_day, last_day),
            )
            .select_related("lesson")
            .order_by("record_date", "id")
        )

        records_by_student = {}
        dates = set()
        for mark in marks:
            records_by_student.setdefault(mark.student_profile_id, []).append(mark)
            dates.add(mark.record_date.isoformat())

        student_payload = []
        for student in students:
            avatar = build_profile_image_url(student.user, request=request)
            student_payload.append(
                {
                    "id": str(student.id),
                    "name": student.user.full_name,
                    "group": student.group_name,
                    "avatar": avatar,
                    "records": MarkRecordSerializer(
                        records_by_student.get(student.id, []), many=True
                    ).data,
                }
            )

        active_courses = Course.objects.filter(is_active=True).order_by(
            "sort_order", "name", "id"
        )
        return Response(
            {
                "courses": MarksCourseSerializer(active_courses, many=True).data,
                "active_course": MarksCourseSerializer(course).data,
                "students": student_payload,
                "dates": sorted(dates),
            }
        )

    @staticmethod
    def _parse_month(value):
        if not value:
            today = date.today()
            return today.year, today.month
        try:
            parsed = date.fromisoformat(f"{value}-01")
        except (TypeError, ValueError):
            return None
        if value != f"{parsed.year:04d}-{parsed.month:02d}":
            return None
        return parsed.year, parsed.month
