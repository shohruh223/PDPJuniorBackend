from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from app.models.auth import StudentProfile
from app.utils.text import split_full_name


def extract_student_dashboard_data(payload: dict) -> dict:
    """
    Real payload:
    {
        "success": true,
        "data": {
            "lessonEndTime": "10:30:03",
            "allDebtor": 0,
            "student": {
                "id": "...",
                "fullName": "Shohruh Test ",
                "photoId": null
            },
            "lesson": {
                "id": "...",
                "status": "TUGAGAN",
                "attendance": "Qatnashgan",
                "coin": 1,
                "lessonDate": [2026, 3, 26]
            },
            "activeCoin": 73,
            "lessonStartTime": "09:00:00",
            "moduleBarchart": [...],
            "attendanceAveragePercent": 100,
            "group": "P-9",
            "studentDebtors": []
        }
    }
    """
    if not isinstance(payload, dict):
        payload = {}

    # PDPStudentAPIClient ba'zan to'liq response qaytaradi:
    #   {"success": true, "data": {...}}
    # eski client yoki testlarda esa bevosita data qaytishi mumkin:
    #   {"student": {...}, "group": "P-9", ...}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    student = data.get("student", {}) or {}
    lesson = data.get("lesson", {}) or {}

    group_value = data.get("group", "") or data.get("groupName", "") or data.get("group_name", "") or ""
    if isinstance(group_value, dict):
        group_value = group_value.get("name") or group_value.get("title") or ""

    return {
        "group_name": str(group_value).strip(),
        "student_full_name": (student.get("fullName") or "").strip(),
        "api_coin": int(data.get("activeCoin", 0) or 0),
        "api_score": 0,  # bu endpointda score yo'q
        "all_debtor": Decimal(str(data.get("allDebtor", 0) or 0)),
        "attendance_average_percent": float(data.get("attendanceAveragePercent", 0) or 0),
        "lesson_coin": int(lesson.get("coin", 0) or 0),
        "lesson_attendance": lesson.get("attendance", "") or "",
        "lesson_status": lesson.get("status", "") or "",
        "lesson_id": lesson.get("id"),
        "lesson_date": lesson.get("lessonDate", []),
        "lesson_start_time": data.get("lessonStartTime"),
        "lesson_end_time": data.get("lessonEndTime"),
        "module_barchart": data.get("moduleBarchart", []) or [],
        "student_debtors": data.get("studentDebtors", []) or [],
    }


@transaction.atomic
def sync_student_dashboard_data(student_profile: StudentProfile, external_payload: dict) -> tuple[StudentProfile, dict]:
    parsed = extract_student_dashboard_data(external_payload)

    parsed_full_name = parsed.get("student_full_name", "").strip()
    if parsed_full_name:
        first_name, last_name = split_full_name(parsed_full_name)

        changed_user_fields = []

        if first_name and student_profile.user.first_name != first_name:
            student_profile.user.first_name = first_name
            changed_user_fields.append("first_name")

        # Bo'sh familiya saqlangan qiymatni o'chirmasin: PDP ba'zan
        # bitta so'zli fullName qaytaradi va split natijasi ("Ism", "").
        if last_name and last_name != student_profile.user.last_name:
            student_profile.user.last_name = last_name
            changed_user_fields.append("last_name")

        if changed_user_fields:
            changed_user_fields.append("updated_at")
            student_profile.user.save(update_fields=changed_user_fields)

    changed_profile_fields = []

    new_group_name = parsed.get("group_name", "") or ""
    if student_profile.group_name != new_group_name:
        student_profile.group_name = new_group_name
        changed_profile_fields.append("group_name")

    new_api_coin = parsed.get("api_coin", 0)
    if student_profile.api_coin != new_api_coin:
        student_profile.api_coin = new_api_coin
        changed_profile_fields.append("api_coin")

    new_api_score = parsed.get("api_score", 0)
    if student_profile.api_score != new_api_score:
        student_profile.api_score = new_api_score
        changed_profile_fields.append("api_score")

    new_all_debtor = parsed.get("all_debtor", Decimal("0.00"))
    if student_profile.all_debtor != new_all_debtor:
        student_profile.all_debtor = new_all_debtor
        changed_profile_fields.append("all_debtor")

    new_attendance_average_percent = parsed.get("attendance_average_percent", 0.0)
    if student_profile.attendance_average_percent != new_attendance_average_percent:
        student_profile.attendance_average_percent = new_attendance_average_percent
        changed_profile_fields.append("attendance_average_percent")

    old_course_id = student_profile.course_id
    student_profile.assign_course_from_group(save=False)
    if student_profile.course_id != old_course_id:
        changed_profile_fields.append("course")

    # Bazada ustuni yo'q tashqi ma'lumotlar (joriy dars, moduleBarchart,
    # studentDebtors) snapshotga yoziladi — shunda dashboard endpointi
    # tashqi API'ni kutmasdan, bazadan javob bera oladi.
    snapshot = {
        "lesson_coin": parsed.get("lesson_coin", 0),
        "lesson_attendance": parsed.get("lesson_attendance", ""),
        "lesson_status": parsed.get("lesson_status", ""),
        "lesson_id": parsed.get("lesson_id"),
        "lesson_date": parsed.get("lesson_date", []),
        "lesson_start_time": parsed.get("lesson_start_time"),
        "lesson_end_time": parsed.get("lesson_end_time"),
        "module_barchart": parsed.get("module_barchart", []),
        "student_debtors": parsed.get("student_debtors", []),
    }
    if student_profile.external_snapshot != snapshot:
        student_profile.external_snapshot = snapshot
        changed_profile_fields.append("external_snapshot")

    student_profile.last_synced_at = timezone.now()
    changed_profile_fields.append("last_synced_at")

    old_total_score = student_profile.total_score
    old_total_coin = student_profile.total_coin

    student_profile.recalculate_all_totals(save=False)

    if student_profile.total_score != old_total_score:
        changed_profile_fields.append("total_score")

    if student_profile.total_coin != old_total_coin:
        changed_profile_fields.append("total_coin")

    if changed_profile_fields:
        changed_profile_fields.append("updated_at")
        student_profile.save(update_fields=list(dict.fromkeys(changed_profile_fields)))

    return student_profile, parsed