from __future__ import annotations

from datetime import date

from django.db.models import Prefetch
from django.utils import timezone

from app.models.auth import StudentProfile
from app.models.month_hero import MonthHero
from app.services.portal.ranking_service import (
    UZ_MONTHS_SHORT,
    build_absolute_photo_url,
    load_mentor_index,
    mentor_name_from_index,
)


DEFAULT_COURSES = ["Python", "Frontend", "Scratch", "Robototexnika"]
DEFAULT_BRANCHES = [
    "Chilonzor", "Yunusobod", "Sergeli", "Mirzo Ulug‘bek",
    "Xadra", "Yashnobod", "Samarqand", "Andijon", "Keles", "Farg‘ona",
]


def month_id(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def month_label(year: int, month: int) -> str:
    return f"{UZ_MONTHS_SHORT[month - 1]} {year}"


def serialize_hero(
    profile: StudentProfile,
    points: int,
    request=None,
    category: str = "",
    mentor_index: dict | None = None,
) -> dict:
    user = profile.user
    course_name = profile.course.name if profile.course else ""
    branch_name = profile.branch.name if profile.branch else ""
    image = build_absolute_photo_url(user, request) or ""
    if mentor_index is None:
        mentor_index = load_mentor_index()
    payload = {
        "name": user.full_name,
        "course": course_name,
        "branch": branch_name,
        "mentor": mentor_name_from_index(mentor_index, profile.branch_id, course_name),
        "points": points,
        "image": image,
        "avatar": image,
    }
    if category:
        payload["category"] = category
    return payload


def heroes_for_period(
    period_date: date,
    request=None,
    *,
    heroes=None,
    mentor_index: dict | None = None,
    fallback_profiles=None,
) -> dict:
    """Bitta oy uchun qahramonlar to'plami.

    `heroes` va `mentor_index` oldindan berilsa bu funksiya BITTA HAM
    so'rov bajarmaydi — `build_heroes_portal` barcha 12 oyni bitta
    so'rovda yuklab, shu yerga uzatadi. Ilgari har oy uchun 3 ta so'rov
    va har bir qahramon uchun alohida mentor so'rovi ketardi (bitta
    so'rovga ~200-400 SQL).
    """
    if mentor_index is None:
        mentor_index = load_mentor_index()

    if heroes is None:
        heroes = list(
            MonthHero.objects
            .filter(period=period_date, is_active=True)
            .select_related(
                "student_profile",
                "student_profile__user",
                "student_profile__course",
                "student_profile__branch",
            )
            .order_by(
                "-points",
                "-student_profile__total_score",
                "student_profile__user__first_name",
            )
        )

    if heroes:
        featured = []
        for hero in heroes[:6]:
            profile = hero.student_profile
            featured.append(
                serialize_hero(
                    profile,
                    hero.points if hero.points is not None else (profile.total_score or 0),
                    request,
                    mentor_index=mentor_index,
                )
            )

        directions = []
        for course_name in DEFAULT_COURSES:
            match = next(
                (
                    h for h in heroes
                    if h.student_profile.course
                    and h.student_profile.course.name.lower() == course_name.lower()
                ),
                None,
            )
            if match:
                profile = match.student_profile
                directions.append(
                    serialize_hero(
                        profile,
                        match.points if match.points is not None else (profile.total_score or 0),
                        request,
                        category=course_name,
                        mentor_index=mentor_index,
                    )
                )

        branches = []
        seen_branches = set()
        for hero in heroes:
            profile = hero.student_profile
            if not profile.branch or profile.branch.name in seen_branches:
                continue
            seen_branches.add(profile.branch.name)
            branches.append(
                serialize_hero(
                    profile,
                    hero.points if hero.points is not None else (profile.total_score or 0),
                    request,
                    category=profile.branch.name,
                    mentor_index=mentor_index,
                )
            )

        return {"featured": featured, "directions": directions, "branches": branches}

    if fallback_profiles is None:
        fallback_profiles = list(
            StudentProfile.objects
            .select_related("user", "course", "branch")
            .filter(user__is_active=True)
            .order_by("-total_score")[:24]
        )
    profile_list = fallback_profiles
    featured = [
        serialize_hero(p, p.total_score or 0, request, mentor_index=mentor_index)
        for p in profile_list[:6]
    ]

    directions = []
    for course_name in DEFAULT_COURSES:
        match = next(
            (p for p in profile_list if p.course and p.course.name.lower() == course_name.lower()),
            None,
        )
        if match:
            directions.append(
                serialize_hero(
                    match, match.total_score or 0, request,
                    category=course_name, mentor_index=mentor_index,
                )
            )

    branches = []
    for branch_name in DEFAULT_BRANCHES:
        match = next(
            (p for p in profile_list if p.branch and p.branch.name == branch_name),
            None,
        )
        if match:
            branches.append(
                serialize_hero(
                    match, match.total_score or 0, request,
                    category=branch_name, mentor_index=mentor_index,
                )
            )

    return {"featured": featured, "directions": directions, "branches": branches}


def available_month_periods(limit: int = 12) -> list[date]:
    periods = list(
        MonthHero.objects
        .filter(is_active=True)
        .values_list("period", flat=True)
        .distinct()
        .order_by("-period")[:limit]
    )
    if periods:
        return periods

    now = timezone.now().date().replace(day=1)
    result = []
    year, month = now.year, now.month
    for _ in range(limit):
        result.append(date(year, month, 1))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return result


def _load_heroes_by_period(periods: list[date]) -> dict:
    """Barcha oylarning qahramonlarini BITTA so'rovda yuklaydi."""
    if not periods:
        return {}
    rows = (
        MonthHero.objects
        .filter(period__in=periods, is_active=True)
        .select_related(
            "student_profile",
            "student_profile__user",
            "student_profile__course",
            "student_profile__branch",
        )
        .order_by(
            "-points",
            "-student_profile__total_score",
            "student_profile__user__first_name",
        )
    )
    grouped: dict = {period: [] for period in periods}
    for hero in rows:
        grouped.setdefault(hero.period, []).append(hero)
    return grouped


def build_heroes_portal(*, month: str | None, view: str, query: str, request=None) -> dict:
    periods = available_month_periods()

    # Ilgari bu sikl har oy uchun 3 ta so'rov va har qahramon uchun
    # alohida mentor so'rovi bajarardi — bitta so'rovga ~200-400 SQL.
    # Endi hamma narsa uchtagina so'rovda yuklanadi.
    mentor_index = load_mentor_index()
    heroes_by_period = _load_heroes_by_period(periods)
    fallback_profiles = None
    if any(not heroes_by_period.get(period) for period in periods):
        fallback_profiles = list(
            StudentProfile.objects
            .select_related("user", "course", "branch")
            .filter(user__is_active=True)
            .order_by("-total_score")[:24]
        )

    months_payload = []
    for period_date in periods:
        year, month_num = period_date.year, period_date.month
        mid = month_id(year, month_num)
        bucket = heroes_for_period(
            period_date,
            request,
            heroes=heroes_by_period.get(period_date, []),
            mentor_index=mentor_index,
            fallback_profiles=fallback_profiles,
        )
        months_payload.append({
            "id": mid,
            "label": month_label(year, month_num),
            "short": UZ_MONTHS_SHORT[month_num - 1],
            **bucket,
        })

    if month:
        active = next((item for item in months_payload if item["id"] == month), None)
    else:
        active = months_payload[0] if months_payload else None

    if not active and months_payload:
        active = months_payload[0]

    if active and query:
        q = query.lower()

        def match_hero(hero):
            text = " ".join([
                hero.get("name", ""),
                hero.get("course", ""),
                hero.get("branch", ""),
                hero.get("mentor", ""),
                hero.get("category", ""),
            ]).lower()
            return q in text

        # `active` — `months_payload` ichidagi aynan o'sha obyekt. Uni
        # joyida o'zgartirish qidiruv natijasini `months` ro'yxatiga ham
        # yuqtirardi. Shuning uchun nusxa olamiz.
        active = dict(active)
        for key in ("featured", "directions", "branches"):
            active[key] = [hero for hero in active.get(key, []) if match_hero(hero)]

    heroes_key = "featured"
    if view == "directions":
        heroes_key = "directions"
    elif view == "branches":
        heroes_key = "branches"

    return {
        "months": months_payload,
        "active_month": active,
        "view": view,
        "heroes": active.get(heroes_key, []) if active else [],
    }
