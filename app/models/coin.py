from django.db import models
from app.models.auth import BaseModel


class CoinProduct(BaseModel):
    class CategoryChoices(models.TextChoices):
        ACADEMY = "academy", "Maktab"
        GADGET = "gadget", "Gadjetlar"
        BOOK = "book", "Kitoblar"
        SPECIAL = "special", "Maxsus"

    name = models.CharField(max_length=120)
    description = models.TextField()
    price = models.PositiveIntegerField()
    image = models.ImageField(upload_to="coin-products/", blank=True, null=True)
    category = models.CharField(
        max_length=20,
        choices=CategoryChoices.choices,
        default=CategoryChoices.ACADEMY,
        db_index=True,
    )
    stock = models.PositiveIntegerField(default=0)
    emoji = models.CharField(max_length=16, default="🎁")
    bg_gradient = models.CharField(
        max_length=200,
        blank=True,
        default="linear-gradient(135deg,#ff2fd5,#7c3aed)",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "coin_products"
        ordering = ["price"]
        verbose_name = "Coin product"
        verbose_name_plural = "Coin products"

    def __str__(self):
        return f"{self.name} - {self.price} coin"


class CoinOrder(BaseModel):
    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        COMPLETED = "completed", "Bajarildi"
        CANCELLED = "cancelled", "Bekor qilindi"

    student_profile = models.ForeignKey(
        "app.StudentProfile",
        on_delete=models.CASCADE,
        related_name="coin_orders",
    )
    product = models.ForeignKey(
        CoinProduct,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    product_title = models.CharField(max_length=120)
    price = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.COMPLETED,
        db_index=True,
    )

    class Meta:
        db_table = "coin_orders"
        ordering = ["-created_at"]
        verbose_name = "Coin buyurtma"
        verbose_name_plural = "Coin buyurtmalar"

    def __str__(self):
        return f"{self.product_title} — {self.price} coin"