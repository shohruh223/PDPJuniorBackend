"""Kesh invalidatsiyasi.

Ommaviy endpointlar Redis'da keshlanadi (`app/services/portal/cache_layer`).
Admin panelda kontent o'zgarganda kesh TTL tugashini kutmasligi kerak —
bu yerdagi signal handlerlar tegishli prefiksni darhol tozalaydi.

Modul qulfi keshi ham shu yerda: ilgari u faqat test yakunlanganda
tozalanardi, ya'ni bo'sh darsga savol qo'shilsa o'quvchi bir soatgacha
eski qulf holatini ko'rardi.
"""

import logging

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from app.models.branch import Branch
from app.models.coin import CoinProduct
from app.models.gallery import GalleryPost
from app.models.mentors import Mentor
from app.models.month_hero import MonthHero
from app.models.portfolio import Portfolio
from app.models.question import Course, Lesson, Module, Question
from app.services.portal.cache_layer import invalidate_prefix

logger = logging.getLogger(__name__)

# Model -> tozalanadigan kesh prefikslari
_PREFIX_MAP = {
    Branch: ("branches", "mentors", "ranking", "heroes"),
    Mentor: ("mentors", "ranking", "heroes"),
    Course: ("courses", "ranking", "heroes"),
    GalleryPost: ("gallery",),
    Portfolio: ("portfolios",),
    MonthHero: ("heroes",),
    CoinProduct: ("shop",),
}


def _invalidate_for(model):
    for prefix in _PREFIX_MAP.get(model, ()):
        invalidate_prefix(prefix)


@receiver(post_save)
@receiver(post_delete)
def clear_public_cache(sender, **kwargs):
    if sender in _PREFIX_MAP:
        _invalidate_for(sender)


@receiver(post_save, sender=Question)
@receiver(post_delete, sender=Question)
@receiver(post_save, sender=Lesson)
@receiver(post_delete, sender=Lesson)
@receiver(post_save, sender=Module)
@receiver(post_delete, sender=Module)
def clear_progress_cache(sender, **kwargs):
    """Kurs tarkibi o'zgarsa modul qulfi keshi eskiradi.

    Kalitlar foydalanuvchi bo'yicha bo'lgani uchun ularni birma-bir
    o'chirish qimmat. Buning o'rniga "avlod" (generation) raqamini
    oshiramiz — barcha eski kalitlar avtomatik yaroqsiz bo'ladi.
    """
    from app.services.student.test_cache_service import bump_progress_generation

    try:
        bump_progress_generation()
    except Exception:
        logger.debug("Progress kesh avlodini oshirib bo'lmadi", exc_info=True)
    invalidate_prefix("courses")
