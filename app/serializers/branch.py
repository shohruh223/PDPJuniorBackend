from rest_framework import serializers

from app.models.branch import Branch
from app.serializers.media import build_file_url


class BranchSerializer(serializers.ModelSerializer):
    mapUrl = serializers.URLField(source="map_url", read_only=True)
    isOpened = serializers.CharField(source="is_opened", read_only=True)
    image = serializers.SerializerMethodField()
    lat = serializers.DecimalField(source="latitude", max_digits=10, decimal_places=7, read_only=True)
    lng = serializers.DecimalField(source="longitude", max_digits=10, decimal_places=7, read_only=True)
    album = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = (
            "id",
            "name",
            "address",
            "phone",
            "hours",
            "image",
            "district",
            "lat",
            "lng",
            "mapUrl",
            "isOpened",
            "album",
        )
        read_only_fields = fields

    def get_image(self, obj):
        return build_file_url(obj.image_url, self.context.get("request"))

    def get_album(self, obj):
        request = self.context.get("request")
        album = obj.album or []

        result = []

        for item in album:
            if not isinstance(item, dict):
                continue

            media_type = item.get("type")
            path = item.get("url")

            if not path:
                continue

            result.append(
                {
                    "type": media_type,
                    "url": build_file_url(path, request),
                }
            )

        return result
