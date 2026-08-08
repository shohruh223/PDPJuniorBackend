from __future__ import annotations

from django.db import transaction

from app.models.auth import StudentProfile
from app.models.coin import CoinOrder, CoinProduct


def serialize_shop_product(product: CoinProduct, request=None) -> dict:
    image_url = None
    if product.image:
        image_url = request.build_absolute_uri(product.image.url) if request else product.image.url

    return {
        "id": str(product.id),
        "title": product.name,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "category": product.category,
        "cat": product.category,
        "stock": product.stock,
        "emoji": product.emoji,
        "bg_gradient": product.bg_gradient,
        "image": image_url,
        "in_stock": product.stock > 0,
    }


def get_shop_catalog(*, category: str | None, request=None) -> dict:
    products = CoinProduct.objects.filter(is_active=True).order_by("price")
    if category and category != "all":
        products = products.filter(category=category)

    items = [serialize_shop_product(product, request) for product in products]
    categories = [
        {"id": "all", "label": "Barchasi"},
        {"id": "academy", "label": "Maktab", "emoji": "📚"},
        {"id": "gadget", "label": "Gadjetlar", "emoji": "📱"},
        {"id": "book", "label": "Kitoblar", "emoji": "📗"},
        {"id": "special", "label": "Maxsus", "emoji": "🎁"},
    ]
    return {"categories": categories, "products": items}


def get_student_balance(profile: StudentProfile) -> int:
    return profile.total_coin or 0


def serialize_order(order: CoinOrder) -> dict:
    return {
        "id": str(order.id),
        "title": order.product_title,
        "price": order.price,
        "status": order.status,
        "date": order.created_at.isoformat(),
    }


@transaction.atomic
def purchase_product(*, profile: StudentProfile, product_id) -> tuple[CoinOrder | None, str | None]:
    try:
        product = CoinProduct.objects.select_for_update().get(id=product_id, is_active=True)
    except CoinProduct.DoesNotExist:
        return None, "Mahsulot topilmadi."

    if product.stock <= 0:
        return None, "Mahsulot tugagan."

    balance = get_student_balance(profile)
    if balance < product.price:
        return None, "Coin yetarli emas."

    remaining = product.price
    if (profile.test_coin or 0) >= remaining:
        profile.test_coin -= remaining
    else:
        remaining -= profile.test_coin or 0
        profile.test_coin = 0
        profile.api_coin = max(0, (profile.api_coin or 0) - remaining)

    profile.recalculate_total_coin(save=True)

    product.stock -= 1
    product.save(update_fields=["stock", "updated_at"])

    order = CoinOrder.objects.create(
        student_profile=profile,
        product=product,
        product_title=product.name,
        price=product.price,
        status=CoinOrder.StatusChoices.COMPLETED,
    )
    return order, None
