from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from app.services import enter_password_via_external_api
from app.services.auth_external_api import PDPAPIError


class StudentProfileSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    full_name = serializers.SerializerMethodField()
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    phone_number = serializers.CharField(read_only=True)
    image = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return obj.full_name

    def get_image(self, obj):
        request = self.context.get("request")
        profile = getattr(obj, "student_profile", None)

        if profile and profile.avatar_url:
            return profile.avatar_url

        if not obj.photo:
            return None

        if request:
            return request.build_absolute_uri(obj.photo.url)

        return obj.photo.url

    def get_avatar(self, obj):
        first = obj.first_name[:1].upper() if obj.first_name else ""
        last = obj.last_name[:1].upper() if obj.last_name else ""

        avatar = f"{first}{last}"

        if avatar:
            return avatar

        if obj.phone_number:
            return obj.phone_number[-2:]

        return None


class StudentProfileImageUpdateSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True)

    def validate_image(self, value):
        max_size = 5 * 1024 * 1024

        if value.size > max_size:
            raise serializers.ValidationError(
                "Rasm hajmi 5MB dan oshmasligi kerak."
            )

        allowed_content_types = ["image/jpeg", "image/png", "image/webp"]
        content_type = getattr(value, "content_type", None)

        if content_type not in allowed_content_types:
            raise serializers.ValidationError(
                "Faqat JPG, PNG yoki WEBP formatdagi rasmlar qabul qilinadi."
            )

        return value

    def update(self, instance, validated_data):
        instance.photo = validated_data["image"]
        instance.save(update_fields=["photo"])
        return instance


class StudentPasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    def _has_real_local_password(self, user):
        password = (user.password or "").strip()

        if not password:
            return False

        if password.startswith("!"):
            return False

        return user.has_usable_password()

    def _check_external_password(self, user, password):
        phone_number = user.phone_number

        phone_variants = []

        if phone_number:
            phone_variants.append(phone_number)

            if phone_number.startswith("+"):
                phone_variants.append(phone_number[1:])

            if phone_number.startswith("998"):
                phone_variants.append(f"+{phone_number}")

        checked_phones = []

        for phone in phone_variants:
            if not phone or phone in checked_phones:
                continue

            checked_phones.append(phone)

            try:
                enter_password_via_external_api(
                    phone_number=phone,
                    password=password,
                )
                return True
            except PDPAPIError:
                continue

        return False

    def validate_old_password(self, value):
        user = self.context["request"].user

        # 1) Agar local Django password haqiqatan mavjud bo‘lsa, local tekshiramiz
        if self._has_real_local_password(user):
            if user.check_password(value):
                return value

            # Local password noto‘g‘ri bo‘lsa ham PDP tarafdan ham tekshirib ko‘ramiz
            if self._check_external_password(user, value):
                return value

            raise serializers.ValidationError("Eski parol noto‘g‘ri.")

        # 2) Agar local password yo‘q yoki bo‘sh bo‘lsa, PDP external parolni tekshiramiz
        if self._check_external_password(user, value):
            return value

        raise serializers.ValidationError("Eski parol noto‘g‘ri.")

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {
                    "confirm_password": "Yangi parollar bir xil emas."
                }
            )

        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {
                    "new_password": "Yangi parol eski paroldan farq qilishi kerak."
                }
            )

        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user