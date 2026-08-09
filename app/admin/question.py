from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path

from app.admin.media import MultipleFileField, save_uploaded_file
from app.admin.mixins import RowActionsAdminMixin
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

        initial_course_id = self.initial.get("course")
        initial_module_id = self.initial.get("module")

        if initial_course_id:
            self.fields["module"].queryset = Module.objects.filter(
                course_id=initial_course_id
            ).order_by("order", "id")

        if initial_module_id:
            self.fields["lesson"].queryset = Lesson.objects.filter(
                module_id=initial_module_id
            ).order_by("order", "id")

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
class QuestionAdmin(RowActionsAdminMixin, PrettyImportExportModelAdmin):
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
        "row_actions",
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

    def get_model_perms(self, request):
        # Kurs, modul, dars va savollar bitta "Darslar" katalogida ko‘rsatiladi.
        return {}

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
class CourseAdmin(RowActionsAdminMixin, PrettyImportExportModelAdmin):
    resource_class = CourseResource

    list_display = (
        "id",
        "name",
        "row_actions",
    )
    search_fields = ("name",)
    ordering = ("name",)

    def get_model_perms(self, request):
        return {}


@admin.register(Module)
class ModuleAdmin(RowActionsAdminMixin, PrettyImportExportModelAdmin):
    resource_class = ModuleResource

    list_display = (
        "id",
        "course",
        "order",
        "name",
        "row_actions",
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

    def get_model_perms(self, request):
        return {}


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

        initial_course_id = self.initial.get("course")
        if initial_course_id:
            self.fields["module"].queryset = Module.objects.filter(
                course_id=initial_course_id
            ).order_by("order", "id")

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
class LessonAdmin(RowActionsAdminMixin, PrettyImportExportModelAdmin):
    resource_class = LessonResource
    form = LessonAdminForm
    change_list_template = "admin/app/lesson/change_list.html"

    list_display = (
        "id",
        "course",
        "module",
        "order",
        "name",
        "row_actions",
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

    def changelist_view(self, request, extra_context=None):
        course_id = request.GET.get("course__id__exact")
        module_id = request.GET.get("module__id__exact")
        lesson_id = request.GET.get("id__exact")

        selected_course = None
        selected_module = None
        selected_lesson = None
        stage = "courses"

        if lesson_id:
            selected_lesson = get_object_or_404(
                Lesson.objects.select_related("course", "module"),
                pk=lesson_id,
            )
            selected_course = selected_lesson.course
            selected_module = selected_lesson.module
            stage = "questions"
        elif module_id:
            selected_module = get_object_or_404(
                Module.objects.select_related("course"),
                pk=module_id,
            )
            selected_course = selected_module.course
            stage = "lessons"
        elif course_id:
            selected_course = get_object_or_404(Course, pk=course_id)
            stage = "modules"

        if course_id and selected_course and str(selected_course.pk) != course_id:
            selected_course = get_object_or_404(Course, pk=course_id)
        if module_id and selected_module and str(selected_module.pk) != module_id:
            selected_module = get_object_or_404(
                Module,
                pk=module_id,
                course=selected_course,
            )
        if (
            selected_module
            and selected_course
            and selected_module.course_id != selected_course.pk
        ):
            selected_module = get_object_or_404(
                Module,
                pk=selected_module.pk,
                course=selected_course,
            )
        if selected_lesson and selected_lesson.module_id != selected_module.pk:
            selected_lesson = get_object_or_404(
                Lesson,
                pk=selected_lesson.pk,
                module=selected_module,
            )

        catalog_context = {
            "catalog_stage": stage,
            "selected_course": selected_course,
            "selected_module": selected_module,
            "selected_lesson": selected_lesson,
            "catalog_courses": Course.objects.annotate(
                module_count=Count("modules", distinct=True),
                lesson_count=Count("lessons", distinct=True),
            ).order_by("sort_order", "name", "id"),
            "catalog_modules": Module.objects.none(),
            "catalog_lessons": Lesson.objects.none(),
            "catalog_questions": Question.objects.none(),
            "course_perms": self.admin_site._registry[Course].get_model_perms(request),
            "module_perms": self.admin_site._registry[Module].get_model_perms(request),
            "lesson_perms": self.get_model_perms(request),
            "question_perms": self.admin_site._registry[Question].get_model_perms(request),
        }

        # get_model_perms() navigatsiyani yashirish uchun bo‘sh; real CRUD
        # ruxsatlari katalog tugmalari uchun alohida hisoblanadi.
        for key, model in (
            ("course_perms", Course),
            ("module_perms", Module),
            ("lesson_perms", Lesson),
            ("question_perms", Question),
        ):
            model_admin = self.admin_site._registry[model]
            catalog_context[key] = {
                "add": model_admin.has_add_permission(request),
                "change": model_admin.has_change_permission(request),
                "delete": model_admin.has_delete_permission(request),
                "view": model_admin.has_view_permission(request),
            }

        if selected_course:
            catalog_context["catalog_modules"] = (
                Module.objects.filter(course=selected_course)
                .annotate(lesson_count=Count("lessons", distinct=True))
                .order_by("order", "id")
            )

        if selected_module:
            catalog_context["catalog_lessons"] = (
                Lesson.objects.filter(
                    course=selected_course,
                    module=selected_module,
                )
                .annotate(question_count=Count("questions", distinct=True))
                .order_by("order", "id")
            )

        if selected_lesson:
            catalog_context["catalog_questions"] = (
                Question.objects.filter(lesson=selected_lesson)
                .select_related("lesson")
                .order_by("-created_at", "id")
            )

        if extra_context:
            catalog_context.update(extra_context)

        return super().changelist_view(request, extra_context=catalog_context)

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