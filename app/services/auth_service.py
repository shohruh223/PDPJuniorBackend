from django.db import transaction
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from app.models.auth import User, StudentProfile
from .auth_external_api import PDPAuthAPIClient
from .student.external_student_api import PDPStudentAPIClient, PDPStudentAPIError
from .student.student_dashboard_service import sync_student_dashboard_data

# DIQQAT: `PreResetTokenError` va token funksiyalari ilgari shu faylda
# HAM, `password_reset_token.py` da HAM alohida aniqlangan edi. View
# ikkinchisini import qilgani uchun `except PreResetTokenError` bu yerdagi
# istisnoni ushlay olmasdi va muddati tugagan token 400 o'rniga 500
# berardi. Endi yagona manba — `password_reset_token`.
from .password_reset_token import (  # noqa: E402
    PRE_RESET_TOKEN_MAX_AGE,
    PRE_RESET_TOKEN_SALT,
    PreResetTokenError,
    make_pre_reset_token,
    parse_pre_reset_token,
)


def split_full_name(full_name: str) -> tuple[str, str]:
    full_name = (full_name or "").strip()
    if not full_name:
        return "", ""

    parts = full_name.split()
    first_name = parts[0]
    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
    return first_name, last_name


def check_phone_via_external_api(phone_number: str) -> dict:
    client = PDPAuthAPIClient()
    payload = client.check_phone(phone_number)
    return payload.get("data", {}) or {}


def enter_password_via_external_api(phone_number: str, password: str) -> dict:
    client = PDPAuthAPIClient()
    payload = client.enter_password(phone_number, password)
    return payload.get("data", {}) or {}


def forgot_password_via_external_api(phone_number: str) -> dict:
    client = PDPAuthAPIClient()
    payload = client.forgot_password(phone_number)
    return payload.get("data", {}) or {}


def verify_sms_code_via_external_api(sms_code_id: str, sms_code: str, phone_number: str) -> dict:
    """
    Password reset yoki alohida verify flow uchun external verify endpoint.
    Login flow local auth/check-sms-code/ ichida PDP check-sms-code endpointini ishlatadi.
    """
    client = PDPAuthAPIClient()
    payload = client.verify_sms_code(
        sms_code_id=sms_code_id,
        sms_code=sms_code,
        phone_number=phone_number,
    )
    return payload.get("data", {}) or {}


def verify_sms_code_for_password_reset(*, sms_code_id: str, sms_code: str, phone_number: str) -> dict:
    """
    Password reset flow uchun local verify bosqichi.
    External verify endpoint chaqirilmaydi, aks holda sms code consume bo‘lib qoladi.
    """
    pre_reset_token = make_pre_reset_token(
        phone_number=phone_number,
        sms_code_id=sms_code_id,
        sms_code=sms_code,
    )
    return {
        "pre_reset_token": pre_reset_token,
    }


def set_new_password_via_external_api(
    phone_number: str,
    sms_code_id: str,
    sms_code: str,
    password: str,
    repeat_password: str,
) -> dict:
    client = PDPAuthAPIClient()
    payload = client.set_new_password(
        phone_number=phone_number,
        sms_code_id=sms_code_id,
        sms_code=sms_code,
        password=password,
        repeat_password=repeat_password,
    )
    return payload.get("data", {}) or {}


def set_new_password_with_pre_token(
    *,
    pre_reset_token: str,
    password: str,
    repeat_password: str,
) -> dict:
    token_data = parse_pre_reset_token(pre_reset_token)

    return set_new_password_via_external_api(
        phone_number=token_data["phone_number"],
        sms_code_id=token_data["sms_code_id"],
        sms_code=token_data["sms_code"],
        password=password,
        repeat_password=repeat_password,
    )



def _as_dict(value):
    return value if isinstance(value, dict) else {}


def _as_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def _first_present(*values):
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _normalize_phone(phone_number: str) -> str:
    phone_number = (phone_number or "").strip()
    if phone_number.startswith("998") and not phone_number.startswith("+"):
        return f"+{phone_number}"
    return phone_number


def _normalize_pdp_token(token: str | None) -> str | None:
    token = (token or "").strip()
    if not token:
        return None
    if token.lower().startswith("bearer "):
        return token
    return f"Bearer {token}"


def _extract_token(data: dict) -> str | None:
    user_data = _as_dict(data.get("user"))
    auth_data = _as_dict(data.get("auth"))
    return _normalize_pdp_token(_first_present(
        data.get("token"),
        data.get("accessToken"),
        data.get("access_token"),
        data.get("jwt"),
        data.get("bearerToken"),
        data.get("authToken"),
        auth_data.get("token"),
        auth_data.get("accessToken"),
        auth_data.get("access_token"),
        user_data.get("token"),
        user_data.get("accessToken"),
        user_data.get("access_token"),
    ))


