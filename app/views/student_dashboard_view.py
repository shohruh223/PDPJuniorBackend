from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from app.models.question import Course, Module, Lesson
from django.db.models import Count, Prefetch
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from app.permissions import IsStudentUserRole
from app.serializers.student_lesson_tree_serializer import StudentModuleSerializer
from app.services.student.student_dashboard_query_service import get_student_dashboard_data
from app.models.auth import StudentProfile


class StudentDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]

    @swagger_auto_schema(
        tags=["Student / Dashboard"],
        operation_summary="Student dashboard ma'lumotlarini olish",
        operation_description="""
Student login qilgandan keyin asosiy dashboard ekranini chizish uchun ishlatiladi.

Bu endpoint student uchun umumiy dashboard ma'lumotlarini qaytaradi.
Odatda frontend foydalanuvchi muvaffaqiyatli login bo‘lgandan keyin
shu endpointni chaqiradi.

Frontend qanday ishlatadi:
1. Foydalanuvchi login qiladi.
2. Front `access token` ni saqlaydi.
3. Dashboard sahifasi ochilganda shu endpointga GET so‘rov yuboradi.
4. Response ichidagi `data` yordamida dashboard kartalari, progress,
   umumiy ko‘rsatkichlar va boshqa studentga tegishli ma'lumotlar chiziladi.

Ketma-ketlik:
- bu endpoint odatda login flow'dan keyin ishlatiladi
- masalan:
  `CheckPhoneAPIView` -> `EnterPasswordAPIView` -> `CheckSMSCodeAPIView`
  -> `StudentDashboardAPIView`

Auth:
- bu endpoint faqat login qilgan student uchun ishlaydi
- `Authorization: Bearer <access_token>` yuborilishi kerak

Success response:
- `success`: so‘rov holati
- `message`: frontga ko‘rsatish mumkin bo‘lgan umumiy xabar
- `data`: dashboard uchun kerakli barcha student ma'lumotlari

Xatolik holati:
- agar student profile topilmasa 404 qaytadi
- agar ichki xatolik bo‘lsa 500 qaytadi

Muhim:
- bu endpoint faqat dashboardning umumiy ma'lumotlarini qaytaradi
- darslar daraxti yoki modul/lesson ro‘yxati uchun keyingi endpoint:
  `student/tests/lessons/`
""",
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Student dashboard ma'lumotlari muvaffaqiyatli olindi.",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Dashboard ma'lumotlari",
                        "data": {
                            "student": {
                                "id": "c97a5d85-2d93-4f0d-b6c4-8d9d3a7d4e33",
                                "external_id": "49687357-f9a9-4642-a946-81ce67b633bd",
                                "full_name": "Ali Valiyev",
                                "first_name": "Ali",
                                "last_name": "Valiyev",
                                "phone_number": "+998901234567",
                                "group_name": "N89",
                                "image": "https://example.uz/media/profiles/ali.webp",
                                "avatar": "AV",
                            },
                            "course": {
                                "id": 1,
                                "name": "Junior Backend"
                            },
                            "scores": {
                                "api_score": 100,
                                "local_test_score": 20,
                                "total_score": 120
                            },
                            "coins": {
                                "api_coin": 40,
                                "test_coin": 5,
                                "total_coin": 45,
                                "lesson_coin": 2
                            },
                            "finance": {
                                "all_debtor": "0.00",
                                "attendance_average_percent": 95,
                                "student_debtors": []
                            },
                            "lesson": {
                                "id": 100,
                                "attendance": "present",
                                "status": "completed",
                                "lesson_date": ["2026-08-08"],
                                "start_time": "10:00",
                                "end_time": "11:30"
                            },
                            "module_barchart": [],
                            "last_synced_at": "2026-08-08T10:00:00Z",
                            "sync_warning": None
                        }
                    }
                },
            ),
            status.HTTP_401_UNAUTHORIZED: openapi.Response(
                description="Token yuborilmagan yoki token noto‘g‘ri."
            ),
            status.HTTP_403_FORBIDDEN: openapi.Response(
                description="Foydalanuvchida student roli yo‘q."
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="Student profile topilmadi."
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Dashboard ma'lumotlarini olishda ichki server xatoligi yuz berdi."
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        try:
            data = get_student_dashboard_data(request.user, request=request)
            return Response(
                {
                    "success": True,
                    "message": "Dashboard ma'lumotlari",
                    "data": data,
                },
                status=status.HTTP_200_OK,
            )
        except StudentProfile.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Student profile topilmadi.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "Dashboardni olishda xatolik.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class StudentLessonListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]

    @swagger_auto_schema(
        tags=["Student / Lessons"],
        operation_summary="Course bo‘yicha modul va lessonlar ro‘yxatini olish",
        operation_description="""
Tanlangan course uchun modul va lessonlar daraxtini qaytaradi.

Bu endpoint odatda student dashboard yoki course detail sahifasida ishlatiladi.
Frontend foydalanuvchi qaysi course'ni ochgan bo‘lsa, o‘sha course'ning
ichidagi modullar va ulardagi lessonlarni olish uchun shu endpointni chaqiradi.

Frontend qanday ishlatadi:
1. Front course tanlaydi yoki dashboarddan current course'ni oladi.
2. Shu endpointga `course_id` query param bilan GET so‘rov yuboradi.
3. Response ichidagi `course` va `modules` orqali sidebar, accordion,
   tree view yoki lesson list UI chiziladi.

Ketma-ketlik:
- odatda `StudentDashboardAPIView` dan keyin ishlatiladi
- misol:
  `StudentDashboardAPIView` -> current course id olish
  -> `StudentLessonListAPIView?course_id=1`

Request query param:
- `course_id`: qaysi course uchun modul va lessonlar kerakligi

Auth:
- bu endpoint login bo‘lgan foydalanuvchi uchun ishlaydi
- `Authorization: Bearer <access_token>` yuborilishi kerak

Success response:
- `course.id`: tanlangan course ID si
- `course.name`: tanlangan course nomi
- `modules`: shu course ichidagi barcha modullar
- har bir modul ichida lessonlar bo‘ladi
- serializerga qarab har bir lesson ichida question count yoki boshqa
  qo‘shimcha ma'lumotlar ham bo‘lishi mumkin

Xatolik holati:
- `course_id` yuborilmasa 400 qaytadi
- course topilmasa 404 qaytadi

Muhim:
- bu endpoint umumiy dashboard emas
- bu endpoint aynan course ichidagi modul/lesson tree'ni qaytaradi
- student dashboard ochilgandan keyin darslar ro‘yxatini chizish uchun juda qulay
""",
        manual_parameters=[
            openapi.Parameter(
                "course_id",
                openapi.IN_QUERY,
                description="Course ID. Qaysi course uchun modul va lessonlar kerak bo‘lsa, shu ID yuboriladi.",
                type=openapi.TYPE_INTEGER,
                required=True,
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Course bo‘yicha modul va lessonlar ro‘yxati muvaffaqiyatli olindi.",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Course lessonlari olindi.",
                        "data": {
                            "course": {
                                "id": 1,
                                "name": "Junior Backend",
                            },
                            "modules": [
                                {
                                    "id": 10,
                                    "name": "Python Basics",
                                    "lessons": [
                                        {
                                            "id": 100,
                                            "name": "Variables",
                                            "questions_count": 10
                                        },
                                        {
                                            "id": 101,
                                            "name": "Conditions",
                                            "questions_count": 8
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                },
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="`course_id` yuborilmagan yoki noto‘g‘ri formatda yuborilgan."
            ),
            status.HTTP_401_UNAUTHORIZED: openapi.Response(
                description="Token yuborilmagan yoki token noto‘g‘ri."
            ),
            status.HTTP_403_FORBIDDEN: openapi.Response(
                description="Foydalanuvchida student roli yo‘q."
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="Berilgan `course_id` bo‘yicha course topilmadi."
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        course_id = request.query_params.get("course_id")
        if not course_id:
            return Response(
                {
                    "success": False,
                    "message": "course_id yuborilishi shart.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Course topilmadi.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        lessons_queryset = (
            Lesson.objects
            .filter(course=course)
            .annotate(questions_count=Count("questions"))
            .order_by("order", "id")
        )

        modules = (
            Module.objects
            .filter(course=course)
            .annotate(lessons_count=Count("lessons", distinct=True))
            .prefetch_related(
                Prefetch("lessons", queryset=lessons_queryset)
            )
            .order_by("order", "id")
        )

        return Response(
            {
                "success": True,
                "message": "Course lessonlari olindi.",
                "data": {
                    "course": {
                        "id": course.id,
                        "name": course.name,
                    },
                    "modules": StudentModuleSerializer(modules, many=True).data,
                },
            },
            status=status.HTTP_200_OK,
        )