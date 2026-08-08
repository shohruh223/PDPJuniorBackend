import re
from rest_framework import serializers


def validate_uzb_phone(value):
    if not re.match(r"^\+998\d{9}$", value):
        raise serializers.ValidationError(
            "Telefon raqami +998XXXXXXXXX formatida bo‘lishi kerak."
        )
    return value


class CheckPhoneSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=13)

    def validate_phone_number(self, value):
        return validate_uzb_phone(value)


class EnterPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=13)
    password = serializers.CharField(write_only=True)

    def validate_phone_number(self, value):
        return validate_uzb_phone(value)


class CheckSMSCodeSerializer(serializers.Serializer):
    sms_code_id = serializers.CharField()
    sms_code = serializers.CharField()
    phone_number = serializers.CharField(max_length=13)

    def validate_phone_number(self, value):
        return validate_uzb_phone(value)


class ForgotPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=13)

    def validate_phone_number(self, value):
        return validate_uzb_phone(value)


class VerifySMSCodeSerializer(serializers.Serializer):
    sms_code_id = serializers.CharField()
    sms_code = serializers.CharField()
    phone_number = serializers.CharField(max_length=13)

    def validate_phone_number(self, value):
        return validate_uzb_phone(value)


class SetNewPasswordSerializer(serializers.Serializer):
    pre_reset_token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=6)
    repeat_password = serializers.CharField(write_only=True, min_length=6)

    def validate_phone_number(self, value):
        return validate_uzb_phone(value)

    def validate(self, attrs):
        if attrs["password"] != attrs["repeat_password"]:
            raise serializers.ValidationError({
                "repeat_password": "Parollar bir xil bo‘lishi kerak."
            })
        return attrs