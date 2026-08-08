from rest_framework import serializers

from app.models import Course, StudentMark


class MarksCourseSerializer(serializers.ModelSerializer):
    image = serializers.CharField(source="image_url", read_only=True)

    class Meta:
        model = Course
        fields = ("id", "name", "description", "image")


class MarkRecordSerializer(serializers.ModelSerializer):
    date = serializers.DateField(source="record_date", read_only=True)
    lesson_id = serializers.IntegerField(read_only=True, allow_null=True)
    lesson_name = serializers.CharField(
        source="lesson.name", read_only=True, allow_null=True
    )

    class Meta:
        model = StudentMark
        fields = (
            "id",
            "date",
            "attendance",
            "grade",
            "verified",
            "lesson_id",
            "lesson_name",
        )


class MarksStudentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    group = serializers.CharField()
    avatar = serializers.CharField(allow_null=True)
    records = MarkRecordSerializer(many=True)
