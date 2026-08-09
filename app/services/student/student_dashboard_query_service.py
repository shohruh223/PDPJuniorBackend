from app.models.auth import StudentProfile
from app.services.profile_image_service import build_profile_image_url
from app.services.student.external_student_api import PDPStudentAPIClient, PDPStudentAPIError
from app.services.student.student_dashboard_service import sync_student_dashboard_data


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
    student_profile = (
        StudentProfile.objects
        .select_related("user", "course")
        .get(user=user)
    )

    sync_warning = None
    external_extra = {
        "lesson_coin": 0,
        "lesson_attendance": "",
        "lesson_status": "",
        "lesson_id": None,
        "lesson_date": [],
        "lesson_start_time": None,
        "lesson_end_time": None,
        "module_barchart": [],
        "student_debtors": [],
    }

    if student_profile.external_id and student_profile.pdp_access_token:
        try:
            client = PDPStudentAPIClient(token=student_profile.pdp_access_token)
            external_payload = client.get_student_info(str(student_profile.external_id))

            student_profile, parsed = sync_student_dashboard_data(
                student_profile,
                external_payload,
            )

            external_extra = {
                "lesson_coin": parsed["lesson_coin"],
                "lesson_attendance": parsed["lesson_attendance"],
                "lesson_status": parsed["lesson_status"],
                "lesson_id": parsed["lesson_id"],
                "lesson_date": parsed["lesson_date"],
                "lesson_start_time": parsed["lesson_start_time"],
                "lesson_end_time": parsed["lesson_end_time"],
                "module_barchart": parsed["module_barchart"],
                "student_debtors": parsed["student_debtors"],
            }
        except PDPStudentAPIError as exc:
            sync_warning = str(exc)

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