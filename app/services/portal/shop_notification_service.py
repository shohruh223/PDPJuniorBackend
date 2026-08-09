import html
import json
from urllib import error, request

from django.conf import settings
from django.utils import timezone

from app.models.coin import CoinOrder


def build_shop_order_message(order):
    created_at = timezone.localtime(order.created_at).strftime("%d.%m.%Y %H:%M")
    return "\n".join(
        [
            "<b>Yangi coin buyurtma</b>",
            "",
            f"<b>O‘quvchi:</b> {html.escape(order.student_name or '-')}",
            f"<b>Telefon:</b> {html.escape(order.student_phone or '-')}",
            f"<b>Filial:</b> {html.escape(order.branch_name or '-')}",
            f"<b>Kurs:</b> {html.escape(order.course_name or '-')}",
            f"<b>Guruh:</b> {html.escape(order.group_name or '-')}",
            f"<b>Mahsulot:</b> {html.escape(order.product_title)}",
            f"<b>Narxi:</b> {order.price} coin",
            (
                f"<b>Balans:</b> {order.balance_before} → "
                f"{order.balance_after} coin"
            ),
            f"<b>Vaqt:</b> {created_at}",
            f"<b>Buyurtma ID:</b> <code>{order.pk}</code>",
        ]
    )


def send_shop_order_notification(order_id):
    order = CoinOrder.objects.get(pk=order_id)
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_SHOP_CHAT_ID

    if not token:
        CoinOrder.objects.filter(pk=order_id).update(
            telegram_error="TELEGRAM_BOT_TOKEN sozlanmagan."
        )
        return False

    payload = json.dumps(
        {
            "chat_id": chat_id,
            "text": build_shop_order_message(order),
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
    ).encode("utf-8")
    telegram_request = request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(telegram_request, timeout=5) as response:
            response_data = json.loads(response.read().decode("utf-8"))
        if not response_data.get("ok"):
            raise RuntimeError(response_data.get("description", "Telegram xatosi"))
    except (error.URLError, TimeoutError, RuntimeError, ValueError) as exc:
        CoinOrder.objects.filter(pk=order_id).update(
            telegram_error=str(exc)[:1000],
        )
        return False

    CoinOrder.objects.filter(pk=order_id).update(
        telegram_sent_at=timezone.now(),
        telegram_error="",
    )
    return True
