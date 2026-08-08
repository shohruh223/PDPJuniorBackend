from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.urls import path

from app.admin.media import MultipleFileField, save_uploaded_file
from app.admin.resources import (
    PrettyImportExportModelAdmin,
    CourseResource,
    ModuleResource,
    LessonResource,
    QuestionResource,
)
from app.models.question import Course, Module, Lesson, Question


class QuestionAdminForm(forms.ModelForm):
    course = forms.ModelChoiceField(
        label="Kurs",
        queryset=Course.objects.all(),
        required=True,
        empty_label="Kursni tanlang",
    )

    module = forms.ModelChoiceField(
        label="Module",
        queryset=Module.objects.none(),
        required=True,
        empty_label="Avval kursni tanlang",
    )

    lesson = forms.ModelChoiceField(
        label="Lesson",
        queryset=Lesson.objects.none(),
        required=True,
        empty_label="Avval moduleni tanlang",
    )

    question_text = forms.CharField(
        label="Savol matni",
        required=True,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Savol matnini kiriting",
            }
        ),
    )

    option_a = forms.CharField(label="A varianti", required=True)
    option_b = forms.CharField(label="B varianti", required=True)
    option_c = forms.CharField(label="C varianti", required=False)
    option_d = forms.CharField(label="D varianti", required=False)

    question_images = MultipleFileField(
        label="Savol rasmlari",
        required=False,
        help_text="Bir nechta rasm yuklash mumkin.",
    )

    class Meta:
        model = Question
        fields = (
            "lesson",
            "correct_option",
            "text",
            "images",
            "options",
        )
        widgets = {
            "text": forms.HiddenInput(),
            "images": forms.HiddenInput(),
            "options": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["text"].required = False
        self.fields["images"].required = False
        self.fields["options"].required = False

        text = self.instance.text if isinstance(self.instance.text, dict) else {}
        options = self.instance.options if isinstance(self.instance.options, dict) else {}

        self.fields["question_text"].initial = text.get("uz", "")

        for option_key in ("A", "B", "C", "D"):
            option_data = options.get(option_key, {})

            if not isinstance(option_data, dict):
                option_data = {}

            self.fields[f"option_{option_key.lower()}"].initial = option_data.get("uz", "")

        self.fields["course"].queryset = Course.objects.all().order_by("id")
        self.fields["module"].queryset = Module.objects.none()
        self.fields["lesson"].queryset = Lesson.objects.none()

        if self.instance and self.instance.pk and self.instance.lesson_id:
            lesson = self.instance.lesson
            module = lesson.module
            course = lesson.course

            self.fields["course"].initial = course
            self.fields["module"].initial = module
            self.fields["lesson"].initial = lesson

            self.fields["module"].queryset = Module.objects.filter(
                course=course
            ).order_by("order", "id")

            self.fields["lesson"].queryset = Lesson.objects.filter(
                module=module
            ).order_by("order", "id")

        if self.data:
            course_id = self.data.get("course")
            module_id = self.data.get("module")

            if course_id:
                self.fields["module"].queryset = Module.objects.filter(
                    course_id=course_id
                ).order_by("order", "id")

            if module_id:
                self.fields["lesson"].queryset = Lesson.objects.filter(
                    module_id=module_id
                ).order_by("order", "id")

    def _build_lang_value(self, value):
        value = (value or "").strip()

        return {
            "uz": value,
            "ru": value,
            "en": value,
        }

    def _build_option(self, option_key):
        value = self.cleaned_data.get(f"option_{option_key.lower()}") or ""
        value = value.strip()

        if not value:
            return None

        return self._build_lang_value(value)

    def clean(self):
        cleaned_data = super().clean()

        course = cleaned_data.get("course")
        module = cleaned_data.get("module")
        lesson = cleaned_data.get("lesson")
        correct_option = cleaned_data.get("correct_option")

        if course and module and module.course_id != course.id:
            raise ValidationError("Tanlangan module shu kursga tegishli emas.")

        if module and lesson and lesson.module_id != module.id:
            raise ValidationError("Tanlangan lesson shu modulega tegishli emas.")

        if course and lesson and lesson.course_id != course.id:
            raise ValidationError("Tanlangan lesson shu kursga tegishli emas.")

        options = {}

        for option_key in ("A", "B", "C", "D"):
            option = self._build_option(option_key)

            if option:
                options[option_key] = option

        if len(options) < 2:
            raise ValidationError("Kamida 2 ta variant kiritilishi kerak.")

        if correct_option and correct_option not in options:
            raise ValidationError(
                "To‘g‘ri javob tanlangan variantlar ichida bo‘lishi kerak."
            )

        cleaned_data["text"] = self._build_lang_value(
            cleaned_data.get("question_text", "")
        )
        cleaned_data["options"] = options

        current_images = self.instance.images if isinstance(self.instance.images, dict) else {}
        cleaned_data["images"] = current_images

        return cleaned_data

    def _get_next_image_key(self, images):
        max_number = 0

        for key in images.keys():
            if not isinstance(key, str):
                continue

            if not key.startswith("image_"):
                continue

            try:
                number = int(key.replace("image_", ""))
                max_number = max(max_number, number)
            except ValueError:
                continue

        return max_number + 1

    def save(self, commit=True):
        obj = super().save(commit=False)

        obj.lesson = self.cleaned_data["lesson"]

        obj.text = self._build_lang_value(
            self.cleaned_data["question_text"]
        )

        options = {}

        for option_key in ("A", "B", "C", "D"):
            option = self._build_option(option_key)

            if option:
                options[option_key] = option

        obj.options = options

        images = obj.images if isinstance(obj.images, dict) else {}
        uploaded_images = self.cleaned_data.get("question_images") or []

        next_image_number = self._get_next_image_key(images)

        for uploaded in uploaded_images:
            saved_path = save_uploaded_file(uploaded, "questions/images")
            images[f"image_{next_image_number}"] = saved_path
            next_image_number += 1

        obj.images = images

        if commit:
            obj.save()

        return obj


@admin.register(Question)
class QuestionAdmin(PrettyImportExportModelAdmin):
    resource_class = QuestionResource
    form = QuestionAdminForm

    fields = (
        "course",
        "module",
        "lesson",
        "question_text",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "correct_option",
        "question_images",
        "text",
        "images",
        "options",
    )

    list_display = (
        "id",
        "lesson",
        "correct_option",
        "created_at",
    )
    list_filter = (
        "correct_option",
        "created_at",
        "lesson__course",
        "lesson__module",
    )
    search_fields = (
        "text__uz",
        "lesson__name",
        "lesson__module__name",
        "lesson__course__name",
    )
    ordering = ("-created_at",)

    class Media:
        js = (
            "app/admin/js/question_filter.js",
        )

    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path(
                "get-modules/",
                self.admin_site.admin_view(self.get_modules),
                name="question-get-modules",
            ),
            path(
                "get-lessons/",
                self.admin_site.admin_view(self.get_lessons),
                name="question-get-lessons",
            ),
        ]

        return custom_urls + urls

    def get_modules(self, request):
        course_id = request.GET.get("course_id")

        modules = Module.objects.none()

        if course_id:
            modules = Module.objects.filter(
                course_id=course_id
            ).order_by("order", "id")

        data = [
            {
                "id": module.id,
                "name": str(module),
            }
            for module in modules
        ]

        return JsonResponse({"results": data})

    def get_lessons(self, request):
        module_id = request.GET.get("module_id")

        lessons = Lesson.objects.none()

        if module_id:
            lessons = Lesson.objects.filter(
                module_id=module_id
            ).order_by("order", "id")

        data = [
            {
                "id": lesson.id,
                "name": str(lesson),
            }
            for lesson in lessons
        ]

        return JsonResponse({"results": data})