def _extract_student_candidates(data: dict) -> list[dict]:
    user_data = _as_dict(data.get("user"))
    candidates = []

    for key in ("students", "studentList", "student_list"):
        candidates.extend(_as_list(data.get(key)))
        candidates.extend(_as_list(user_data.get(key)))

    for value in (
        data.get("student"),
        data.get("selectedStudent"),
        data.get("currentStudent"),
        user_data.get("student"),
        user_data.get("selectedStudent"),
        user_data.get("currentStudent"),
    ):
        candidates.extend(_as_list(value))

    # Ba'zi PDP javoblarida student ma'lumoti to'g'ridan-to'g'ri data ichida keladi.
    if _first_present(
        data.get("studentId"), data.get("student_id"), data.get("externalStudentId"),
        data.get("id"), data.get("fullName"), data.get("firstName"), data.get("groupName"), data.get("group"),
    ):
        candidates.append(data)

    cleaned = []
    for item in candidates:
        if isinstance(item, dict) and item not in cleaned:
            cleaned.append(item)
    return cleaned


def _get_group_name(source: dict, root_data: dict) -> str:
    group_obj = _as_dict(_first_present(source.get("group"), root_data.get("group")))
    raw_group = _first_present(
        source.get("groupName"),
        source.get("group_name"),
        source.get("groupTitle"),
        group_obj.get("name"),
        group_obj.get("title"),
        root_data.get("groupName"),
        root_data.get("group_name"),
        root_data.get("groupTitle"),
    )
    if isinstance(raw_group, dict):
        raw_group = _first_present(raw_group.get("name"), raw_group.get("title"))
    return (raw_group or "").strip()


def _extract_student_identity(data: dict, fallback_phone: str) -> dict:
    candidates = _extract_student_candidates(data)
    student_data = candidates[0] if candidates else {}
    user_data = _as_dict(data.get("user"))

    external_student_id = _first_present(
        student_data.get("id"),
        student_data.get("studentId"),
        student_data.get("student_id"),
        student_data.get("externalId"),
        student_data.get("external_id"),
        student_data.get("externalStudentId"),
        data.get("studentId"),
        data.get("student_id"),
        data.get("externalStudentId"),
    )

    full_name = (_first_present(
        student_data.get("fullName"),
        student_data.get("full_name"),
        user_data.get("fullName"),
        user_data.get("full_name"),
        data.get("fullName"),
        data.get("full_name"),
    ) or "").strip()

    first_name = (_first_present(
        student_data.get("firstName"),
        student_data.get("first_name"),
        user_data.get("firstName"),
        user_data.get("first_name"),
        data.get("firstName"),
        data.get("first_name"),
    ) or "").strip()

    last_name = (_first_present(
        student_data.get("lastName"),
        student_data.get("last_name"),
        user_data.get("lastName"),
        user_data.get("last_name"),
        data.get("lastName"),
        data.get("last_name"),
    ) or "").strip()

    if not first_name and full_name:
        first_name, last_name = split_full_name(full_name)

    external_phone = _normalize_phone(_first_present(
        student_data.get("phoneNumber"),
        student_data.get("phone_number"),
        student_data.get("phone"),
        user_data.get("phoneNumber"),
        user_data.get("phone_number"),
        user_data.get("phone"),
        data.get("phoneNumber"),
        data.get("phone_number"),
        data.get("phone"),
        fallback_phone,
    ))

    patron = (_first_present(
        student_data.get("patron"),
        student_data.get("middleName"),
        student_data.get("middle_name"),
        user_data.get("patron"),
        data.get("patron"),
    ) or "").strip()

    return {
        "student_data": student_data,
        "external_student_id": external_student_id,
        "first_name": first_name,
        "last_name": last_name,
        "full_name": full_name,
        "patron": patron,
        "external_phone": external_phone,
        "group_name": _get_group_name(student_data, data),
    }


