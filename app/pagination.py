"""Orqaga mos paginatsiya.

Muammo: ro'yxat endpointlari (to'lovlar, invoyslar, galereya, darslar,
reyting) hech qanday chegarasiz butun jadvalni qaytarardi. Bir necha ming
yozuvli o'quvchida bu bitta so'rovda megabaytlab JSON va sekundlab
serializatsiya degani.

Yechim ikki qatlamli:

1. `?page=` yoki `?limit=` yuborilmasa javob shakli **o'zgarmaydi** — eski
   frontend hech narsa sezmaydi. Lekin `HARD_MAX` chegarasi baribir
   qo'llanadi, ya'ni bitta so'rov hech qachon 500 yozuvdan ko'pini
   qaytarmaydi.
2. `?page=2&limit=50` yuborilsa to'liq paginatsiya ishlaydi va javobga
   `meta` bloki qo'shiladi.
"""

from collections.abc import Sized

from django.conf import settings
from rest_framework.pagination import PageNumberPagination


DEFAULT_PAGE_SIZE = getattr(settings, "REST_FRAMEWORK", {}).get("PAGE_SIZE", 50)
HARD_MAX = 500


class OptionalPageNumberPagination(PageNumberPagination):
    """`?page=` berilmasa paginatsiya qilinmaydi (eski xatti-harakat)."""

    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = "limit"
    max_page_size = HARD_MAX

    def paginate_queryset(self, queryset, request, view=None):
        if not self._wants_pagination(request):
            return None
        return super().paginate_queryset(queryset, request, view)

    @staticmethod
    def _wants_pagination(request):
        params = getattr(request, "query_params", None) or {}
        return bool(params.get("page") or params.get("limit") or params.get("page_size"))


def _int_param(params, *names, default=None, minimum=1, maximum=None):
    for name in names:
        raw = params.get(name)
        if raw in (None, ""):
            continue
        try:
            value = int(raw)
        except (TypeError, ValueError):
            continue
        if value < minimum:
            value = minimum
        if maximum is not None and value > maximum:
            value = maximum
        return value
    return default


def wants_pagination(request) -> bool:
    params = getattr(request, "query_params", None) or {}
    return bool(params.get("page") or params.get("limit") or params.get("page_size"))


def paginate_iterable(request, items, *, default_limit=None, hard_max=HARD_MAX):
    """APIView'lar uchun qo'lda paginatsiya.

    Qaytaradi: `(kesilgan_ro'yxat, meta_yoki_None)`.

    `meta` faqat mijoz paginatsiya so'raganda qaytariladi — shunda view
    uni javobga qo'shadi. Aks holda `None` qaytadi va view eski shaklni
    saqlaydi.
    """
    params = getattr(request, "query_params", None) or {}
    default_limit = default_limit or DEFAULT_PAGE_SIZE

    if not wants_pagination(request):
        # Paginatsiya so'ralmagan: eski shakl, lekin qattiq chegara bilan.
        capped = list(items[:hard_max]) if _is_sliceable(items) else list(items)[:hard_max]
        return capped, None

    limit = _int_param(params, "limit", "page_size", default=default_limit, maximum=hard_max)
    page = _int_param(params, "page", default=1)

    total = _count(items)
    offset = (page - 1) * limit
    window = items[offset:offset + limit]
    page_items = list(window)

    pages = (total + limit - 1) // limit if limit else 1
    meta = {
        "page": page,
        "limit": limit,
        "total": total,
        "pages": pages,
        "has_next": page < pages,
        "has_previous": page > 1,
    }
    return page_items, meta


def _is_sliceable(items):
    return hasattr(items, "__getitem__")


def _count(items):
    counter = getattr(items, "count", None)
    if callable(counter):
        try:
            return counter()
        except TypeError:
            pass
    if isinstance(items, Sized):
        return len(items)
    return len(list(items))
