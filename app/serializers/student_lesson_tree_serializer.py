from rest_framework import serializers

from app.models.question import Module, Lesson
from app.utils.text import estimated_test_minutes


class StudentLessonItemSerializer(serializers.ModelSerializer):
    questions_count = serializers.SerializerMethodField()
    estimated_duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = (
            "id",
            "name",
            "order",
            "questions_count",
            "estimated_duration_minutes",
        )

    def get_questions_count(self, obj):
        return getattr(obj, "questions_count", 0)

    def get_estimated_duration_minutes(self, obj):
        return estimated_test_minutes(getattr(obj, "questions_count", 0))


class StudentModuleSerializer(serializers.ModelSerializer):
    lessons = StudentLessonItemSerializer(many=True, read_only=True)
    lessons_count = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = ("id", "name", "order", "lessons_count", "lessons")

    def get_lessons_count(self, obj):
        return getattr(obj, "lessons_count", 0)