"""Ommaviy endpointlar uchun kesh qatlami.

`/api/ranking`, `/api/heroes`, `/api/gallery`, `/api/branches`,
`/api/mentors`, `/api/courses`, `/api/portfolios` — bularning hammasi
autentifikatsiyasiz va barcha foydalanuvchi uchun **bir xil** javob
qaytaradi. Ya'ni 500 o'quvchi bir vaqtda sahifani ochsa, baza bir xil
ishni 500 marta bajaradi.

Bu modul ikkita muammoni hal qiladi:

1. **Takroriy hisoblash.** Natija Redis'da TTL bilan saqlanadi.
2. **Cache stampede.** Kesh muddati tugagan lahzada 500 ta so'rov bir
   vaqtda kelsa, hammasi qayta hisoblashga urinardi. Bu yerda qisqa
   muddatli qulf bor: faqat bittasi hisoblaydi, qolganlari eskirgan
   nusxani oladi (u bir muncha vaqt "grace" oynasida saqlanadi).

Kesh yiqilsa hech narsa buzilmaydi — funksiya oddiygina qayta
hisoblanadi.
"""

import hashlib
import logging
import time

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Eskirgan qiymat qancha vaqt saqlansin (stampede paytida shu qaytariladi).
GRACE_SECONDS = 120
LOCK_SECONDS = 20


def make_key(prefix: str, **parts) -> str:
    """Barqaror kesh kaliti. Uzun qismlar hash qilinadi."""
    raw = "|".join(f"{k}={parts[k]}" for k in sorted(parts))
    if len(raw) > 120:
        raw = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return f"pub:{prefix}:{raw}"


def cached_call(key: str, ttl: int, producer):
    """Natijani keshdan oladi, bo'lmasa `producer()` ni chaqiradi.

    Saqlangan yozuv: `{"v": qiymat, "exp": muddati}`. TTL tugaganidan
    keyin ham yozuv `GRACE_SECONDS` davomida keshda qoladi, shuning uchun
    qayta hisoblash paytida boshqalar bo'sh javob olmaydi.
    """
    now = time.time()

    try:
        entry = cache.get(key)
    except Exception:
        entry = None

    if isinstance(entry, dict) and "v" in entry:
        if entry.get("exp", 0) > now:
            return entry["v"]

        # Muddati tugadi: faqat bitta so'rov qayta hisoblaydi.
        lock = f"{key}:lock"
        got_lock = False
        try:
            got_lock = bool(cache.add(lock, "1", LOCK_SECONDS))
        except Exception:
            got_lock = True

        if not got_lock:
            return entry["v"]  # eskirgan, lekin to'g'ri shakldagi javob

        try:
            value = producer()
        except Exception:
            try:
                cache.delete(lock)
            except Exception:
                pass
            raise
        _store(key, value, ttl)
        try:
            cache.delete(lock)
        except Exception:
            pass
        return value

    value = producer()
    _store(key, value, ttl)
    return value


def _store(key: str, value, ttl: int) -> None:
    try:
        cache.set(key, {"v": value, "exp": time.time() + ttl}, ttl + GRACE_SECONDS)
    except Exception:
        logger.debug("Keshga yozib bo'lmadi: %s", key, exc_info=True)


def invalidate_prefix(prefix: str) -> None:
    """Berilgan prefiksdagi barcha kalitlarni o'chiradi (Redis'da).

    LocMemCache uchun `delete_pattern` yo'q — u holda hech narsa
    qilinmaydi va yozuvlar TTL bilan tabiiy eskiradi.
    """
    pattern = f"*pub:{prefix}:*"
    try:
        delete_pattern = getattr(cache, "delete_pattern", None)
        if callable(delete_pattern):
            delete_pattern(pattern)
    except Exception:
        logger.debug("Kesh prefiksini tozalab bo'lmadi: %s", prefix, exc_info=True)


def request_host(request) -> str:
    """Kesh kalitiga host qo'shiladi — javobda absolyut URL'lar bor."""
    if request is None:
        return "-"
    try:
        return request.get_host()
    except Exception:
        return "-"
