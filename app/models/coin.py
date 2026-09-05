from django.db import models
from app.models.auth import BaseModel


class CoinProduct(BaseModel):
    class CategoryChoices(models.TextChoices):
        ACADEMY = "academy", "Maktab"
        GADGET = "gadget", "Gadjetlar"
        BOOK = "book", "Kitoblar"
        SPECIAL = "special", "Maxsus"

    name = models.CharField(max_length=120, verbose_name="Mahsulot nomi")
    description = models.TextField(verbose_name="Tavsifi")
    price = models.PositiveIntegerField(verbose_name="Narxi (coin)")
    image = models.ImageField(upload_to="coin-products/", blank=True, null=True, verbose_name="Rasmi")
    image_url = models.CharField(max_length=500, blank=True, default="", verbose_name="Rasm havolasi")
    category = models.CharField(
        max_length=20,
        choices=CategoryChoices.choices,
        default=CategoryChoices.ACADEMY,
        db_index=True,
        verbose_name="Toifasi",
    )
    stock = models.PositiveIntegerField(default=0, verbose_name="Ombordagi soni")
    emoji = models.CharField(max_length=16, default="🎁", verbose_name="Emoji")
    bg_gradient = models.CharField(
        max_length=200,
        blank=True,
        default="linear-gradient(135deg,#ff2fd5,#7c3aed)",
        verbose_name="Fon gradienti",
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")

    class Meta:
        db_table = "coin_products"
        ordering = ["price"]
        verbose_name = "Coin mahsuloti"
        verbose_name_plural = "Coin mahsulotlari"

    def __str__(self):
        return f"{self.name} - {self.price} coin"

    def get_display_image_url(self, request=None):
        from app.serializers.media import build_file_url

        if self.image:
            url = self.image.url
            if request and not str(url).startswith(("http://", "https://")):
                return request.build_absolute_uri(url)
            return url
        return build_file_url(self.image_url, request)


class CoinOrder(BaseModel):
    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        COMPLETED = "completed", "Bajarildi"
        CANCELLED = "cancelled", "Bekor qilindi"

    student_profile = models.ForeignKey(
        "app.StudentProfile",
        on_delete=models.CASCADE,
        related_name="coin_orders",
        verbose_name="O‘quvchi",
    )
    product = models.ForeignKey(
        CoinProduct,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="Mahsulot",
    )
    product_title = models.CharField(max_length=120, verbose_name="Mahsulot nomi")
    price = models.PositiveIntegerField(verbose_name="Narxi (coin)")
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        db_index=True,
        verbose_name="Holati",
    )
    student_name = models.CharField(max_length=120, blank=True, default="", verbose_name="O‘quvchi ismi")
    student_phone = models.CharField(max_length=20, blank=True, default="", verbose_name="O‘quvchi telefoni")
    course_name = models.CharField(max_length=120, blank=True, default="", verbose_name="Kurs")
    branch_name = models.CharField(max_length=120, blank=True, default="", verbose_name="Filial")
    group_name = models.CharField(max_length=120, blank=True, default="", verbose_name="Guruh")
    balance_before = models.PositiveIntegerField(default=0, verbose_name="Xariddan oldingi balans")
    balance_after = models.PositiveIntegerField(default=0, verbose_name="Xariddan keyingi balans")
    telegram_sent_at = models.DateTimeField(blank=True, null=True, verbose_name="Telegramga yuborildi")
    telegram_error = models.TextField(blank=True, default="", verbose_name="Telegram xatosi")
    is_admin_read = models.BooleanField(default=False, db_index=True, verbose_name="Admin ko‘rgan")
    admin_read_at = models.DateTimeField(blank=True, null=True, verbose_name="Ko‘rilgan vaqti")

    class Meta:
        db_table = "coin_orders"
        ordering = ["-created_at"]
        verbose_name = "Coin buyurtma"
        verbose_name_plural = "Coin buyurtmalar"

    def __str__(self):
        return f"{self.product_title} — {self.price} coin"