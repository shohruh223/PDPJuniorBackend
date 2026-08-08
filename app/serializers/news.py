from rest_framework import serializers
from app.models import News


class NewsSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = News
        fields = [
            "id",
            "title",
            "date",
            "type",
            "description",
            "color",
            "icon",
        ]