from rest_framework import serializers

from app.models import Course


class CourseCatalogSerializer(serializers.ModelSerializer):
    image = serializers.CharField(source="image_url", read_only=True)
    module_count = serializers.IntegerField(read_only=True)
    lesson_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = (
            "id",
            "name",
            "description",
            "image",
            "module_count",
            "lesson_count",
        )