@admin.register(Course)
class CourseAdmin(PrettyImportExportModelAdmin):
    resource_class = CourseResource

    list_display = (
        "id",
        "name",
    )
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Module)
class ModuleAdmin(PrettyImportExportModelAdmin):
    resource_class = ModuleResource

    list_display = (
        "id",
        "course",
        "order",
        "name",
    )
    list_filter = ("course",)
    search_fields = (
        "name",
        "course__name",
    )
    ordering = (
        "course",
        "order",
        "id",
    )


class LessonAdminForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = (
            "course",
            "module",
            "name",
            "order",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["module"].queryset = Module.objects.none()

        if self.instance and self.instance.pk and self.instance.course_id:
            self.fields["module"].queryset = Module.objects.filter(
                course_id=self.instance.course_id
            ).order_by("order", "id")

        if self.data:
            course_id = self.data.get("course")

            if course_id:
                self.fields["module"].queryset = Module.objects.filter(
                    course_id=course_id
                ).order_by("order", "id")

    def clean(self):
        cleaned_data = super().clean()

        course = cleaned_data.get("course")
        module = cleaned_data.get("module")

        if course and module and module.course_id != course.id:
            raise ValidationError("Tanlangan module shu kursga tegishli emas.")

        return cleaned_data


@admin.register(Lesson)
class LessonAdmin(PrettyImportExportModelAdmin):
    resource_class = LessonResource
    form = LessonAdminForm

    list_display = (
        "id",
        "course",
        "module",
        "order",
        "name",
    )
    list_filter = (
        "course",
        "module",
    )
    search_fields = (
        "name",
        "course__name",
        "module__name",
    )
    ordering = (
        "module__order",
        "order",
        "id",
    )

    class Media:
        js = (
            "app/admin/js/lesson_filter.js",
        )

    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path(
                "get-modules/",
                self.admin_site.admin_view(self.get_lesson_modules),
                name="lesson-get-modules",
            ),
        ]

        return custom_urls + urls

    def get_lesson_modules(self, request):
        course_id = request.GET.get("course_id")

        modules = Module.objects.none()

        if course_id:
            modules = Module.objects.filter(
                course_id=course_id
            ).order_by("order", "id")

        data = [
            {
                "id": module.id,
                "name": str(module),
            }
            for module in modules
        ]

        return JsonResponse({"results": data})