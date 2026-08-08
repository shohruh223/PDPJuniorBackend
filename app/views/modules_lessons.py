from django.db.models import Count
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models.question import Course, Lesson, Module
from app.permissions import IsStudentUserRole
from app.services.portal.ranking_service import (
    get_modules_with_lessons,
    get_student_course,
    serialize_lesson_item,
    serialize_module_item,
)


lesson_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
        "name": openapi.Schema(type=openapi.TYPE_STRING),
        "order": openapi.Schema(type=openapi.TYPE_INTEGER),
        "module_id": openapi.Schema(type=openapi.TYPE_INTEGER),
        "questions_count": openapi.Schema(type=openapi.TYPE_INTEGER),
        "estimated_duration_minutes": openapi.Schema(type=openapi.TYPE_INTEGER),
    },
)

module_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
        "name": openapi.Schema(type=openapi.TYPE_STRING),
        "order": openapi.Schema(type=openapi.TYPE_INTEGER),
        "course_id": openapi.Schema(type=openapi.TYPE_INTEGER),
        "lessons_count": openapi.Schema(type=openapi.TYPE_INTEGER),
    },
)


class ModuleListAPIView(APIView):
    """Frontend lessons modullar ro‘yxati."""

    permission_classes = [IsAuthenticated, IsStudentUserRole]

    @swagger_auto_schema(
        tags=["Portal / Modules"],
        operation_summary="Student kursi modullari",
        operation_description=(
            "Berilgan `course_id` kursining modullarini tartib bilan qaytaradi. Parametr yuborilmasa "
            "autentifikatsiya qilingan student profili/guruhidan kurs aniqlanadi. Bearer student tokeni talab qilinadi."
        ),
        manual_parameters=[
            openapi.Parameter("course_id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Ixtiyoriy kurs IDsi."),
        ],
        responses={
            200: openapi.Response(
                "Modullar ro‘yxati.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "course": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                        "name": openapi.Schema(type=openapi.TYPE_STRING),
                                    },
                                ),
                                "modules": openapi.Schema(type=openapi.TYPE_ARRAY, items=module_schema),
                            },
                        ),
                    },
                ),
            ),
            401: openapi.Response("Autentifikatsiya talab qilinadi."),
            403: openapi.Response("Faqat studentlar uchun."),
            404: openapi.Response("Kurs ID topilmadi yoki student uchun kurs aniqlanmadi."),
        },
    )
    def get(self, request, *args, **kwargs):
        course_id = request.query_params.get("course_id")
        if course_id:
            course = get_object_or_404(Course, pk=course_id)
        else:
            course = get_student_course(request.user)
            if not course:
                return Response(
                    {"success": False, "message": "Student uchun course topilmadi."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        modules = get_modules_with_lessons(course)
        data = [serialize_module_item(module, include_lessons=False) for module in modules]

        return Response(
            {
                "success": True,
                "message": "Modullar ro‘yxati.",
                "data": {
                    "course": {
                        "id": course.id,
                        "name": course.name,
                    },
                    "modules": data,
                },
            },
            status=status.HTTP_200_OK,
        )


class ModuleDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]

    @swagger_auto_schema(
        tags=["Portal / Modules"],
        operation_summary="Modul va uning darslari",
        operation_description=(
            "URL dagi `module_id` bo‘yicha modul ma’lumotlari va tartiblangan darslarini qaytaradi. "
            "Bearer student tokeni talab qilinadi."
        ),
        manual_parameters=[
            openapi.Parameter("module_id", openapi.IN_PATH, type=openapi.TYPE_INTEGER, required=True, description="Modul IDsi.")
        ],
        responses={
            200: openapi.Response(
                "Modul topildi.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                **module_schema["properties"],
                                "lessons": openapi.Schema(type=openapi.TYPE_ARRAY, items=lesson_schema),
                            },
                        ),
                    },
                ),
            ),
            401: openapi.Response("Autentifikatsiya talab qilinadi."),
            403: openapi.Response("Faqat studentlar uchun."),
            404: openapi.Response("Modul topilmadi."),
        },
    )
    def get(self, request, module_id, *args, **kwargs):
        module = get_object_or_404(
            Module.objects.annotate(lessons_count=Count("lessons", distinct=True)),
            pk=module_id,
        )
        lessons = (
            Lesson.objects.filter(module=module)
            .annotate(questions_count=Count("questions"))
            .order_by("order", "id")
        )
        module.lessons_count = lessons.count()
        payload = serialize_module_item(module, include_lessons=False)
        payload["lessons"] = [serialize_lesson_item(lesson) for lesson in lessons]

        return Response(
            {
                "success": True,
                "message": "Modul ma'lumotlari.",
                "data": payload,
            },
            status=status.HTTP_200_OK,
        )


class LessonListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]

    @swagger_auto_schema(
        tags=["Portal / Lessons"],
        operation_summary="Darslar ro‘yxati",
        operation_description=(
            "Darslarni modul yoki kurs bo‘yicha qaytaradi. `module_id` ikkalasi berilganda ustuvor; "
            "faqat `course_id` berilsa kurs bo‘yicha filtrlanadi. Ikkalasi ham yo‘q bo‘lsa student kursi ishlatiladi."
        ),
        manual_parameters=[
            openapi.Parameter("module_id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Modul IDsi."),
            openapi.Parameter("course_id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Kurs IDsi."),
        ],
        responses={
            200: openapi.Response(
                "Darslar ro‘yxati.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "lessons": openapi.Schema(type=openapi.TYPE_ARRAY, items=lesson_schema),
                                "count": openapi.Schema(type=openapi.TYPE_INTEGER),
                            },
                        ),
                    },
                ),
            ),
            400: openapi.Response("Filter berilmagan va student kursi aniqlanmagan."),
            401: openapi.Response("Autentifikatsiya talab qilinadi."),
            403: openapi.Response("Faqat studentlar uchun."),
        },
    )
    def get(self, request, *args, **kwargs):
        module_id = request.query_params.get("module_id")
        course_id = request.query_params.get("course_id")

        lessons = Lesson.objects.annotate(questions_count=Count("questions"))

        if module_id:
            lessons = lessons.filter(module_id=module_id)
        elif course_id:
            lessons = lessons.filter(course_id=course_id)
        else:
            course = get_student_course(request.user)
            if not course:
                return Response(
                    {"success": False, "message": "Filter yoki course topilmadi."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            lessons = lessons.filter(course=course)

        lessons = lessons.select_related("module", "course").order_by("module__order", "order", "id")
        items = [serialize_lesson_item(lesson) for lesson in lessons]

        return Response(
            {
                "success": True,
                "message": "Darslar ro‘yxati.",
                "data": {"lessons": items, "count": len(items)},
            },
            status=status.HTTP_200_OK,
        )


class LessonDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]

    @swagger_auto_schema(
        tags=["Portal / Lessons"],
        operation_summary="Dars tafsilotlari",
        operation_description=(
            "URL dagi `lesson_id` bo‘yicha darsni, savollar sonini hamda tegishli modul va kurs "
            "qisqa ma’lumotlarini qaytaradi. Bearer student tokeni talab qilinadi."
        ),
        manual_parameters=[
            openapi.Parameter("lesson_id", openapi.IN_PATH, type=openapi.TYPE_INTEGER, required=True, description="Dars IDsi.")
        ],
        responses={
            200: openapi.Response(
                "Dars topildi.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                **lesson_schema["properties"],
                                "module": openapi.Schema(type=openapi.TYPE_OBJECT),
                                "course": openapi.Schema(type=openapi.TYPE_OBJECT),
                            },
                        ),
                    },
                ),
            ),
            401: openapi.Response("Autentifikatsiya talab qilinadi."),
            403: openapi.Response("Faqat studentlar uchun."),
            404: openapi.Response("Dars topilmadi."),
        },
    )
    def get(self, request, lesson_id, *args, **kwargs):
        lesson = get_object_or_404(
            Lesson.objects.annotate(questions_count=Count("questions")).select_related("module", "course"),
            pk=lesson_id,
        )
        payload = serialize_lesson_item(lesson)
        payload["module"] = {
            "id": lesson.module_id,
            "name": lesson.module.name,
            "order": lesson.module.order,
        }
        payload["course"] = {
            "id": lesson.course_id,
            "name": lesson.course.name,
        }

        return Response(
            {
                "success": True,
                "message": "Dars ma'lumotlari.",
                "data": payload,
            },
            status=status.HTTP_200_OK,
        )
