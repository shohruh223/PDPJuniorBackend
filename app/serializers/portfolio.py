from rest_framework import serializers

from app.models.portfolio import Portfolio
from app.serializers.media import build_file_url


class PortfolioSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = (
            "id",
            "name",
            "url",
            "image",
            "desc",
            "student",
            "category",
            "year",
        )
        read_only_fields = fields

    def get_image(self, obj):
        request = self.context.get("request")
        data = obj.image or {}

        if isinstance(data, dict):
            path = data.get("url")
        else:
            path = None

        return build_file_url(path, request)