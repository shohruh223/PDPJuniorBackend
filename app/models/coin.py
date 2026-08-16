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
    image_url = models.CharField(max_length=500, blank=True, default="")
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
        verbose_name = "Coin mahsuloti"
        verbose_name_plural = "Coin mahsulotlari"

    def __str__(self):
        return f"{self.name} - {self.price} coin"

    def get_display_image_url(self, request=None):
        if self.image:
            url = self.image.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return self.image_url or None


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
        default=StatusChoices.PENDING,
        db_index=True,
    )
    student_name = models.CharField(max_length=120, blank=True, default="")
    student_phone = models.CharField(max_length=20, blank=True, default="")
    course_name = models.CharField(max_length=120, blank=True, default="")
    branch_name = models.CharField(max_length=120, blank=True, default="")
    group_name = models.CharField(max_length=120, blank=True, default="")
    balance_before = models.PositiveIntegerField(default=0)
    balance_after = models.PositiveIntegerField(default=0)
    telegram_sent_at = models.DateTimeField(blank=True, null=True)
    telegram_error = models.TextField(blank=True, default="")
    is_admin_read = models.BooleanField(default=False, db_index=True)
    admin_read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "coin_orders"
        ordering = ["-created_at"]
        verbose_name = "Coin buyurtma"
        verbose_name_plural = "Coin buyurtmalar"

    def __str__(self):
        return f"{self.product_title} — {self.price} coin"