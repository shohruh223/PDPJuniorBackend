from rest_framework import viewsets, permissions, filters
from rest_framework.response import Response
from rest_framework.decorators import action

from app.models.question import Course, Lesson, Question, Module
from app.permissions import IsAdminUserRole
from app.serializers.question import (
    CourseSerializer,
    LessonSerializer,
    QuestionWriteSerializer,
    QuestionAdminReadSerializer, ModuleSerializer,
)



class AdminCourseViewSet(viewsets.ModelViewSet):
    """
    Admin course qo'shishi, ko'rishi, tahrirlashi, o'chirishi mumkin.
    """
    queryset = Course.objects.all().order_by("name")
    serializer_class = CourseSerializer
    permission_classes = [IsAdminUserRole]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["id", "name"]
    ordering = ["name"]


class AdminModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all().select_related("course")
    serializer_class = ModuleSerializer
    permission_classes = [IsAdminUserRole]

    def get_queryset(self):
        queryset = super().get_queryset()
        course_id = self.request.query_params.get("course_id")
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset.order_by("course_id", "order")


class AdminLessonViewSet(viewsets.ModelViewSet):
    """
    Admin lesson qo'shishi, ko'rishi, tahrirlashi, o'chirishi mumkin.
    """
    queryset = Lesson.objects.select_related("course").all().order_by("course__name", "name")
    serializer_class = LessonSerializer
    permission_classes = [IsAdminUserRole]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "course__name"]
    ordering_fields = ["id", "name", "course__name"]
    ordering = ["course__name", "name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        course_id = self.request.query_params.get("course_id")
        module_id = self.request.query_params.get("module_id")

        if course_id:
            queryset = queryset.filter(course_id=course_id)

        if module_id:
            queryset = queryset.filter(module_id=module_id)

        return queryset


class AdminQuestionViewSet(viewsets.ModelViewSet):
    """
    Admin question qo'shishi, ko'rishi, tahrirlashi, o'chirishi mumkin.
    """
    queryset = Question.objects.select_related("lesson", "lesson__course").all()
    permission_classes = [IsAdminUserRole]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "lesson__name",
        "lesson__course__name",
        "text",
    ]
    ordering_fields = ["id", "created_at", "lesson__name", "lesson__course__name"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return QuestionAdminReadSerializer
        return QuestionWriteSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        course_id = self.request.query_params.get("course_id")
        lesson_id = self.request.query_params.get("lesson_id")

        if course_id:
            queryset = queryset.filter(lesson__course_id=course_id)

        if lesson_id:
            queryset = queryset.filter(lesson_id=lesson_id)

        return queryset

    @action(detail=False, methods=["get"], url_path="by-lesson/(?P<lesson_id>[^/.]+)")
    def by_lesson(self, request, lesson_id=None):
        queryset = self.get_queryset().filter(lesson_id=lesson_id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = QuestionAdminReadSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = QuestionAdminReadSerializer(queryset, many=True)
        return Response(serializer.data)