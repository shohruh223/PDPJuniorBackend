from __future__ import annotations

from django.db.models import Count, Prefetch, Q

from app.models.auth import StudentProfile
from app.models.mentors import Mentor
from app.models.question import Course, Lesson, Module
from app.services.profile_image_service import build_profile_image_url


UZ_MONTHS_SHORT = [
    "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
    "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr",
]


def build_absolute_photo_url(user, request=None):
    return build_profile_image_url(user, request=request)


def resolve_mentor_name(branch_id, course_name: str | None) -> str:
    if not branch_id:
        return ""
    mentors = Mentor.objects.filter(
        branch_id=branch_id,
        is_active=True,
        branch__is_active=True,
    )
    if course_name:
        match = mentors.filter(role__iexact=course_name).first()
        if match:
            return match.name
    mentor = mentors.first()
    return mentor.name if mentor else ""


def estimate_streak(profile: StudentProfile) -> int:
    if profile.streak_days:
        return profile.streak_days
    percent = profile.attendance_average_percent or 0
    if percent <= 0:
        return 0
    return max(1, min(30, int(round(percent / 7))))


def serialize_ranking_student(profile: StudentProfile, request=None, period: str = "total") -> dict:
    user = profile.user
    course_name = profile.course.name if profile.course else "Python"
    branch_name = profile.branch.name if profile.branch else "PDP Junior"
    avatar = build_absolute_photo_url(user, request)

    total_points = profile.total_score or 0
    monthly_points = profile.local_test_score or max(0, int(total_points * 0.18))

    return {
        "id": str(profile.id),
        "name": user.full_name,
        "course": course_name,
        "branch": branch_name,
        "mentor": resolve_mentor_name(profile.branch_id, course_name),
        "avatar": avatar or "",
        "totalPoints": total_points,
        "monthlyPoints": monthly_points,
        "streak": estimate_streak(profile),
        "level": profile.group_name or "P-9",
        "score": monthly_points if period == "month" else total_points,
    }


def get_ranking_list(
    *,
    scope: str = "all",
    period: str = "total",
    context: str = "",
    query: str = "",
    request=None,
    limit: int = 100,
) -> list[dict]:
    qs = (
        StudentProfile.objects
        .select_related("user", "course", "branch")
        .filter(user__is_active=True, user__role="student")
    )

    if scope == "course" and context:
        qs = qs.filter(course__name__iexact=context)
    elif scope == "branch" and context:
        qs = qs.filter(branch__name__iexact=context)

    if query:
        qs = qs.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(group_name__icontains=query)
            | Q(course__name__icontains=query)
            | Q(branch__name__icontains=query)
        )

    order_field = "-local_test_score" if period == "month" else "-total_score"
    qs = qs.order_by(order_field, "user__first_name")[:limit]

    return [serialize_ranking_student(profile, request, period) for profile in qs]


def get_student_course(user):
    if not hasattr(user, "student_profile"):
        return None
    profile = user.student_profile
    if profile.course:
        return profile.course
    group_course_name = profile.resolve_course_name_from_group()
    if group_course_name:
        return Course.objects.filter(name__iexact=group_course_name).first()
    return None


def get_modules_with_lessons(course: Course):
    lessons_qs = (
        Lesson.objects.filter(course=course)
        .annotate(questions_count=Count("questions"))
        .order_by("order", "id")
    )
    modules = (
        Module.objects.filter(course=course)
        .annotate(lessons_count=Count("lessons", distinct=True))
        .prefetch_related(Prefetch("lessons", queryset=lessons_qs))
        .order_by("order", "id")
    )
    return modules


def serialize_lesson_item(lesson: Lesson) -> dict:
    questions_count = getattr(lesson, "questions_count", None)
    if questions_count is None:
        questions_count = lesson.questions.count()
    return {
        "id": lesson.id,
        "name": lesson.name,
        "order": lesson.order,
        "module_id": lesson.module_id,
        "questions_count": questions_count,
        "estimated_duration_minutes": max(1, questions_count + 1),
    }


def serialize_module_item(module: Module, include_lessons: bool = True) -> dict:
    lessons = list(module.lessons.all()) if include_lessons else []
    payload = {
        "id": module.id,
        "name": module.name,
        "order": module.order,
        "course_id": module.course_id,
        "lessons_count": getattr(module, "lessons_count", len(lessons)),
    }
    if include_lessons:
        payload["lessons"] = [serialize_lesson_item(lesson) for lesson in lessons]
    return payload
