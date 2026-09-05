"""Admin paneldagi maydon nomlarini o'zbekchaga o'tkazish.

FAQAT KO'RINISH. Bu migratsiyada bitta ham SQL buyrug'i yo'q —
tekshirish uchun: `python manage.py sqlmigrate app 0015` (natija bo'sh).
`verbose_name`, `choices` yorliqlari va `Meta.verbose_name` — Django
uchun metama'lumot; jadval tuzilishi va ma'lumotlar o'zgarmaydi.

Nima uchun kerak edi: admin panel butunlay o'zbek tilida bo'lsa-da,
174 dan ortiq maydon inglizcha texnik nomi bilan chiqardi — "Group
name", "Total score", "All debtor", "Attendance average percent",
"Is active" va hokazo. Filial holati "Opened"/"Closed", foydalanuvchi
roli "Student"/"Guest" deb ko'rinardi.
"""


import app.models.branch
import app.models.mentors
import app.models.month_hero
import app.models.portfolio
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0014_student_profile_spent_coin_and_snapshot"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="studentinvoice",
            options={
                "ordering": ["-updated_at", "-created_at"],
                "verbose_name": "O‘quvchi invoysi",
                "verbose_name_plural": "O‘quvchi invoyslari",
            },
        ),
        migrations.AlterModelOptions(
            name="studentprofile",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "O‘quvchi profili",
                "verbose_name_plural": "O‘quvchi profillari",
            },
        ),
        migrations.AlterModelOptions(
            name="studentquestionreward",
            options={
                "verbose_name": "Savol mukofoti",
                "verbose_name_plural": "Savol mukofotlari",
            },
        ),
        migrations.AlterField(
            model_name="branch",
            name="address",
            field=models.CharField(max_length=255, verbose_name="Manzil"),
        ),
        migrations.AlterField(
            model_name="branch",
            name="album",
            field=models.JSONField(
                blank=True,
                default=list,
                validators=[app.models.branch.validate_album],
                verbose_name="Rasmlar albomi",
            ),
        ),
        migrations.AlterField(
            model_name="branch",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, verbose_name="Yaratilgan sana"
            ),
        ),
        migrations.AlterField(
            model_name="branch",
            name="district",
            field=models.CharField(
                blank=True, default="", max_length=120, verbose_name="Tuman"
            ),
        ),
        migrations.AlterField(
            model_name="branch",
            name="hours",
            field=models.CharField(
                blank=True,
                default="09:00–18:00",
                max_length=50,
                verbose_name="Ish vaqti",
            ),
        ),
        migrations.AlterField(
            model_name="branch",
            name="image_url",
            field=models.CharField(
                blank=True, default="", max_length=500, verbose_name="Rasm havolasi"
            ),
        ),
        migrations.AlterField(
            model_name="branch",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Faol"),
        ),
        migrations.AlterField(
            model_name="branch",
            name="is_opened",
            field=models.CharField(
                choices=[("opened", "Ochiq"), ("closed", "Yopiq")],
                db_index=True,
                default="opened",
                max_length=20,
                verbose_name="Holati",
            ),
        ),
        migrations.AlterField(
            model_name="branch",
            name="latitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=7,
                max_digits=10,
                null=True,
                verbose_name="Kenglik",
            ),
        ),
        migrations.AlterField(
            model_name="branch",
            name="longitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=7,
                max_digits=10,
                null=True,
                verbose_name="Uzunlik",
            ),
        ),
        migrations.AlterField(
            model_name="branch",
            name="map_url",
            field=models.URLField(max_length=500, verbose_name="Xarita havolasi"),
        ),
        migrations.AlterField(
            model_name="branch",
            name="name",
            field=models.CharField(max_length=120, verbose_name="Filial nomi"),
        ),
        migrations.AlterField(
            model_name="branch",
            name="phone",
            field=models.CharField(max_length=20, verbose_name="Telefon"),
        ),
        migrations.AlterField(
            model_name="branch",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana"),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="admin_read_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Ko‘rilgan vaqti"
            ),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="balance_after",
            field=models.PositiveIntegerField(
                default=0, verbose_name="Xariddan keyingi balans"
            ),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="balance_before",
            field=models.PositiveIntegerField(
                default=0, verbose_name="Xariddan oldingi balans"
            ),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="branch_name",
            field=models.CharField(
                blank=True, default="", max_length=120, verbose_name="Filial"
            ),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="course_name",
            field=models.CharField(
                blank=True, default="", max_length=120, verbose_name="Kurs"
            ),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="created_at",
            field=models.DateTimeField(
                default=django.utils.timezone.now, verbose_name="Yaratilgan sana"
            ),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="group_name",
            field=models.CharField(
                blank=True, default="", max_length=120, verbose_name="Guruh"
            ),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="is_admin_read",
            field=models.BooleanField(
                db_index=True, default=False, verbose_name="Admin ko‘rgan"
            ),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="price",
            field=models.PositiveIntegerField(verbose_name="Narxi (coin)"),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="product",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="orders",
                to="app.coinproduct",
                verbose_name="Mahsulot",
            ),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="product_title",
            field=models.CharField(max_length=120, verbose_name="Mahsulot nomi"),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Kutilmoqda"),
                    ("completed", "Bajarildi"),
                    ("cancelled", "Bekor qilindi"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
                verbose_name="Holati",
            ),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="student_name",
            field=models.CharField(
                blank=True, default="", max_length=120, verbose_name="O‘quvchi ismi"
            ),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="student_phone",
            field=models.CharField(
                blank=True, default="", max_length=20, verbose_name="O‘quvchi telefoni"
            ),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="student_profile",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="coin_orders",
                to="app.studentprofile",
                verbose_name="O‘quvchi",
            ),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="telegram_error",
            field=models.TextField(
                blank=True, default="", verbose_name="Telegram xatosi"
            ),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="telegram_sent_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Telegramga yuborildi"
            ),
        ),
        migrations.AlterField(
            model_name="coinorder",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana"),
        ),
        migrations.AlterField(
            model_name="coinproduct",
            name="bg_gradient",
            field=models.CharField(
                blank=True,
                default="linear-gradient(135deg,#ff2fd5,#7c3aed)",
                max_length=200,
                verbose_name="Fon gradienti",
            ),
        ),
        migrations.AlterField(
            model_name="coinproduct",
            name="category",
            field=models.CharField(
                choices=[
                    ("academy", "Maktab"),
                    ("gadget", "Gadjetlar"),
                    ("book", "Kitoblar"),
                    ("special", "Maxsus"),
                ],
                db_index=True,
                default="academy",
                max_length=20,
                verbose_name="Toifasi",
            ),
        ),
        migrations.AlterField(
            model_name="coinproduct",
            name="created_at",
            field=models.DateTimeField(
                default=django.utils.timezone.now, verbose_name="Yaratilgan sana"
            ),
        ),
        migrations.AlterField(
            model_name="coinproduct",
            name="description",
            field=models.TextField(verbose_name="Tavsifi"),
        ),
        migrations.AlterField(
            model_name="coinproduct",
            name="emoji",
            field=models.CharField(default="🎁", max_length=16, verbose_name="Emoji"),
        ),
        migrations.AlterField(
            model_name="coinproduct",
            name="image",
            field=models.ImageField(
                blank=True, null=True, upload_to="coin-products/", verbose_name="Rasmi"
            ),
        ),
        migrations.AlterField(
            model_name="coinproduct",
            name="image_url",
            field=models.CharField(
                blank=True, default="", max_length=500, verbose_name="Rasm havolasi"
            ),
        ),
        migrations.AlterField(
            model_name="coinproduct",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Faol"),
        ),
        migrations.AlterField(
            model_name="coinproduct",
            name="name",
            field=models.CharField(max_length=120, verbose_name="Mahsulot nomi"),
        ),
        migrations.AlterField(
            model_name="coinproduct",
            name="price",
            field=models.PositiveIntegerField(verbose_name="Narxi (coin)"),
        ),
        migrations.AlterField(
            model_name="coinproduct",
            name="stock",
            field=models.PositiveIntegerField(default=0, verbose_name="Ombordagi soni"),
        ),
        migrations.AlterField(
            model_name="coinproduct",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana"),
        ),
        migrations.AlterField(
            model_name="course",
            name="description",
            field=models.TextField(blank=True, default="", verbose_name="Tavsifi"),
        ),
        migrations.AlterField(
            model_name="course",
            name="image_url",
            field=models.CharField(
                blank=True, default="", max_length=500, verbose_name="Rasm havolasi"
            ),
        ),
        migrations.AlterField(
            model_name="course",
            name="is_active",
            field=models.BooleanField(db_index=True, default=True, verbose_name="Faol"),
        ),
        migrations.AlterField(
            model_name="course",
            name="name",
            field=models.CharField(max_length=100, unique=True, verbose_name="Nomi"),
        ),
        migrations.AlterField(
            model_name="course",
            name="sort_order",
            field=models.PositiveIntegerField(
                db_index=True, default=0, verbose_name="Tartib raqami"
            ),
        ),
        migrations.AlterField(
            model_name="gallerypost",
            name="category",
            field=models.JSONField(
                help_text='{"uz":"Tadbir","ru":"Событие","en":"Event"}',
                verbose_name="Toifasi",
            ),
        ),
        migrations.AlterField(
            model_name="gallerypost",
            name="cover_bg",
            field=models.CharField(
                blank=True, default="", max_length=200, verbose_name="Muqova foni"
            ),
        ),
        migrations.AlterField(
            model_name="gallerypost",
            name="cover_contain",
            field=models.BooleanField(
                default=False, verbose_name="Muqovani to‘liq ko‘rsatish"
            ),
        ),
        migrations.AlterField(
            model_name="gallerypost",
            name="cover_image",
            field=models.CharField(
                blank=True, default="", max_length=500, verbose_name="Muqova rasmi"
            ),
        ),
        migrations.AlterField(
            model_name="gallerypost",
            name="created_at",
            field=models.DateTimeField(
                default=django.utils.timezone.now, verbose_name="Yaratilgan sana"
            ),
        ),
        migrations.AlterField(
            model_name="gallerypost",
            name="date",
            field=models.CharField(
                help_text="Masalan: 12.07.2026", max_length=20, verbose_name="Sanasi"
            ),
        ),
        migrations.AlterField(
            model_name="gallerypost",
            name="description",
            field=models.JSONField(verbose_name="Tavsifi"),
        ),
        migrations.AlterField(
            model_name="gallerypost",
            name="icon",
            field=models.CharField(default="📰", max_length=16, verbose_name="Belgisi"),
        ),
        migrations.AlterField(
            model_name="gallerypost",
            name="is_active",
            field=models.BooleanField(db_index=True, default=True, verbose_name="Faol"),
        ),
        migrations.AlterField(
            model_name="gallerypost",
            name="media",
            field=models.JSONField(
                blank=True, default=list, verbose_name="Media fayllar"
            ),
        ),
        migrations.AlterField(
            model_name="gallerypost",
            name="sort_order",
            field=models.PositiveIntegerField(default=0, verbose_name="Tartib raqami"),
        ),
        migrations.AlterField(
            model_name="gallerypost",
            name="title",
            field=models.JSONField(verbose_name="Sarlavhasi"),
        ),
        migrations.AlterField(
            model_name="gallerypost",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana"),
        ),
        migrations.AlterField(
            model_name="gallerypost",
            name="views_count",
            field=models.PositiveIntegerField(
                default=0, verbose_name="Ko‘rishlar soni"
            ),
        ),
        migrations.AlterField(
            model_name="gallerypost",
            name="views_display",
            field=models.CharField(
                blank=True, default="", max_length=20, verbose_name="Ko‘rishlar (matn)"
            ),
        ),
        migrations.AlterField(
            model_name="lesson",
            name="course",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="lessons",
                to="app.course",
                verbose_name="Kurs",
            ),
        ),
        migrations.AlterField(
            model_name="lesson",
            name="module",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="lessons",
                to="app.module",
                verbose_name="Modul",
            ),
        ),
        migrations.AlterField(
            model_name="lesson",
            name="name",
            field=models.CharField(max_length=255, verbose_name="Dars nomi"),
        ),
        migrations.AlterField(
            model_name="lesson",
            name="order",
            field=models.PositiveIntegerField(verbose_name="Tartib raqami"),
        ),
        migrations.AlterField(
            model_name="mentor",
            name="avatar",
            field=models.JSONField(
                blank=True,
                default=dict,
                validators=[app.models.mentors.validate_avatar],
                verbose_name="Rasmi",
            ),
        ),
        migrations.AlterField(
            model_name="mentor",
            name="bio",
            field=models.TextField(
                blank=True, default="", verbose_name="Qisqa ma’lumot"
            ),
        ),
        migrations.AlterField(
            model_name="mentor",
            name="branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="mentors",
                to="app.branch",
                verbose_name="Filial",
            ),
        ),
        migrations.AlterField(
            model_name="mentor",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, verbose_name="Yaratilgan sana"
            ),
        ),
        migrations.AlterField(
            model_name="mentor",
            name="exp",
            field=models.CharField(max_length=50, verbose_name="Tajribasi"),
        ),
        migrations.AlterField(
            model_name="mentor",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Faol"),
        ),
        migrations.AlterField(
            model_name="mentor",
            name="name",
            field=models.CharField(max_length=120, verbose_name="Ismi"),
        ),
        migrations.AlterField(
            model_name="mentor",
            name="role",
            field=models.CharField(max_length=80, verbose_name="Yo‘nalishi"),
        ),
        migrations.AlterField(
            model_name="mentor",
            name="students_count",
            field=models.CharField(max_length=50, verbose_name="O‘quvchilar soni"),
        ),
        migrations.AlterField(
            model_name="mentor",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana"),
        ),
        migrations.AlterField(
            model_name="mentor",
            name="working_period_start",
            field=models.DateField(verbose_name="Ishga kirgan sana"),
        ),
        migrations.AlterField(
            model_name="module",
            name="course",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="modules",
                to="app.course",
                verbose_name="Kurs",
            ),
        ),
        migrations.AlterField(
            model_name="module",
            name="name",
            field=models.CharField(max_length=255, verbose_name="Modul nomi"),
        ),
        migrations.AlterField(
            model_name="module",
            name="order",
            field=models.PositiveIntegerField(verbose_name="Tartibi"),
        ),
        migrations.AlterField(
            model_name="monthhero",
            name="created_at",
            field=models.DateTimeField(
                default=django.utils.timezone.now, verbose_name="Yaratilgan sana"
            ),
        ),
        migrations.AlterField(
            model_name="monthhero",
            name="is_active",
            field=models.BooleanField(db_index=True, default=True, verbose_name="Faol"),
        ),
        migrations.AlterField(
            model_name="monthhero",
            name="period",
            field=models.DateField(
                db_index=True,
                default=app.models.month_hero.current_period,
                help_text="Oy/yil filter uchun. Masalan: 2026-04-01",
                verbose_name="Oy",
            ),
        ),
        migrations.AlterField(
            model_name="monthhero",
            name="points",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Shu oyda to'plangan ball. 0 bo'lsa student umumiy bali ishlatiladi.",
                verbose_name="Ballari",
            ),
        ),
        migrations.AlterField(
            model_name="monthhero",
            name="student_profile",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="month_heroes",
                to="app.studentprofile",
                verbose_name="O‘quvchi",
            ),
        ),
        migrations.AlterField(
            model_name="monthhero",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana"),
        ),
        migrations.AlterField(
            model_name="portfolio",
            name="category",
            field=models.CharField(
                blank=True, default="", max_length=80, verbose_name="Toifasi"
            ),
        ),
        migrations.AlterField(
            model_name="portfolio",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, verbose_name="Yaratilgan sana"
            ),
        ),
        migrations.AlterField(
            model_name="portfolio",
            name="desc",
            field=models.CharField(max_length=255, verbose_name="Tavsifi"),
        ),
        migrations.AlterField(
            model_name="portfolio",
            name="image",
            field=models.JSONField(
                blank=True,
                default=dict,
                validators=[app.models.portfolio.validate_portfolio_image],
                verbose_name="Rasmi",
            ),
        ),
        migrations.AlterField(
            model_name="portfolio",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Faol"),
        ),
        migrations.AlterField(
            model_name="portfolio",
            name="name",
            field=models.CharField(max_length=120, verbose_name="Loyiha nomi"),
        ),
        migrations.AlterField(
            model_name="portfolio",
            name="student",
            field=models.CharField(
                blank=True, default="", max_length=120, verbose_name="Muallifi"
            ),
        ),
        migrations.AlterField(
            model_name="portfolio",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana"),
        ),
        migrations.AlterField(
            model_name="portfolio",
            name="url",
            field=models.URLField(max_length=500, verbose_name="Havolasi"),
        ),
        migrations.AlterField(
            model_name="portfolio",
            name="year",
            field=models.CharField(
                blank=True, default="", max_length=4, verbose_name="Yili"
            ),
        ),
        migrations.AlterField(
            model_name="question",
            name="correct_option",
            field=models.CharField(
                choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
                max_length=1,
                verbose_name="To‘g‘ri javob",
            ),
        ),
        migrations.AlterField(
            model_name="question",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, verbose_name="Yaratilgan sana"
            ),
        ),
        migrations.AlterField(
            model_name="question",
            name="images",
            field=models.JSONField(blank=True, default=dict, verbose_name="Rasmlar"),
        ),
        migrations.AlterField(
            model_name="question",
            name="lesson",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="questions",
                to="app.lesson",
                verbose_name="Dars",
            ),
        ),
        migrations.AlterField(
            model_name="question",
            name="options",
            field=models.JSONField(verbose_name="Variantlar"),
        ),
        migrations.AlterField(
            model_name="question",
            name="text",
            field=models.JSONField(verbose_name="Savol matni"),
        ),
        migrations.AlterField(
            model_name="studentinvoice",
            name="created_at",
            field=models.DateTimeField(
                default=django.utils.timezone.now, verbose_name="Yaratilgan sana"
            ),
        ),
        migrations.AlterField(
            model_name="studentinvoice",
            name="debt_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=14,
                verbose_name="Qarz summasi",
            ),
        ),
        migrations.AlterField(
            model_name="studentinvoice",
            name="external_id",
            field=models.CharField(
                db_index=True,
                help_text="PDP invoiceId",
                max_length=128,
                verbose_name="Tashqi ID",
            ),
        ),
        migrations.AlterField(
            model_name="studentinvoice",
            name="group_name",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="Guruh nomi"
            ),
        ),
        migrations.AlterField(
            model_name="studentinvoice",
            name="invoice_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=14,
                verbose_name="Invoys summasi",
            ),
        ),
        migrations.AlterField(
            model_name="studentinvoice",
            name="invoice_number",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                max_length=128,
                verbose_name="Invoys raqami",
            ),
        ),
        migrations.AlterField(
            model_name="studentinvoice",
            name="invoice_status",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                max_length=64,
                verbose_name="Invoys holati",
            ),
        ),
        migrations.AlterField(
            model_name="studentinvoice",
            name="paid_invoice_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=14,
                verbose_name="To‘langan summa",
            ),
        ),
        migrations.AlterField(
            model_name="studentinvoice",
            name="raw_data",
            field=models.JSONField(
                blank=True, default=dict, verbose_name="Xom ma’lumot"
            ),
        ),
        migrations.AlterField(
            model_name="studentinvoice",
            name="student_profile",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="invoices",
                to="app.studentprofile",
                verbose_name="O‘quvchi profili",
            ),
        ),
        migrations.AlterField(
            model_name="studentinvoice",
            name="time_table_name",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="Dars jadvali"
            ),
        ),
        migrations.AlterField(
            model_name="studentinvoice",
            name="time_table_position",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                max_length=64,
                verbose_name="Jadval o‘rni",
            ),
        ),
        migrations.AlterField(
            model_name="studentinvoice",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana"),
        ),
        migrations.AlterField(
            model_name="studentmark",
            name="attendance",
            field=models.CharField(
                choices=[
                    ("present", "Qatnashgan"),
                    ("absent", "Qatnashmagan"),
                    ("late", "Kechikkan"),
                ],
                default="present",
                max_length=10,
                verbose_name="Davomat",
            ),
        ),
        migrations.AlterField(
            model_name="studentmark",
            name="course",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="student_marks",
                to="app.course",
                verbose_name="Kurs",
            ),
        ),
        migrations.AlterField(
            model_name="studentmark",
            name="grade",
            field=models.PositiveSmallIntegerField(
                blank=True,
                choices=[(1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")],
                null=True,
                verbose_name="Baho",
            ),
        ),
        migrations.AlterField(
            model_name="studentmark",
            name="lesson",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="student_marks",
                to="app.lesson",
                verbose_name="Dars",
            ),
        ),
        migrations.AlterField(
            model_name="studentmark",
            name="record_date",
            field=models.DateField(db_index=True, verbose_name="Sanasi"),
        ),
        migrations.AlterField(
            model_name="studentmark",
            name="student_profile",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="marks",
                to="app.studentprofile",
                verbose_name="O‘quvchi",
            ),
        ),
        migrations.AlterField(
            model_name="studentmark",
            name="verified",
            field=models.BooleanField(default=False, verbose_name="Tasdiqlangan"),
        ),
        migrations.AlterField(
            model_name="studentpaymenthistory",
            name="aim",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="Maqsadi"
            ),
        ),
        migrations.AlterField(
            model_name="studentpaymenthistory",
            name="amount",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=14,
                verbose_name="Summasi",
            ),
        ),
        migrations.AlterField(
            model_name="studentpaymenthistory",
            name="canceled",
            field=models.BooleanField(default=False, verbose_name="Bekor qilingan"),
        ),
        migrations.AlterField(
            model_name="studentpaymenthistory",
            name="cashier",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="Kassir"
            ),
        ),
        migrations.AlterField(
            model_name="studentpaymenthistory",
            name="created_at",
            field=models.DateTimeField(
                default=django.utils.timezone.now, verbose_name="Yaratilgan sana"
            ),
        ),
        migrations.AlterField(
            model_name="studentpaymenthistory",
            name="created_date",
            field=models.DateTimeField(
                blank=True, db_index=True, null=True, verbose_name="Yaratilgan sana"
            ),
        ),
        migrations.AlterField(
            model_name="studentpaymenthistory",
            name="date",
            field=models.DateTimeField(
                blank=True, db_index=True, null=True, verbose_name="To‘lov sanasi"
            ),
        ),
        migrations.AlterField(
            model_name="studentpaymenthistory",
            name="external_id",
            field=models.CharField(
                db_index=True, max_length=128, verbose_name="Tashqi ID"
            ),
        ),
        migrations.AlterField(
            model_name="studentpaymenthistory",
            name="group_name",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="Guruh"
            ),
        ),
        migrations.AlterField(
            model_name="studentpaymenthistory",
            name="invoice_number",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                max_length=128,
                verbose_name="Invoys raqami",
            ),
        ),
        migrations.AlterField(
            model_name="studentpaymenthistory",
            name="payment_type",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="To‘lov turi"
            ),
        ),
        migrations.AlterField(
            model_name="studentpaymenthistory",
            name="raw_data",
            field=models.JSONField(
                blank=True, default=dict, verbose_name="Xom ma’lumot"
            ),
        ),
        migrations.AlterField(
            model_name="studentpaymenthistory",
            name="student_profile",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payment_histories",
                to="app.studentprofile",
                verbose_name="O‘quvchi",
            ),
        ),
        migrations.AlterField(
            model_name="studentpaymenthistory",
            name="time_table_name",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="Dars jadvali"
            ),
        ),
        migrations.AlterField(
            model_name="studentpaymenthistory",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana"),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="address",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="Manzil"
            ),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="all_debtor",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=12,
                verbose_name="Umumiy qarz",
            ),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="api_coin",
            field=models.IntegerField(default=0, verbose_name="PDP coini"),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="api_score",
            field=models.IntegerField(default=0, verbose_name="PDP bali"),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="attendance_average_percent",
            field=models.FloatField(default=0, verbose_name="O‘rtacha davomat (%)"),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="avatar_url",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Frontend yoki tashqi storage'dagi avatar URL/path.",
                max_length=500,
                verbose_name="Avatar havolasi",
            ),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="bio",
            field=models.TextField(
                blank=True, default="", verbose_name="Qisqa ma’lumot"
            ),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="student_profiles",
                to="app.branch",
                verbose_name="Filial",
            ),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="course",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="student_profiles",
                to="app.course",
                verbose_name="Kurs",
            ),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="created_at",
            field=models.DateTimeField(
                default=django.utils.timezone.now, verbose_name="Yaratilgan sana"
            ),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="external_id",
            field=models.UUIDField(
                blank=True,
                db_index=True,
                null=True,
                unique=True,
                verbose_name="Tashqi ID (PDP)",
            ),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="external_snapshot",
            field=models.JSONField(
                blank=True, default=dict, verbose_name="PDP ma’lumot nusxasi"
            ),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="group_name",
            field=models.CharField(
                blank=True, db_index=True, max_length=120, verbose_name="Guruh nomi"
            ),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="last_synced_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Oxirgi sinxronizatsiya"
            ),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="lesson_last_coin",
            field=models.IntegerField(default=0, verbose_name="Oxirgi dars coini"),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="local_test_score",
            field=models.IntegerField(default=0, verbose_name="Test bali"),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="parent_phone",
            field=models.CharField(
                blank=True,
                default="",
                max_length=13,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Telefon raqami +998XXXXXXXXX formatida bo‘lishi kerak.",
                        regex="^\\+998\\d{9}$",
                    )
                ],
                verbose_name="Ota-ona telefoni",
            ),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="pdp_access_token",
            field=models.TextField(blank=True, null=True, verbose_name="PDP tokeni"),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="spent_coin",
            field=models.PositiveIntegerField(
                default=0, verbose_name="Sarflangan coin"
            ),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="streak_days",
            field=models.PositiveIntegerField(
                default=0, verbose_name="Ketma-ket kunlar"
            ),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="test_coin",
            field=models.IntegerField(default=0, verbose_name="Test coini"),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="total_coin",
            field=models.IntegerField(
                db_index=True, default=0, verbose_name="Jami coin"
            ),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="total_score",
            field=models.IntegerField(
                db_index=True, default=0, verbose_name="Jami ball"
            ),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana"),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="user",
            field=models.OneToOneField(
                limit_choices_to={"role": "student"},
                on_delete=django.db.models.deletion.CASCADE,
                related_name="student_profile",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Foydalanuvchi",
            ),
        ),
        migrations.AlterField(
            model_name="studentquestionreward",
            name="awarded_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Berilgan vaqt"),
        ),
        migrations.AlterField(
            model_name="studentquestionreward",
            name="question",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="student_rewards",
                to="app.question",
                verbose_name="Savol",
            ),
        ),
        migrations.AlterField(
            model_name="studentquestionreward",
            name="session",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="awarded_rewards",
                to="app.testsession",
                verbose_name="Test sessiyasi",
            ),
        ),
        migrations.AlterField(
            model_name="studentquestionreward",
            name="student",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="question_rewards",
                to=settings.AUTH_USER_MODEL,
                verbose_name="O‘quvchi",
            ),
        ),
        migrations.AlterField(
            model_name="testsession",
            name="answered_count",
            field=models.PositiveIntegerField(default=0, verbose_name="Javob berilgan"),
        ),
        migrations.AlterField(
            model_name="testsession",
            name="correct_count",
            field=models.PositiveIntegerField(
                default=0, verbose_name="To‘g‘ri javoblar"
            ),
        ),
        migrations.AlterField(
            model_name="testsession",
            name="duration_minutes",
            field=models.PositiveIntegerField(
                default=0, verbose_name="Davomiyligi (daq.)"
            ),
        ),
        migrations.AlterField(
            model_name="testsession",
            name="expires_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Tugash vaqti"
            ),
        ),
        migrations.AlterField(
            model_name="testsession",
            name="finalized_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Hisoblangan vaqt"
            ),
        ),
        migrations.AlterField(
            model_name="testsession",
            name="finished_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Yakunlangan vaqt"
            ),
        ),
        migrations.AlterField(
            model_name="testsession",
            name="is_finished",
            field=models.BooleanField(default=False, verbose_name="Yakunlangan"),
        ),
        migrations.AlterField(
            model_name="testsession",
            name="lesson",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="test_sessions",
                to="app.lesson",
                verbose_name="Dars",
            ),
        ),
        migrations.AlterField(
            model_name="testsession",
            name="percent",
            field=models.PositiveSmallIntegerField(default=0, verbose_name="Foiz"),
        ),
        migrations.AlterField(
            model_name="testsession",
            name="session_id",
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                editable=False,
                unique=True,
                verbose_name="Sessiya ID",
            ),
        ),
        migrations.AlterField(
            model_name="testsession",
            name="started_at",
            field=models.DateTimeField(
                auto_now_add=True, verbose_name="Boshlangan vaqt"
            ),
        ),
        migrations.AlterField(
            model_name="testsession",
            name="student",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="test_sessions",
                to=settings.AUTH_USER_MODEL,
                verbose_name="O‘quvchi",
            ),
        ),
        migrations.AlterField(
            model_name="testsession",
            name="total_questions",
            field=models.PositiveIntegerField(default=0, verbose_name="Savollar soni"),
        ),
        migrations.AlterField(
            model_name="testsession",
            name="unanswered_count",
            field=models.PositiveIntegerField(default=0, verbose_name="Javobsiz"),
        ),
        migrations.AlterField(
            model_name="testsession",
            name="wrong_count",
            field=models.PositiveIntegerField(default=0, verbose_name="Xato javoblar"),
        ),
        migrations.AlterField(
            model_name="testsessionanswer",
            name="is_correct",
            field=models.BooleanField(default=False, verbose_name="To‘g‘ri"),
        ),
        migrations.AlterField(
            model_name="testsessionanswer",
            name="question",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="test_answers",
                to="app.question",
                verbose_name="Savol",
            ),
        ),
        migrations.AlterField(
            model_name="testsessionanswer",
            name="selected_option",
            field=models.CharField(
                choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
                max_length=1,
                verbose_name="Tanlangan variant",
            ),
        ),
        migrations.AlterField(
            model_name="testsessionanswer",
            name="session",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="answers",
                to="app.testsession",
                verbose_name="Test sessiyasi",
            ),
        ),
        migrations.AlterField(
            model_name="testsessionquestion",
            name="correct_option_snapshot",
            field=models.CharField(
                blank=True,
                choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
                default="",
                max_length=1,
                verbose_name="To‘g‘ri javob nusxasi",
            ),
        ),
        migrations.AlterField(
            model_name="testsessionquestion",
            name="order",
            field=models.PositiveSmallIntegerField(verbose_name="Tartibi"),
        ),
        migrations.AlterField(
            model_name="testsessionquestion",
            name="question",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="in_test_sessions",
                to="app.question",
                verbose_name="Savol",
            ),
        ),
        migrations.AlterField(
            model_name="testsessionquestion",
            name="question_snapshot",
            field=models.JSONField(
                blank=True, default=dict, verbose_name="Savol nusxasi"
            ),
        ),
        migrations.AlterField(
            model_name="testsessionquestion",
            name="session",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="items",
                to="app.testsession",
                verbose_name="Sessiya",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="birth_date",
            field=models.DateField(
                blank=True, null=True, verbose_name="Tug‘ilgan sanasi"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="created_at",
            field=models.DateTimeField(
                default=django.utils.timezone.now, verbose_name="Yaratilgan sana"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(
                blank=True, max_length=254, null=True, verbose_name="Elektron pochta"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="first_name",
            field=models.CharField(blank=True, max_length=50, verbose_name="Ism"),
        ),
        migrations.AlterField(
            model_name="user",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Faol"),
        ),
        migrations.AlterField(
            model_name="user",
            name="is_staff",
            field=models.BooleanField(
                default=False, verbose_name="Admin panelga kira oladi"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="last_name",
            field=models.CharField(blank=True, max_length=50, verbose_name="Familiya"),
        ),
        migrations.AlterField(
            model_name="user",
            name="phone_number",
            field=models.CharField(
                max_length=13,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Telefon raqami +998XXXXXXXXX formatida bo‘lishi kerak.",
                        regex="^\\+998\\d{9}$",
                    )
                ],
                verbose_name="Telefon raqami",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="photo",
            field=models.ImageField(
                blank=True, null=True, upload_to="users/", verbose_name="Rasmi"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="preferred_language",
            field=models.CharField(
                choices=[("uz", "O‘zbek"), ("ru", "Русский"), ("en", "English")],
                default="uz",
                max_length=5,
                verbose_name="Tanlangan til",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "Administrator"),
                    ("student", "O‘quvchi"),
                    ("guest", "Mehmon"),
                ],
                default="student",
                max_length=20,
                verbose_name="Roli",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana"),
        ),
    ]