def check_sms_code_and_sync_user(*, sms_code_id: str, sms_code: str, phone_number: str) -> dict:
    """SMS kodni tasdiqlaydi va lokal foydalanuvchini sinxronlaydi.

    MUHIM: bu funksiya ilgari butunlay `@transaction.atomic` ichida edi va
    o'sha tranzaksiya ichida ikkita tashqi HTTP so'rov bajarardi. PDP
    sekin javob berganda baza tranzaksiyasi va ulanishi tarmoq kutish
    vaqti davomida ochiq qolardi — bir vaqtda ko'p login bo'lsa
    Postgres ulanishlari tugab, butun API to'xtardi.

    Endi tarmoq chaqiruvlari tranzaksiyadan tashqarida, baza yozuvlari esa
    `_persist_authenticated_student` ichidagi qisqa tranzaksiyada.
    """
    client = PDPAuthAPIClient()

    payload = client.check_sms_code(
        sms_code_id=sms_code_id,
        sms_code=sms_code,
        phone_number=phone_number,
    )

    if not payload.get("success"):
        raise ValueError("SMS kod noto‘g‘ri yoki muddati tugagan.")

    data = payload.get("data", {}) or {}
    if not isinstance(data, dict):
        raise ValueError("PDP auth API data noto‘g‘ri formatda qaytdi.")

    pdp_token = _extract_token(data)
    identity = _extract_student_identity(data, phone_number)

    external_student_id = identity["external_student_id"]
    first_name = identity["first_name"]
    last_name = identity["last_name"]
    patron = identity["patron"]
    external_phone = identity["external_phone"]
    group_name = identity["group_name"]

    # Baza yozuvlari qisqa tranzaksiyada — tarmoq chaqiruvlari undan
    # tashqarida qoladi, ya'ni PDP sekinlashsa ham ulanish band bo'lmaydi.
    with transaction.atomic():
        user, created = User.objects.get_or_create(
            phone_number=external_phone,
            defaults={
                "role": User.RoleChoices.STUDENT,
                "first_name": first_name,
                "last_name": last_name,
                "is_active": True,
            },
        )

        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])

        changed_fields = []

        if user.role != User.RoleChoices.STUDENT:
            user.role = User.RoleChoices.STUDENT
            changed_fields.append("role")

        if first_name and user.first_name != first_name:
            user.first_name = first_name
            changed_fields.append("first_name")

        if last_name and user.last_name != last_name:
            user.last_name = last_name
            changed_fields.append("last_name")

        if not user.is_active:
            user.is_active = True
            changed_fields.append("is_active")

        if changed_fields:
            changed_fields.append("updated_at")
            user.save(update_fields=list(dict.fromkeys(changed_fields)))

        student_profile, _ = StudentProfile.objects.get_or_create(
            user=user,
            defaults={
                "external_id": external_student_id,
                "pdp_access_token": pdp_token,
                "group_name": group_name,
            },
        )

        profile_changed_fields = []

        if external_student_id and str(student_profile.external_id or "") != str(external_student_id):
            student_profile.external_id = external_student_id
            profile_changed_fields.append("external_id")

        if pdp_token and student_profile.pdp_access_token != pdp_token:
            student_profile.pdp_access_token = pdp_token
            profile_changed_fields.append("pdp_access_token")

        if group_name and student_profile.group_name != group_name:
            student_profile.group_name = group_name
            profile_changed_fields.append("group_name")

        old_course_id = student_profile.course_id
        student_profile.assign_course_from_group(save=False)

        if student_profile.course_id != old_course_id:
            profile_changed_fields.append("course")

        if profile_changed_fields:
            profile_changed_fields.append("updated_at")
            student_profile.save(update_fields=list(dict.fromkeys(profile_changed_fields)))

    dashboard_sync_warning = None

    if student_profile.external_id and student_profile.pdp_access_token:
        # Login paytida dashboard ma'lumoti ham kerak, lekin uni kutib
        # turish login javobini sekinlashtiradi. Celery yoqilgan bo'lsa
        # sinxronizatsiya fon rejimiga uzatiladi; aks holda bu yerda
        # bajariladi, lekin tranzaksiyadan TASHQARIDA.
        from app.services.student import sync_coordinator

        try:
            synced, warning = sync_coordinator.ensure_fresh(
                student_profile, sync_coordinator.DASHBOARD, force=False
            )
            dashboard_sync_warning = warning
            if synced:
                student_profile.refresh_from_db()
                user = student_profile.user
        except Exception as exc:  # sinxronizatsiya login'ni to'xtatmasin
            dashboard_sync_warning = str(exc)

    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    # XAVFSIZLIK: `pdp_token` — bu backend adminapi.pdp.uz ga murojaat
    # qilishda ishlatadigan haqiqiy credential. Uni brauzerga berish
    # kerak emas: mijozga faqat quyidagi JWT kerak. Frontend hozircha
    # bu maydonni o'qiyotgan bo'lishi mumkin, shuning uchun o'chirish
    # env orqali boshqariladi — frontend tekshirilgach EXPOSE_PDP_TOKEN=0
    # qo'ying.
    expose_pdp_token = getattr(settings, "EXPOSE_PDP_TOKEN", True)

    return {
        "pdp_token": pdp_token if expose_pdp_token else None,
        "access": str(access),
        "refresh": str(refresh),
        "dashboard_sync_warning": dashboard_sync_warning,
        "student": {
            "id": str(student_profile.id),
            "external_id": str(student_profile.external_id) if student_profile.external_id else None,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "phone_number": user.phone_number,
            "patron": patron,
            "role": user.role,
            "group_name": student_profile.group_name,
            "course_id": str(student_profile.course_id) if student_profile.course_id else None,
            "course_name": student_profile.course.name if student_profile.course else None,
            "api_coin": student_profile.api_coin,
            "test_coin": student_profile.test_coin,
            "total_coin": student_profile.total_coin,
            "api_score": student_profile.api_score,
            "local_test_score": student_profile.local_test_score,
            "total_score": student_profile.total_score,
            "all_debtor": str(student_profile.all_debtor),
            "attendance_average_percent": student_profile.attendance_average_percent,
            "last_synced_at": student_profile.last_synced_at,
        },
    }