from rest_framework import serializers

from app.models import Course
from app.serializers.media import build_file_url


class CourseCatalogSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
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

    def get_image(self, obj):
        return build_file_url(obj.image_url, self.context.get("request"))
