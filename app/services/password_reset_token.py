from django.core import signing
from django.conf import settings

PRE_RESET_TOKEN_SALT = "pre-reset-password"
PRE_RESET_TOKEN_MAX_AGE = getattr(settings, "PRE_RESET_TOKEN_MAX_AGE", 300)


class PreResetTokenError(Exception):
    pass


def make_pre_reset_token(*, phone_number: str, sms_code_id: str, sms_code: str) -> str:
    payload = {
        "phone_number": phone_number,
        "sms_code_id": sms_code_id,
        "sms_code": sms_code,
        "purpose": "set_new_password",
    }
    return signing.dumps(payload, salt=PRE_RESET_TOKEN_SALT)


def parse_pre_reset_token(token: str) -> dict:
    try:
        data = signing.loads(
            token,
            salt=PRE_RESET_TOKEN_SALT,
            max_age=PRE_RESET_TOKEN_MAX_AGE,
        )
    except signing.SignatureExpired:
        raise PreResetTokenError("Pre reset token muddati tugagan.")
    except signing.BadSignature:
        raise PreResetTokenError("Pre reset token noto‘g‘ri.")

    if data.get("purpose") != "set_new_password":
        raise PreResetTokenError("Pre reset token noto‘g‘ri maqsad uchun yaratilgan.")

    return data