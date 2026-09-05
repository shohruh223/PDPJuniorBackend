"""Kesh oldindan to'ldirish (cache warming).

Reyting va oy qahramonlari eng qimmat ommaviy so'rovlar. Kesh muddati
tuganda birinchi kelgan foydalanuvchi ularni qayta hisoblashga majbur
bo'ladi — 500 kishilik yukda bu sezilarli "tishlar" beradi.

Bu vazifa Celery beat orqali har 5 daqiqada ishlaydi va eng ko'p
so'raladigan variantlarni oldindan hisoblab qo'yadi, ya'ni foydalanuvchi
hech qachon sovuq keshga tushmaydi.
"""

import logging

from django.conf import settings

from app.services.portal import cache_layer

logger = logging.getLogger(__name__)


def warm_ranking() -> int:
    from app.services.portal.ranking_service import get_ranking_list

    warmed = 0
    for period in ("total", "month"):
        key = cache_layer.make_key(
            "ranking", scope="all", period=period, context="", q="", host="-"
        )
        try:
            cache_layer.cached_call(
                key,
                getattr(settings, "CACHE_TTL_RANKING", 120),
                lambda p=period: get_ranking_list(scope="all", period=p, request=None),
            )
            warmed += 1
        except Exception:
            logger.warning("Reyting keshini to'ldirib bo'lmadi (%s)", period, exc_info=True)
    return warmed


def warm_heroes() -> int:
    from app.services.portal.heroes_service import build_heroes_portal

    warmed = 0
    for view in ("all", "directions", "branches"):
        key = cache_layer.make_key("heroes", month="-", view=view, q="", host="-")
        try:
            cache_layer.cached_call(
                key,
                getattr(settings, "CACHE_TTL_HEROES", 300),
                lambda v=view: build_heroes_portal(month=None, view=v, query="", request=None),
            )
            warmed += 1
        except Exception:
            logger.warning("Heroes keshini to'ldirib bo'lmadi (%s)", view, exc_info=True)
    return warmed


def warm_all() -> dict:
    return {"ranking": warm_ranking(), "heroes": warm_heroes()}
