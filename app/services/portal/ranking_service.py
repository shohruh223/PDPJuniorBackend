from __future__ import annotations

from django.conf import settings
from django.db.models import Count, Prefetch, Q

from app.models.auth import StudentProfile
from app.models.mentors import Mentor
from app.models.question import Course, Lesson, Module
from app.services.profile_image_service import build_profile_image_url
from app.utils.text import estimated_test_minutes


UZ_MONTHS_SHORT = [
    "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
    "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr",
]


def build_absolute_photo_url(user, request=None):
    return build_profile_image_url(user, request=request)


def load_mentor_index() -> dict:
    """Barcha faol mentorlarni BITTA so'rovda lug'atga yig'adi.

    Ilgari `resolve_mentor_name` har bir o'quvchi uchun 1-2 ta alohida
    so'rov bajarardi. `/api/student/ranking/me` esa 500 ta profilni
    yuklagani uchun bitta sahifa ochilishi ~1000 SQL so'roviga aylanardi.
    Endi mentorlar bir marta o'qiladi va xotirada qidiriladi.

    Struktura: {branch_id: {"by_role": {role_lower: name}, "any": name}}
    """
    index: dict = {}
    rows = (
        Mentor.objects.filter(is_active=True, branch__is_active=True)
        .order_by("branch_id", "id")
        .values_list("branch_id", "role", "name")
    )
    for branch_id, role, name in rows:
        bucket = index.setdefault(branch_id, {"by_role": {}, "any": None})
        role_key = (role or "").strip().lower()
        bucket["by_role"].setdefault(role_key, name)
        if bucket["any"] is None:
            bucket["any"] = name
    return index


def mentor_name_from_index(index: dict, branch_id, course_name: str | None) -> str:
    if not branch_id:
        return ""
    bucket = index.get(branch_id)
    if not bucket:
        return ""
    if course_name:
        found = bucket["by_role"].get(course_name.strip().lower())
        if found:
            return found
    return bucket["any"] or ""


def resolve_mentor_name(branch_id, course_name: str | None) -> str:
    """Bitta mentor nomi (kamdan-kam holatlar uchun).

    Ro'yxatlarda BUNI ISHLATMANG — `load_mentor_index()` bilan bir marta
    yuklab, `mentor_name_from_index()` orqali qidiring.
    """
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
    """O'quvchining ketma-ket kunlar seriyasi.

    DIQQAT: ilgari `streak_days` bo'sh bo'lsa davomat foizidan 1-30
    kunlik seriya "taxmin qilinardi" va bu foydalanuvchiga haqiqiy
    ko'rsatkich sifatida ko'rsatilardi. Ota-ona yoki mentor bu raqamga
    ishonsa, noto'g'ri xulosaga kelardi.

    Endi ma'lumot yo'q bo'lsa 0 qaytadi. Eski xatti-harakatni
    `RANKING_ESTIMATE_MISSING=1` bilan qaytarish mumkin.
    """
    if profile.streak_days:
        return profile.streak_days
    if not getattr(settings, "RANKING_ESTIMATE_MISSING", False):
        return 0
    percent = profile.attendance_average_percent or 0
    if percent <= 0:
        return 0
    return max(1, min(30, int(round(percent / 7))))


def serialize_ranking_student(
    profile: StudentProfile,
    request=None,
    period: str = "total",
    mentor_index: dict | None = None,
) -> dict:
    user = profile.user
    # Ilgari bu yerda kursi noma'lum o'quvchiga "Python", filiali
    # noma'lumga "PDP Junior" yozib qo'yilardi — ya'ni bo'sh ma'lumot
    # haqiqiy ma'lumotdan farq qilmasdi.
    course_name = profile.course.name if profile.course else ""
    branch_name = profile.branch.name if profile.branch else ""
    avatar = build_absolute_photo_url(user, request)

    total_points = profile.total_score or 0
    # Ilgari oylik ball bo'sh bo'lsa umumiy balning 18 %i "o'ylab
    # topilardi" — hech qachon test topshirmagan o'quvchi ham oylik ball
    # bilan ko'rinardi.
    monthly_points = profile.local_test_score or 0
    if not monthly_points and getattr(settings, "RANKING_ESTIMATE_MISSING", False):
        monthly_points = max(0, int(total_points * 0.18))

    if mentor_index is None:
        mentor_index = load_mentor_index()
    mentor = mentor_name_from_index(mentor_index, profile.branch_id, course_name)

    return {
        "id": str(profile.id),
        "name": user.full_name,
        "course": course_name,
        "branch": branch_name,
        "mentor": mentor,
        "avatar": avatar or "",
        "totalPoints": total_points,
        "monthlyPoints": monthly_points,
        "streak": estimate_streak(profile),
        "level": profile.group_name or "",
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

    # Mentorlar bir marta yuklanadi — profil boshiga so'rov yo'q.
    mentor_index = load_mentor_index()
    return [
        serialize_ranking_student(profile, request, period, mentor_index=mentor_index)
        for profile in qs
    ]


def get_student_rank(profile: StudentProfile, *, period: str = "total") -> int | None:
    """O'quvchining o'rnini BITTA COUNT so'rovi bilan hisoblaydi.

    Ilgari buning uchun 500 ta profil yuklanib, Python'da indeks
    qidirilardi. Endi "mendan yuqori nechta o'quvchi bor" degan savolga
    baza javob beradi.
    """
    score_field = "local_test_score" if period == "month" else "total_score"
    my_score = getattr(profile, score_field, 0) or 0

    base = StudentProfile.objects.filter(user__is_active=True, user__role="student")
    higher = base.filter(**{f"{score_field}__gt": my_score}).count()

    # Bir xil ballda tartib `user__first_name` bo'yicha — shu bilan
    # o'rin barqaror bo'ladi.
    same_score_before = (
        base.filter(**{score_field: my_score})
        .filter(user__first_name__lt=profile.user.first_name or "")
        .count()
    )
    return higher + same_score_before + 1


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
        "estimated_duration_minutes": estimated_test_minutes(questions_count),
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
