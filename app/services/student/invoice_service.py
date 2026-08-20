from django.db import transaction

from app.models.auth import StudentProfile
from app.models.payment import StudentInvoice
from app.services.student.external_student_api import (
    PDPStudentAPIClient,
    PDPStudentAPIError,
)


def extract_invoice_items(payload: dict) -> list[dict]:
    """
    PDP student-invoices endpointidan kelgan responsedan
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


def parse_invoice_item(item: dict) -> dict | None:
    """
    External APIdan kelgan bitta invoice objectni
    model fieldlariga moslab beradi.
    """

    if not isinstance(item, dict):
        return None

    external_id = item.get("invoiceId") or item.get("id")

    if not external_id:
        return None

    return {
        "external_id": str(external_id),
        "invoice_number": str(item.get("invoiceNumber") or ""),
        "invoice_status": str(item.get("invoiceStatus") or ""),
        "invoice_amount": StudentInvoice.to_decimal(item.get("invoiceAmount")),
        "paid_invoice_amount": StudentInvoice.to_decimal(
            item.get("paidInvoiceAmount")
        ),
        "debt_amount": StudentInvoice.to_decimal(item.get("debtAmount")),
        "time_table_name": str(item.get("timeTableName") or ""),
        "time_table_position": str(item.get("timeTablePosition") or ""),
        "group_name": str(item.get("groupName") or ""),
        "raw_data": item,
    }


@transaction.atomic
def sync_student_invoices(
    student_profile: StudentProfile,
    external_payload: dict,
) -> list[StudentInvoice]:
    """
    PDPdan kelgan student invoicelarni bazaga saqlaydi.

    Agar invoice oldin saqlangan bo'lsa, update qiladi.
    Agar yangi bo'lsa, create qiladi.
    """

    items = extract_invoice_items(external_payload)

    synced_invoices = []

    for item in items:
        parsed = parse_invoice_item(item)

        if not parsed:
            continue

        external_id = parsed["external_id"]

        invoice, _ = StudentInvoice.objects.update_or_create(
            student_profile=student_profile,
            external_id=external_id,
            defaults=parsed,
        )

        synced_invoices.append(invoice)

    return synced_invoices


def fetch_and_sync_student_invoices(
    student_profile: StudentProfile,
) -> tuple[list[StudentInvoice], str | None]:
    """
    Student uchun PDP student-invoices endpointdan data olib,
    bazaga sync qiladi.
    """

    if not student_profile.external_id:
        return [], "Student external_id topilmadi."

    if not student_profile.pdp_access_token:
        return [], "PDP access token topilmadi."

    try:
        client = PDPStudentAPIClient(token=student_profile.pdp_access_token)

        payload = client.get_student_invoices(
            str(student_profile.external_id)
        )

        invoices = sync_student_invoices(
            student_profile=student_profile,
            external_payload=payload,
        )

        return invoices, None

    except PDPStudentAPIError as exc:
        return [], str(exc)
