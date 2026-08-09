from django import template

from app.models.coin import CoinOrder


register = template.Library()


@register.simple_tag
def shop_order_notifications(user, limit=8):
    if not user or not user.is_authenticated or not user.is_staff:
        return {"orders": [], "unread_count": 0}

    orders = list(
        CoinOrder.objects.select_related("student_profile", "product")
        .order_by("-created_at")[:limit]
    )
    return {
        "orders": orders,
        "unread_count": CoinOrder.objects.filter(is_admin_read=False).count(),
    }
