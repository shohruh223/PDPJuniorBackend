from django import forms
from django.contrib import admin
from django.utils import timezone

from app.admin.resources import PrettyImportExportModelAdmin, MonthHeroResource
from app.models.branch import Branch
from app.models.month_hero import MonthHero


class MonthHeroAdminForm(forms.ModelForm):
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all().order_by("name"),
        required=False,
        label="Filial",
        help_text="Tanlangan filial student profiliga saqlanadi.",
    )

    class Meta:
        model = MonthHero
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.student_profile_id:
            self.fields["branch"].initial = self.instance.student_profile.branch_id

    def clean(self):
        cleaned_data = super().clean()

        student_profile = cleaned_data.get("student_profile")

        if not student_profile:
            return cleaned_data

        if self.instance and self.instance.pk and self.instance.period:
            period = self.instance.period
        else:
            today = timezone.localdate()
            period = today.replace(day=1)

        exists = MonthHero.objects.filter(
            student_profile=student_profile,
            period=period,
        )

        if self.instance and self.instance.pk:
            exists = exists.exclude(pk=self.instance.pk)

        if exists.exists():
            raise forms.ValidationError(
                "Bu student shu oy uchun allaqachon Oy qahramoni sifatida qo‘shilgan. "
                "Yangisini qo‘shmang, mavjud yozuvni edit qiling."
            )

        return cleaned_data


@admin.register(MonthHero)
class MonthHeroAdmin(PrettyImportExportModelAdmin):
    resource_class = MonthHeroResource
    form = MonthHeroAdminForm

    autocomplete_fields = ("student_profile",)

    list_display = (
        "id",
        "student_full_name",
        "student_phone",
        "student_course",
        "student_branch",
        "student_score",
        "period",
        "is_active",
        "created_at",
    )

    list_filter = (
        "period",
        "is_active",
        "student_profile__course",
        "student_profile__branch",
    )

    search_fields = (
        "student_profile__user__first_name",
        "student_profile__user__last_name",
        "student_profile__user__full_name",
        "student_profile__user__phone",
        "student_profile__user__phone_number",
        "student_profile__group_name",
        "student_profile__course__name",
        "student_profile__branch__name",
    )

    readonly_fields = (
        "period",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-period",
        "-student_profile__total_score",
    )

    def get_fields(self, request, obj=None):
        if obj is None:
            return (
                "student_profile",
                "branch",
                "is_active",
            )

        return (
            "student_profile",
            "branch",
            "is_active",
            "period",
            "created_at",
            "updated_at",
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "student_profile",
                "student_profile__user",
                "student_profile__course",
                "student_profile__branch",
            )
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        branch = form.cleaned_data.get("branch")

        if obj.student_profile_id:
            student_profile = obj.student_profile
            student_profile.branch = branch
            student_profile.save(update_fields=["branch"])

    @admin.display(description="Student")
    def student_full_name(self, obj):
        if not obj.student_profile_id:
            return "-"

        user = obj.student_profile.user

        full_name = getattr(user, "full_name", None)
        if full_name:
            return full_name

        first_name = getattr(user, "first_name", "") or ""
        last_name = getattr(user, "last_name", "") or ""

        name = f"{first_name} {last_name}".strip()
        return name or "-"

    @admin.display(description="Telefon")
    def student_phone(self, obj):
        if not obj.student_profile_id:
            return "-"

        user = obj.student_profile.user

        phone = getattr(user, "phone", None)
        if phone:
            return phone

        phone_number = getattr(user, "phone_number", None)
        if phone_number:
            return phone_number

        return "-"

    @admin.display(description="Kurs")
    def student_course(self, obj):
        if not obj.student_profile_id:
            return "-"

        course = obj.student_profile.course

        if course:
            return course.name

        return "-"

    @admin.display(description="Filial")
    def student_branch(self, obj):
        if not obj.student_profile_id:
            return "-"

        branch = obj.student_profile.branch

        if branch:
            return branch.name

        return "-"

    @admin.display(description="Score")
    def student_score(self, obj):
        if not obj.student_profile_id:
            return 0

        return obj.student_profile.total_score