from django.db import models
from django.core.exceptions import ValidationError
from root.settings import LANGUAGES

LANGUAGE_CODES = {code for code, _ in LANGUAGES}
REQUIRED_LANGUAGE_CODES = {"uz", "ru", "en"}


def validate_i18n_json(value, required=True):
    """
    Ko'p tilli JSON validator.

    Misol:
    {
        "uz": "Savol matni",
        "ru": "Текст вопроса",
        "en": "Question text"
    }
    """
    if not isinstance(value, dict):
        raise ValidationError("Qiymat dict bo'lishi kerak.")

    invalid_keys = [key for key in value.keys() if key not in LANGUAGE_CODES]
    if invalid_keys:
        raise ValidationError(f"Noto'g'ri til kodi: {', '.join(invalid_keys)}")

    if required:
        missing_keys = REQUIRED_LANGUAGE_CODES - set(value.keys())
        if missing_keys:
            raise ValidationError(
                f"Quyidagi tillar majburiy: {', '.join(sorted(missing_keys))}"
            )

    for lang_code, text in value.items():
        if not isinstance(text, str):
            raise ValidationError(f"{lang_code} uchun qiymat string bo'lishi kerak.")

        if not text.strip():
            raise ValidationError(f"{lang_code} uchun matn bo'sh bo'lmasligi kerak.")


def validate_images_json(value):
    """
    images uchun oddiy validator.
    Misol:
    {
        "main": "https://example.com/image1.png",
        "extra": "https://example.com/image2.png"
    }
    """
    if not isinstance(value, dict):
        raise ValidationError("images dict bo'lishi kerak.")

    for key, image in value.items():
        if not isinstance(key, str):
            raise ValidationError("images kalitlari string bo'lishi kerak.")
        if not isinstance(image, str):
            raise ValidationError(f"images['{key}'] string bo'lishi kerak.")


class Course(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    image_url = models.CharField(max_length=500, blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Kurs"
        verbose_name_plural = "Kurslar"
        ordering = ["sort_order", "name", "id"]


class Module(models.Model):
    course = models.ForeignKey(
        "app.Course",
        on_delete=models.CASCADE,
        related_name="modules"
    )
    name = models.CharField(max_length=255)
    order = models.PositiveIntegerField()

    class Meta:
        db_table = "modules"
        ordering = ["order", "id"]
        unique_together = ("course", "order")

    def __str__(self):
        return f"{self.course.name} | {self.order}-modul | {self.name}"


class Lesson(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lessons"
    )
    module = models.ForeignKey(
        "app.Module",
        on_delete=models.CASCADE,
        related_name="lessons"
    )
    name = models.CharField(max_length=255)
    order = models.PositiveIntegerField()

    class Meta:
        verbose_name = "Dars"
        verbose_name_plural = "Darslar"
        ordering = ["module__order", "order", "id"]
        unique_together = ("module", "order")
        constraints = [
            models.UniqueConstraint(
                fields=["module", "name"],
                name="unique_lesson_name_per_module"
            )
        ]

    def clean(self):
        if self.module and self.course_id != self.module.course_id:
            raise ValidationError("Lesson course bilan module course bir xil bo‘lishi kerak")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.module.order}-modul | {self.order}-dars | {self.name}"


class Question(models.Model):
    OPTION_CHOICES = [
        ("A", "A"),
        ("B", "B"),
        ("C", "C"),
        ("D", "D"),
    ]
    ALLOWED_OPTION_KEYS = {key for key, _ in OPTION_CHOICES}

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="questions"
    )

    text = models.JSONField()
    images = models.JSONField(blank=True, default=dict)
    options = models.JSONField()

    correct_option = models.CharField(
        max_length=1,
        choices=OPTION_CHOICES
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def _validate_options(self):
        if not isinstance(self.options, dict):
            raise ValidationError({"options": "options dict bo'lishi kerak."})

        option_count = len(self.options)
        if option_count < 2:
            raise ValidationError({"options": "Minimum 2 ta variant bo'lishi kerak."})
        if option_count > 4:
            raise ValidationError({"options": "Maksimum 4 ta variant bo'lishi mumkin."})

        option_keys = set(self.options.keys())
        if not option_keys.issubset(self.ALLOWED_OPTION_KEYS):
            raise ValidationError({"options": "Variantlar faqat A, B, C, D bo'lishi mumkin."})

        for key, value in self.options.items():
            try:
                validate_i18n_json(value, required=True)
            except ValidationError as e:
                raise ValidationError({"options": [f"{key}: {msg}" for msg in e.messages]})

    def clean(self):
        errors = {}

        if not self.lesson_id:
            errors["lesson"] = "lesson tanlanishi kerak."

        try:
            validate_i18n_json(self.text, required=True)
        except ValidationError as e:
            errors["text"] = e.messages

        try:
            self._validate_options()
        except ValidationError as e:
            if hasattr(e, "message_dict"):
                errors.update(e.message_dict)
            else:
                errors["options"] = e.messages

        if isinstance(self.options, dict) and self.correct_option not in self.options:
            errors["correct_option"] = "correct_option options ichida mavjud bo'lishi kerak."

        try:
            validate_images_json(self.images)
        except ValidationError as e:
            errors["images"] = e.messages

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def is_correct(self, answer):
        return answer == self.correct_option

    @property
    def course(self):
        return self.lesson.course if self.lesson_id else None

    def __str__(self):
        uz = (self.text or {}).get("uz")
        ru = (self.text or {}).get("ru")
        en = (self.text or {}).get("en")
        title = uz or ru or en or ""
        return f"{self.lesson.order}-dars | {self.lesson.name} | {title[:60]}"

    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
        ordering = ["-created_at"]