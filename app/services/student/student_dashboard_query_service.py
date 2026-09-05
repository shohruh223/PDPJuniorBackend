from app.models.auth import StudentProfile
from app.services.profile_image_service import build_profile_image_url
from app.services.student import sync_coordinator


def build_absolute_photo_url(user, request=None):
    return build_profile_image_url(user, request=request)


def build_avatar(user):
    """
    User ismidan avatar initials yasaydi.
    Masalan: Azizbek Karimov -> AK
    Agar ism/familiya bo'lmasa phone_number oxirgi 2 raqamini qaytaradi.
    """
    first = user.first_name[:1].upper() if user.first_name else ""
    last = user.last_name[:1].upper() if user.last_name else ""

    avatar = f"{first}{last}"

    if avatar:
        return avatar

    if user.phone_number:
        return user.phone_number[-2:]

    return None


def get_student_dashboard_data(user, request=None):
    """Dashboard ma'lumotlari — har doim bazadan.

    Ilgari bu funksiya har chaqirilganda `adminapi.pdp.uz` ga bloklovchi
    HTTP so'rov yuborardi. Endi tashqi ma'lumot fon rejimida (Celery)
    yangilanadi va bu yerda faqat saqlangan snapshot o'qiladi, ya'ni
    javob vaqti tashqi servisga bog'liq emas.

    `?refresh=1` bilan mijoz majburiy yangilashni so'ray oladi (bu
    endpointda SyncThrottle bilan cheklangan).
    """
    student_profile = (
        StudentProfile.objects
        .select_related("user", "course")
        .get(user=user)
    )

    force = sync_coordinator.wants_refresh(request) if request is not None else False
    _, sync_warning = sync_coordinator.ensure_fresh(
        student_profile, sync_coordinator.DASHBOARD, force=force
    )
    if force:
        student_profile.refresh_from_db()

    snapshot = student_profile.external_snapshot or {}
    external_extra = {
        "lesson_coin": snapshot.get("lesson_coin", 0),
        "lesson_attendance": snapshot.get("lesson_attendance", ""),
        "lesson_status": snapshot.get("lesson_status", ""),
        "lesson_id": snapshot.get("lesson_id"),
        "lesson_date": snapshot.get("lesson_date", []),
        "lesson_start_time": snapshot.get("lesson_start_time"),
        "lesson_end_time": snapshot.get("lesson_end_time"),
        "module_barchart": snapshot.get("module_barchart", []),
        "student_debtors": snapshot.get("student_debtors", []),
    }

    return {
        "student": {
            "id": str(student_profile.id),
            "external_id": str(student_profile.external_id) if student_profile.external_id else None,
            "full_name": student_profile.user.full_name,
            "first_name": student_profile.user.first_name,
            "last_name": student_profile.user.last_name,
            "phone_number": student_profile.user.phone_number,
            "group_name": student_profile.group_name,
            "image": build_absolute_photo_url(student_profile.user, request),
            "avatar": build_avatar(student_profile.user),
        },
        "course": {
            "id": student_profile.course.id if student_profile.course else None,
            "name": student_profile.course.name if student_profile.course else None,
        },
        "scores": {
            "api_score": student_profile.api_score,
            "local_test_score": student_profile.local_test_score,
            "total_score": student_profile.total_score,
        },
        "coins": {
            "api_coin": student_profile.api_coin,
            "test_coin": student_profile.test_coin,
            "spent_coin": student_profile.spent_coin,
            "total_coin": student_profile.total_coin,
            "lesson_coin": external_extra["lesson_coin"],
        },
        "finance": {
            "all_debtor": str(student_profile.all_debtor),
            "attendance_average_percent": student_profile.attendance_average_percent,
            "student_debtors": external_extra["student_debtors"],
        },
        "lesson": {
            "id": external_extra["lesson_id"],
            "attendance": external_extra["lesson_attendance"],
            "status": external_extra["lesson_status"],
            "lesson_date": external_extra["lesson_date"],
            "start_time": external_extra["lesson_start_time"],
            "end_time": external_extra["lesson_end_time"],
        },
        "module_barchart": external_extra["module_barchart"],
        "last_synced_at": student_profile.last_synced_at,
        "sync_warning": sync_warning,
    }