"""Frontend (PDP Junior portal) uchun response adapterlari."""


def pick_sms_code_id(data: dict) -> str | None:
    if not isinstance(data, dict):
        return None
    return (
        data.get("sms_code_id")
        or data.get("smsCodeId")
        or data.get("smsCodeID")
    )


def auth_sms_response(data: dict, message: str = "SMS kodi yuborildi") -> dict:
    sms_code_id = pick_sms_code_id(data)
    payload = {"message": message}
    if sms_code_id:
        payload["sms_code_id"] = str(sms_code_id)
    return payload


def auth_login_verify_response(data: dict) -> dict:
    student = data.get("student") or {}
    return {
        "access_token": data.get("access") or data.get("access_token"),
        "refresh_token": data.get("refresh") or data.get("refresh_token"),
        "token_type": "Bearer",
        "user": {
            "id": student.get("id"),
            "name": student.get("full_name") or student.get("name"),
            "phone_number": student.get("phone_number"),
            "full_name": student.get("full_name"),
            "first_name": student.get("first_name"),
            "last_name": student.get("last_name"),
            "group_name": student.get("group_name"),
            "class_name": student.get("group_name"),
            "grade": student.get("group_name"),
            "branch": student.get("branch_name") or student.get("branch"),
            "avatar": student.get("avatar"),
            "avatar_url": student.get("image") or student.get("avatar_url"),
            "email": student.get("email"),
        },
        "pdp_token": data.get("pdp_token"),
    }


def auth_forgot_verify_response(data: dict) -> dict:
    token = data.get("pre_reset_token") or data.get("preResetToken")
    payload = {}
    if token:
        payload["pre_reset_token"] = str(token)
    return payload
