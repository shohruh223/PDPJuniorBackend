from django.db import transaction

from app.models.auth import StudentProfile
from app.models.payment import StudentPaymentHistory
from app.services.student.external_student_api import (
    PDPStudentAPIClient,
    PDPStudentAPIError,
)


def extract_payment_history_items(payload: dict) -> list[dict]:
    """
    PDP payment-history endpointidan kelgan responsedan
    data listini ajratib oladi.

    Real response:
    {
        "success": true,
        "data": [
            {...},
            {...}
        ]
    }
    """

    if not isinstance(payload, dict):
        return []

    data = payload.get("data", [])

    if not isinstance(data, list):
        return []

    return [item for item in data if isinstance(item, dict)]


def parse_payment_history_item(item: dict) -> dict | None:
    """
    External APIdan kelgan bitta payment objectni
    model fieldlariga moslab beradi.
    """

    if not isinstance(item, dict):
        return None

    external_id = item.get("id")

    if not external_id:
        return None

    return {
        "external_id": str(external_id),
        "amount": StudentPaymentHistory.to_decimal(item.get("amount")),
        "aim": str(item.get("aim") or ""),
        "invoice_number": str(item.get("invoiceNumber") or ""),
        "time_table_name": str(item.get("timeTableName") or ""),
        "group_name": str(item.get("groupName") or ""),
        "payment_type": str(item.get("paymentType") or ""),
        "date": StudentPaymentHistory.timestamp_ms_to_datetime(item.get("date")),
        "created_date": StudentPaymentHistory.timestamp_ms_to_datetime(
            item.get("createdDate")
        ),
        "cashier": str(item.get("cashier") or ""),
        "canceled": bool(item.get("canceled", False)),
        "raw_data": item,
    }


@transaction.atomic
def sync_student_payment_histories(
    student_profile: StudentProfile,
    external_payload: dict,
) -> list[StudentPaymentHistory]:
    """
    PDPdan kelgan payment historylarni bazaga saqlaydi.

    Agar payment oldin saqlangan bo'lsa, update qiladi.
    Agar yangi bo'lsa, create qiladi.
    """

    items = extract_payment_history_items(external_payload)

    synced_histories = []

    for item in items:
        parsed = parse_payment_history_item(item)

        if not parsed:
            continue

        external_id = parsed["external_id"]

        history, _ = StudentPaymentHistory.objects.update_or_create(
            student_profile=student_profile,
            external_id=external_id,
            defaults=parsed,
        )

        synced_histories.append(history)

    return synced_histories


def fetch_and_sync_student_payment_histories(
    student_profile: StudentProfile,
) -> tuple[list[StudentPaymentHistory], str | None]:
    """
    Student uchun PDP payment history endpointdan data olib,
    bazaga sync qiladi.
    """

    if not student_profile.external_id:
        return [], "Student external_id topilmadi."

    if not student_profile.pdp_access_token:
        return [], "PDP access token topilmadi."

    try:
        client = PDPStudentAPIClient(token=student_profile.pdp_access_token)

        payload = client.get_student_payment_history(
            str(student_profile.external_id)
        )

        histories = sync_student_payment_histories(
            student_profile=student_profile,
            external_payload=payload,
        )

        return histories, None

    except PDPStudentAPIError as exc:
        return [], str(exc)