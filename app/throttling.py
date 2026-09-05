"""Rate limiting.

Ilgari loyihada hech qanday throttle yo'q edi: bitta skript
`/auth/sms/resend` ni cheksiz chaqirib SMS balansni yoqib yuborishi yoki
`/api/ranking` ni bombardimon qilib bazani cho'ktirishi mumkin edi.

Bu yerdagi klasslar ikki qatlam hosil qiladi:

* `BurstAnonThrottle` / `BurstUserThrottle` — barcha endpointlar uchun
  umumiy shift. Ular DRF ning standart klasslariga o'xshaydi, lekin:
  - `/health` va `/admin` yo'llariga tegmaydi;
  - kesh ishlamay qolsa so'rovni **bloklamaydi** (fail-open) — Redis
    yiqilganda sayt to'xtab qolmasligi kerak.
* `ScopedRateThrottle` merosxo'rlari — qimmat endpointlar uchun
  (`login`, `sms`, `password`, `test_write`, `shop_write`, `sync`).

Barcha tezliklar `settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]` da,
ular esa env o'zgaruvchilaridan o'qiladi.
"""

import logging

from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle

logger = logging.getLogger(__name__)

EXEMPT_PREFIXES = ("/health", "/admin", "/static")


def _client_ip(request):
    """Proxy ortida haqiqiy IP `X-Forwarded-For` da keladi."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class _SafeThrottleMixin:
    """Kesh ishlamasa so'rovni o'tkazib yuboradi va yo'llarni istisno qiladi."""

    def allow_request(self, request, view):
        path = getattr(request, "path", "") or ""
        if path.startswith(EXEMPT_PREFIXES):
            return True
        try:
            return super().allow_request(request, view)
        except Exception:  # kesh yiqilgan — saytni to'xtatmaymiz
            logger.warning("Throttle keshi ishlamadi, so'rov o'tkazildi", exc_info=True)
            return True

    def get_ident(self, request):
        if getattr(request, "user", None) is not None and request.user.is_authenticated:
            return super().get_ident(request)
        return _client_ip(request) or super().get_ident(request)


class BurstAnonThrottle(_SafeThrottleMixin, AnonRateThrottle):
    scope = "anon"


class BurstUserThrottle(_SafeThrottleMixin, UserRateThrottle):
    scope = "user"


class SafeScopedThrottle(_SafeThrottleMixin, ScopedRateThrottle):
    """View'da `throttle_scope = "..."` orqali ishlatiladi."""


class AuthEndpointThrottle(_SafeThrottleMixin, AnonRateThrottle):
    """Login / parol tekshirish — IP bo'yicha qattiq cheklov."""

    scope = "auth"


class SmsThrottle(_SafeThrottleMixin, AnonRateThrottle):
    """SMS yuborish va qayta yuborish — eng qimmat operatsiya."""

    scope = "sms"

    def get_cache_key(self, request, view):
        """IP bilan birga telefon raqamini ham hisobga oladi.

        Aks holda bitta IP ortidagi maktab tarmog'i bir-birini bloklaydi,
        yoki bitta raqamga turli IP'lardan SMS yog'diriladi.
        """
        ident = _client_ip(request) or self.get_ident(request)
        phone = ""
        data = getattr(request, "data", None)
        if isinstance(data, dict):
            phone = str(data.get("phone_number") or data.get("phoneNumber") or "")
        return self.cache_format % {"scope": self.scope, "ident": f"{ident}:{phone}"}


class PasswordThrottle(_SafeThrottleMixin, UserRateThrottle):
    """Parol o'zgartirish — tashqi API'ga uzatiladi, shuning uchun cheklanadi."""

    scope = "password"


class TestWriteThrottle(_SafeThrottleMixin, UserRateThrottle):
    """Test topshirish yozuvlari: start / answer / result."""

    scope = "test_write"


class ShopWriteThrottle(_SafeThrottleMixin, UserRateThrottle):
    """Do'kon buyurtmasi — pul bilan bog'liq, ehtiyotkorlik bilan."""

    scope = "shop_write"


class SyncThrottle(_SafeThrottleMixin, UserRateThrottle):
    """Tashqi PDP API bilan sinxronlashni majburlaydigan endpointlar."""

    scope = "sync"
