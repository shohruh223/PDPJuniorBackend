from __future__ import annotations

from datetime import date

from django.db.models import Prefetch
from django.utils import timezone

from app.models.auth import StudentProfile
from app.models.month_hero import MonthHero
from app.services.portal.ranking_service import (
    UZ_MONTHS_SHORT,
    build_absolute_photo_url,
    resolve_mentor_name,
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


def serialize_hero(profile: StudentProfile, points: int, request=None, category: str = "") -> dict:
    user = profile.user
    course_name = profile.course.name if profile.course else "Python"
    branch_name = profile.branch.name if profile.branch else ""
    image = build_absolute_photo_url(user, request) or ""
    payload = {
        "name": user.full_name,
        "course": course_name,
        "branch": branch_name,
        "mentor": resolve_mentor_name(profile.branch_id, course_name),
        "points": points,
        "image": image,
        "avatar": image,
    }
    if category:
        payload["category"] = category
    return payload


def heroes_for_period(period_date: date, request=None) -> dict:
    heroes = (
        MonthHero.objects
        .filter(period=period_date, is_active=True)
        .select_related(
            "student_profile",
            "student_profile__user",
            "student_profile__course",
            "student_profile__branch",
        )
        .order_by("-points", "-student_profile__total_score", "student_profile__user__first_name")
    )

    if heroes.exists():
        featured = []
        for hero in heroes[:6]:
            profile = hero.student_profile
            featured.append(
                serialize_hero(profile, hero.points or profile.total_score or 0, request)
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
                        match.points or profile.total_score or 0,
                        request,
                        category=course_name,
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
                    hero.points or profile.total_score or 0,
                    request,
                    category=profile.branch.name,
                )
            )

        return {"featured": featured, "directions": directions, "branches": branches}

    profiles = (
        StudentProfile.objects
        .select_related("user", "course", "branch")
        .filter(user__is_active=True)
        .order_by("-total_score")[:24]
    )
    profile_list = list(profiles)
    featured = [
        serialize_hero(p, p.total_score or 0, request) for p in profile_list[:6]
    ]

    directions = []
    for course_name in DEFAULT_COURSES:
        match = next(
            (p for p in profile_list if p.course and p.course.name.lower() == course_name.lower()),
            None,
        )
        if match:
            directions.append(
                serialize_hero(match, match.total_score or 0, request, category=course_name)
            )

    branches = []
    for branch_name in DEFAULT_BRANCHES:
        match = next(
            (p for p in profile_list if p.branch and p.branch.name == branch_name),
            None,
        )
        if match:
            branches.append(
                serialize_hero(match, match.total_score or 0, request, category=branch_name)
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


def build_heroes_portal(*, month: str | None, view: str, query: str, request=None) -> dict:
    periods = available_month_periods()
    months_payload = []

    for period_date in periods:
        year, month_num = period_date.year, period_date.month
        mid = month_id(year, month_num)
        bucket = heroes_for_period(period_date, request)
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
