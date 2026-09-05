"""Admin bosh sahifasi uchun sonlar va bo'lim kategoriyalari.

Ilgari bosh sahifadagi har bir kartochka bir xil matnni ko'rsatardi —
«Ma'lumotlarni ko'rish va boshqarish», 19 marta takrorlangan. Ya'ni
sahifa boshqaruv paneli emas, oddiy havolalar ro'yxati edi: admin
"nechta o'quvchi bor?", "nechta buyurtma kutmoqda?" degan savolga javob
olish uchun har bir bo'limni ochib chiqishi kerak edi. Kartochka
tepasidagi "kategoriya" yozuvi ham 19 tadan 13 tasida bir xil edi
("Kontent boshqaruvi"), ya'ni hech narsani ajratmasdi.

Bu modul shu sonlarni bitta joyda hisoblab keshda saqlaydi va har bir
modelga haqiqiy kategoriya beradi.

TEZLIK. Bosh sahifa 20 dan ortiq jadvalni sanaydi. Kichik jadvallarda
`COUNT(*)` arzon, lekin `TestSessionAnswer` kabi jadval 500 ta o'quvchi
bilan yuz minglab qatorga yetadi va Postgres'da `COUNT(*)` butun
jadvalni o'qiydi. Shuning uchun katta jadvallarda planner statistikasi
(`pg_class.reltuples`) ishlatiladi va son "~" belgisi bilan taxminiy
ekani ko'rsatiladi. Natija baribir 2 daqiqa keshlanadi.
"""

import logging

from django.contrib import admin
from django.core.cache import cache
from django.db import connection
from django.template import Library
from django.utils import timezone

register = Library()
logger = logging.getLogger(__name__)

CACHE_KEY = "admin:model-counts"
SUMMARY_CACHE_KEY = "admin:dashboard-summary"
CACHE_TTL = 120

# Shu chegaradan katta jadvallarda aniq COUNT(*) o'rniga taxmin.
EXACT_COUNT_LIMIT = 50_000

# Kartochka tepasidagi kategoriya. Kalit — "app_label.model_name".
MODEL_CATEGORY = {
    "app.user": "Hisoblar",
    "app.studentprofile": "Hisoblar",
    "auth.group": "Hisoblar",
    "app.mentor": "Ta’lim jamoasi",
    "app.branch": "Tashkilot",
    "app.course": "Ta’lim kontenti",
    "app.module": "Ta’lim kontenti",
    "app.lesson": "Ta’lim kontenti",
    "app.question": "Ta’lim kontenti",
    "app.testsession": "Testlar",
    "app.testsessionquestion": "Testlar",
    "app.testsessionanswer": "Testlar",
    "app.studentquestionreward": "Testlar",
    "app.studentmark": "Baho va reyting",
    "app.monthhero": "Baho va reyting",
    "app.coinproduct": "Coin do‘koni",
    "app.coinorder": "Coin do‘koni",
    "app.studentpaymenthistory": "Moliya",
    "app.studentinvoice": "Moliya",
    "app.galleerypost": "Media",
    "app.gallerypost": "Media",
    "app.portfolio": "Media",
}

# Kartochkadagi son yonidagi so'z (birlik shakli).
MODEL_NOUN = {
    "app.user": "foydalanuvchi",
    "app.studentprofile": "o‘quvchi",
    "auth.group": "guruh",
    "app.mentor": "mentor",
    "app.branch": "filial",
    "app.course": "kurs",
    "app.module": "modul",
    "app.lesson": "dars",
    "app.question": "savol",
    "app.testsession": "test",
    "app.testsessionquestion": "savol",
    "app.testsessionanswer": "javob",
    "app.studentquestionreward": "mukofot",
    "app.studentmark": "baho",
    "app.monthhero": "qahramon",
    "app.coinproduct": "mahsulot",
    "app.coinorder": "buyurtma",
    "app.studentpaymenthistory": "to‘lov",
    "app.studentinvoice": "invoys",
    "app.gallerypost": "post",
    "app.portfolio": "ish",
}


def _row_estimates():
    """Postgres planner statistikasi: {"jadval_nomi": taxminiy_qatorlar}."""
    if connection.vendor != "postgresql":
        return {}
    try:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT relname, reltuples::bigint FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE c.relkind = 'r' AND n.nspname = current_schema()"
            )
            return {name: int(rows) for name, rows in cur.fetchall()}
    except Exception:
        logger.debug("pg_class statistikasi o‘qilmadi", exc_info=True)
        return {}


