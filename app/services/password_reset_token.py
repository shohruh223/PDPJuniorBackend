"""Parolni tiklash oqimidagi qisqa muddatli token.

MUAMMO (eski yechim). Token `django.core.signing.dumps()` bilan
yaratilardi va uning ichida `sms_code` **ochiq matnda** turardi.
`signing.dumps` faqat **imzolaydi**, shifrlamaydi — yozuv oddiy base64
JSON, ya'ni tokenni ko'rgan har kim (brauzer xotirasi, proxy loglari,
xato hisobotlari, ekran surati) foydalanuvchining SMS kodini o'qiy
olardi.

YANGI YECHIM. Mijozga faqat **tasodifiy identifikator** beriladi, SMS
kod esa server tomonda (kesh — production'da Redis) saqlanadi va
`PRE_RESET_TOKEN_MAX_AGE` dan keyin o'z-o'zidan yo'qoladi. Token bir
marta ishlatiladi: parol o'rnatilgach yozuv darhol o'chiriladi, ya'ni
o'g'irlangan token qayta ishlatilmaydi.

Kesh vaqtincha ishlamay qolsa (Redis yiqilishi) `signing` ga qaytish
yo'q — bunda foydalanuvchi SMS kodni qaytadan so'rashi kerak. Bu
ataylab: xavfsizlikni qulaylik uchun qurbon qilmaymiz.
"""

import secrets

from django.conf import settings
from django.core.cache import cache

PRE_RESET_TOKEN_SALT = "pre-reset-password"
PRE_RESET_TOKEN_MAX_AGE = getattr(settings, "PRE_RESET_TOKEN_MAX_AGE", 300)

_CACHE_PREFIX = "pwreset:"


class PreResetTokenError(Exception):
    pass


def _key(token: str) -> str:
    return f"{_CACHE_PREFIX}{token}"


def make_pre_reset_token(*, phone_number: str, sms_code_id: str, sms_code: str) -> str:
    """Tasodifiy token yaratadi va maxfiy ma'lumotni server tomonda saqlaydi."""
    token = secrets.token_urlsafe(32)
    payload = {
        "phone_number": phone_number,
        "sms_code_id": sms_code_id,
        "sms_code": sms_code,
        "purpose": "set_new_password",
    }
    try:
        cache.set(_key(token), payload, PRE_RESET_TOKEN_MAX_AGE)
    except Exception as exc:  # kesh yo'q — tokenni bermaymiz
        raise PreResetTokenError(
            "Hozir parolni tiklash mumkin emas. Birozdan keyin qayta urinib ko‘ring."
        ) from exc
    return token


def parse_pre_reset_token(token: str, *, consume: bool = False) -> dict:
    """Tokenni tekshiradi. `consume=True` bo'lsa yozuvni o'chiradi (bir martalik)."""
    if not token or not isinstance(token, str):
        raise PreResetTokenError("Pre reset token noto‘g‘ri.")

    try:
        data = cache.get(_key(token))
    except Exception:
        data = None

    if not data:
        # Yo'q, muddati tugagan yoki allaqachon ishlatilgan — farqni
        # oshkor qilmaymiz.
        raise PreResetTokenError("Pre reset token noto‘g‘ri yoki muddati tugagan.")

    if data.get("purpose") != "set_new_password":
        raise PreResetTokenError("Pre reset token noto‘g‘ri maqsad uchun yaratilgan.")

    if consume:
        try:
            cache.delete(_key(token))
        except Exception:
            pass

    return data


def revoke_pre_reset_token(token: str) -> None:
    try:
        cache.delete(_key(token))
    except Exception:
        pass
