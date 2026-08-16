from rest_framework import serializers
from app.models.coin import CoinProduct


class CoinProductSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = CoinProduct
        fields = [
            "id",
            "name",
            "description",
            "price",
            "category",
            "stock",
            "emoji",
            "bg_gradient",
            "image",
            "in_stock",
        ]
        read_only_fields = fields

    def get_in_stock(self, obj):
        return obj.stock > 0

    def get_image(self, obj):
        return obj.get_display_image_url(self.context.get("request"))