@register.simple_tag
def model_counts():
    """`{"app.studentprofile": {"value": 261, "exact": True}, ...}`."""
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached

    estimates = _row_estimates()
    counts = {}
    for model in admin.site._registry:
        meta = model._meta
        key = f"{meta.app_label}.{meta.model_name}"
        estimate = estimates.get(meta.db_table)
        try:
            if estimate is not None and estimate > EXACT_COUNT_LIMIT:
                counts[key] = {"value": estimate, "exact": False}
            else:
                counts[key] = {
                    "value": model._default_manager.count(),
                    "exact": True,
                }
        except Exception:
            logger.debug("Sonini hisoblab bo‘lmadi: %s", key, exc_info=True)
            counts[key] = None

    cache.set(CACHE_KEY, counts, CACHE_TTL)
    return counts


@register.simple_tag
def dashboard_summary():
    """Sahifa tepasidagi to‘rtta asosiy ko‘rsatkich."""
    cached = cache.get(SUMMARY_CACHE_KEY)
    if cached is not None:
        return cached

    def safe(fn, default=None):
        try:
            return fn()
        except Exception:
            logger.debug("Ko‘rsatkichni hisoblab bo‘lmadi", exc_info=True)
            return default

    from django.urls import reverse

    from app.models.auth import StudentProfile
    from app.models.coin import CoinOrder
    from app.models.question import Lesson, Question
    from app.models.test import TestSession

    month_start = timezone.localdate().replace(day=1)

    def url(name):
        return safe(lambda: reverse(f"admin:app_{name}_changelist"), "")

    def student_hint():
        total = StudentProfile.objects.count()
        active = StudentProfile.objects.filter(user__is_active=True).count()
        if total and active == total:
            return "barchasi faol"
        return f"{active} tasi faol"

    data = [
        {
            # Havola StudentProfile emas, User katalogiga ketadi: bosh
            # sahifada va yon menyuda StudentProfile ataylab yashirilgan
            # (`get_model_perms` bo'sh qaytaradi), o'quvchilar ro'yxati
            # esa "Foydalanuvchilar" katalogi orqali boshqariladi.
            "label": "O‘quvchilar",
            "value": safe(lambda: StudentProfile.objects.count()),
            "hint": safe(student_hint, ""),
            "url": url("user"),
            "tone": "primary",
        },
        {
            "label": "Darslar",
            "value": safe(lambda: Lesson.objects.count()),
            "hint": safe(
                lambda: "{} ta savol bazasi".format(Question.objects.count()), ""
            ),
            "url": url("lesson"),
            "tone": "violet",
        },
        {
            "label": "Bu oydagi testlar",
            "value": safe(
                lambda: TestSession.objects.filter(
                    started_at__date__gte=month_start
                ).count()
            ),
            "hint": safe(
                lambda: "{} tasi tugallanmagan".format(
                    TestSession.objects.filter(is_finished=False).count()
                ),
                "",
            ),
            "url": url("testsession"),
            "tone": "green",
        },
        {
            "label": "Kutayotgan buyurtma",
            "value": safe(
                lambda: CoinOrder.objects.filter(status="pending").count()
            ),
            "hint": safe(
                lambda: "{} tasi hali ko‘rilmagan".format(
                    CoinOrder.objects.filter(is_admin_read=False).count()
                ),
                "",
            ),
            "url": url("coinorder"),
            "tone": "amber",
        },
    ]

    cache.set(SUMMARY_CACHE_KEY, data, CACHE_TTL)
    return data


@register.filter
def count_for(counts, model_key):
    """Shablonda: `{{ counts|count_for:model_key }}` -> `261 ta o‘quvchi`."""
    if not isinstance(counts, dict):
        return ""
    key = str(model_key).lower()
    entry = counts.get(key)
    if not entry:
        return ""
    noun = MODEL_NOUN.get(key, "yozuv")
    prefix = "" if entry.get("exact", True) else "~"
    return f"{prefix}{entry['value']:,} ta {noun}".replace(",", " ")


@register.filter
def category_for(model_key):
    """Kartochka tepasidagi kategoriya nomi."""
    return MODEL_CATEGORY.get(str(model_key).lower(), "Boshqa bo‘limlar")
