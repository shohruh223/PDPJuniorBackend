import uuid
from decimal import Decimal

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

from app.models.question import Course

LANGUAGES = [
    ("uz", "O‘zbek"),
    ("ru", "Русский"),
    ("en", "English"),
]


uzb_phone_validator = RegexValidator(
    regex=r"^\+998\d{9}$",
    message="Telefon raqami +998XXXXXXXXX formatida bo‘lishi kerak."
)


class BaseModel(models.Model):
    """
    Barcha modellarga umumiy UUID va timestamp fieldlar beradi.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")

    class Meta:
        abstract = True


class UserManager(BaseUserManager):
    """
    Custom user manager.
    Login phone_number orqali ishlaydi.
    """
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("Users must have a phone number!")

        role = extra_fields.pop("role", User.RoleChoices.STUDENT)
        user = self.model(phone_number=phone_number, role=role, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", User.RoleChoices.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser is_staff=True bo‘lishi shart.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser is_superuser=True bo‘lishi shart.")
        if extra_fields.get("role") != User.RoleChoices.ADMIN:
            raise ValueError("Superuser role=ADMIN bo‘lishi shart.")

        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """
    Tizimdagi asosiy foydalanuvchi modeli.
    """
    class RoleChoices(models.TextChoices):
        ADMIN = "admin", "Administrator"
        STUDENT = "student", "O‘quvchi"
        GUEST = "guest", "Mehmon"

    phone_number = models.CharField(
        max_length=13,
        validators=[uzb_phone_validator],
        unique=True
    ,
        verbose_name="Telefon raqami",
    )
    first_name = models.CharField(max_length=50, blank=True, verbose_name="Ism")
    last_name = models.CharField(max_length=50, blank=True, verbose_name="Familiya")
    email = models.EmailField(blank=True, null=True, verbose_name="Elektron pochta")

    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.STUDENT
    ,
        verbose_name="Roli",
    )

    photo = models.ImageField(upload_to="users/", blank=True, null=True, verbose_name="Rasmi")
    birth_date = models.DateField(blank=True, null=True, verbose_name="Tug‘ilgan sanasi")

    preferred_language = models.CharField(
        max_length=5,
        choices=LANGUAGES,
        default="uz"
    ,
        verbose_name="Tanlangan til",
    )

    is_active = models.BooleanField(default=True, verbose_name="Faol")
    is_staff = models.BooleanField(default=False, verbose_name="Admin panelga kira oladi")

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        # Admin jadvallarida bu matn FK ustunlarida ko'rinadi. Ilgari
        # "+998901112233 (student)" edi — rol har qatorda takrorlanib,
        # ism esa umuman ko'rinmasdi.
        name = f"{self.first_name} {self.last_name}".strip()
        return f"{name} · {self.phone_number}" if name else str(self.phone_number)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.phone_number

    @property
    def is_admin(self):
        return self.role == self.RoleChoices.ADMIN

    @property
    def is_student(self):
        return self.role == self.RoleChoices.STUDENT

    @property
    def is_guest(self):
        return self.role == self.RoleChoices.GUEST

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        ordering = ["-created_at"]



class StudentProfile(BaseModel):
    GROUP_PREFIX_TO_COURSE = {
        "P": "Python",
        "F": "Frontend",
        "M": "Microbots",
    }

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="student_profile",
        limit_choices_to={"role": User.RoleChoices.STUDENT},
        verbose_name="Foydalanuvchi",
    )
    external_id = models.UUIDField(blank=True, null=True, unique=True, db_index=True, verbose_name="Tashqi ID (PDP)")

    group_name = models.CharField(max_length=120, blank=True, db_index=True, verbose_name="Guruh nomi")
    course = models.ForeignKey(
        'app.Course',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_profiles",
        verbose_name="Kurs",
    )

    parent_phone = models.CharField(
        max_length=13,
        blank=True,
        default="",
        validators=[uzb_phone_validator],
        verbose_name="Ota-ona telefoni",
    )
    address = models.CharField(max_length=255, blank=True, default="", verbose_name="Manzil")
    bio = models.TextField(blank=True, default="", verbose_name="Qisqa ma’lumot")
    avatar_url = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Frontend yoki tashqi storage'dagi avatar URL/path.",
        verbose_name="Avatar havolasi",
    )
    streak_days = models.PositiveIntegerField(default=0, verbose_name="Ketma-ket kunlar")

    branch = models.ForeignKey(
        "app.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_profiles",
        verbose_name="Filial",
    )

    # SCORE
    api_score = models.IntegerField(default=0, verbose_name="PDP bali")
    local_test_score = models.IntegerField(default=0, verbose_name="Test bali")
    total_score = models.IntegerField(default=0, db_index=True, verbose_name="Jami ball")

    # COIN
    api_coin = models.IntegerField(default=0, verbose_name="PDP coini")
    test_coin = models.IntegerField(default=0, verbose_name="Test coini")
    lesson_last_coin = models.IntegerField(default=0, verbose_name="Oxirgi dars coini")
    total_coin = models.IntegerField(default=0, db_index=True, verbose_name="Jami coin")

    all_debtor = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Umumiy qarz",
    )
    attendance_average_percent = models.FloatField(default=0, verbose_name="O‘rtacha davomat (%)")

    last_synced_at = models.DateTimeField(blank=True, null=True, verbose_name="Oxirgi sinxronizatsiya")
    pdp_access_token = models.TextField(blank=True, null=True, verbose_name="PDP tokeni")

    # Do'konda sarflangan coin. Ilgari xarid to'g'ridan-to'g'ri api_coin dan
    # yechilardi, keyingi PDP sinxronizatsiyasi esa uni qaytarib qo'yardi —
    # ya'ni cheksiz bepul xarid. Endi api_coin faqat PDP tomonidan
    # boshqariladi, sarflangan miqdor esa shu yerda alohida yig'iladi.
    spent_coin = models.PositiveIntegerField(default=0, verbose_name="Sarflangan coin")

    # PDP dashboard endpointidan kelgan, bazada ustuni yo'q ma'lumotlar
    # (joriy dars, moduleBarchart, studentDebtors). Ilgari ular faqat
    # jonli javobda bo'lgani uchun dashboard har chaqirilganda tashqi API
    # ga bloklovchi so'rov yuborishga majbur edi. Endi bu yerda saqlanadi
    # va endpoint bazadan o'qiydi.
    external_snapshot = models.JSONField(default=dict, blank=True, verbose_name="PDP ma’lumot nusxasi")

    class Meta:
        db_table = "student_profiles"
        ordering = ["-created_at"]
        verbose_name = "O‘quvchi profili"
        verbose_name_plural = "O‘quvchi profillari"
        indexes = [
            models.Index(fields=["group_name"]),
            models.Index(fields=["course"]),
            models.Index(fields=["branch"]),
            models.Index(fields=["last_synced_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(api_score__gte=0),
                name="studentprofile_api_score_gte_0",
            ),
            models.CheckConstraint(
                check=models.Q(local_test_score__gte=0),
                name="studentprofile_local_test_score_gte_0",
            ),
            models.CheckConstraint(
                check=models.Q(api_coin__gte=0),
                name="studentprofile_api_coin_gte_0",
            ),
            models.CheckConstraint(
                check=models.Q(test_coin__gte=0),
                name="studentprofile_test_coin_gte_0",
            ),
            models.CheckConstraint(
                check=models.Q(total_score__gte=0),
                name="studentprofile_total_score_gte_0",
            ),
            models.CheckConstraint(
                check=models.Q(total_coin__gte=0),
                name="studentprofile_total_coin_gte_0",
            ),
            models.CheckConstraint(
                check=models.Q(spent_coin__gte=0),
                name="studentprofile_spent_coin_gte_0",
            ),
            models.CheckConstraint(
                check=models.Q(attendance_average_percent__gte=0)
                & models.Q(attendance_average_percent__lte=100),
                name="studentprofile_attendance_between_0_100",
            ),
        ]

    def clean(self):
        super().clean()

        if self.user and self.user.role != User.RoleChoices.STUDENT:
            raise ValidationError("StudentProfile faqat STUDENT user uchun yaratiladi.")

        if self.parent_phone == "":
            # blank bo'lsa validator bezovta qilmasin
            self.parent_phone = ""

        if self.course and self.group_name:
            resolved_name = self.resolve_course_name_from_group()
            if resolved_name and self.course.name != resolved_name:
                raise ValidationError({
                    "course": f"Group '{self.group_name}' ga mos course '{resolved_name}' bo‘lishi kerak."
                })

        self.total_score = self.calculate_total_score()
        self.total_coin = self.calculate_total_coin()

    def save(self, *args, **kwargs):
        """Validatsiya faqat to'liq saqlashda ishlaydi.

        Ilgari bu yerda har safar `full_clean()` chaqirilardi. U
        `update_fields` ni e'tiborsiz qoldiradi va har bir yozuvda
        qo'shimcha `validate_unique` SELECT'lari hamda constraint
        tekshiruvini bajaradi — ya'ni har bir to'g'ri javob va har bir
        do'kon xaridi ortiqcha so'rovlar keltirib chiqarardi. Bundan
        tashqari guruh/kurs mos kelmasa u issiq yo'lda `ValidationError`
        (500) berardi.

        Endi `update_fields` bilan chaqirilgan tor yangilanishlar (coin,
        ball, sinxronizatsiya belgisi) validatsiyadan o'tmaydi; to'liq
        saqlash — admin, forma, yangi obyekt — avvalgidek tekshiriladi.
        `skip_validation=True` bilan uni ataylab o'chirish ham mumkin.
        """
        skip_validation = kwargs.pop("skip_validation", False)
        update_fields = kwargs.get("update_fields")

        if update_fields is None:
            if not skip_validation:
                self.full_clean()
            return super().save(*args, **kwargs)

        # Tor yangilanish: ball/coin manbalari o'zgargan bo'lsa, jami
        # ko'rsatkichlar ham o'sha yozuvda yangilanadi — aks holda
        # total_* bazada eskirib qoladi.
        fields = set(update_fields)
        if fields & {"api_score", "local_test_score"}:
            self.total_score = self.calculate_total_score()
            fields.add("total_score")
        if fields & {"api_coin", "test_coin", "spent_coin"}:
            self.total_coin = self.calculate_total_coin()
            fields.add("total_coin")
        if fields != set(update_fields):
            fields.add("updated_at")
            kwargs["update_fields"] = sorted(fields)
        return super().save(*args, **kwargs)

    def calculate_total_score(self):
        return (self.api_score or 0) + (self.local_test_score or 0)

    def calculate_total_coin(self):
        earned = (self.api_coin or 0) + (self.test_coin or 0)
        return max(0, earned - (self.spent_coin or 0))

    def recalculate_total_score(self, save=True):
        self.total_score = self.calculate_total_score()
        if save:
            self.save(update_fields=["total_score", "updated_at"])
        return self.total_score

    def recalculate_total_coin(self, save=True):
        self.total_coin = self.calculate_total_coin()
        if save:
            self.save(update_fields=["total_coin", "updated_at"])
        return self.total_coin

    def recalculate_all_totals(self, save=True):
        self.total_score = self.calculate_total_score()
        self.total_coin = self.calculate_total_coin()

        if save:
            self.save(update_fields=["total_score", "total_coin", "updated_at"])

        return {
            "total_score": self.total_score,
            "total_coin": self.total_coin,
        }

    def resolve_course_name_from_group(self):
        if not self.group_name:
            return None

        group = self.group_name.strip()
        if not group:
            return None

        prefix = group[0].upper()
        return self.GROUP_PREFIX_TO_COURSE.get(prefix)

    def assign_course_from_group(self, save=True):
        from app.models.question import Course

        course_name = self.resolve_course_name_from_group()
        if not course_name:
            return None

        course, _ = Course.objects.get_or_create(name=course_name)
        self.course = course

        if save:
            self.save(update_fields=["course", "updated_at"])

        return course

    def mark_synced(self, save=True):
        self.last_synced_at = timezone.now()
        if save:
            self.save(update_fields=["last_synced_at", "updated_at"])
        return self.last_synced_at

    @property
    def direction_name(self):
        return self.course.name if self.course else None

    def __str__(self):
        return self.user.full_name