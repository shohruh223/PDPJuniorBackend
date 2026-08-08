from django import forms
from django.contrib import admin
from django.contrib.auth.hashers import make_password

from app.admin.resources import (
    PrettyImportExportModelAdmin,
    StudentProfileResource,
    UserResource,
)
from app.models.auth import User, StudentProfile


class UserAdminForm(forms.ModelForm):
    password = forms.CharField(
        label="Parol",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Yangi parol kiriting",
            }
        ),
        help_text="Bo‘sh qoldirilsa, eski parol o‘zgarmaydi.",
    )

    class Meta:
        model = User
        fields = (
            "phone_number",
            "password",
            "role",
            "photo",
            "preferred_language",
            "is_active",
            "is_staff",
        )

    def save(self, commit=True):
        obj = super().save(commit=False)

        password = self.cleaned_data.get("password")

        if password:
            obj.password = make_password(password)
        elif obj.pk:
            old_obj = User.objects.get(pk=obj.pk)
            obj.password = old_obj.password

        if commit:
            obj.save()

        return obj


@admin.register(User)
class UserAdmin(PrettyImportExportModelAdmin):
    resource_class = UserResource
    form = UserAdminForm

    fields = (
        "phone_number",
        "password",
        "role",
        "photo",
        "preferred_language",
        "is_active",
        "is_staff",
    )

    list_display = (
        "id",
        "phone_number",
        "role",
        "is_active",
        "is_staff",
        "created_at",
    )
    list_filter = (
        "role",
        "is_active",
        "is_staff",
    )
    search_fields = (
        "phone_number",
    )
    ordering = ("-created_at",)


@admin.register(StudentProfile)
class StudentProfileAdmin(PrettyImportExportModelAdmin):
    resource_class = StudentProfileResource

    list_display = (
        "id",
        "user",
        "group_name",
        "course",
        "branch",
        "total_score",
        "total_coin",
        "all_debtor",
        "attendance_average_percent",
    )
    list_filter = (
        "course",
        "branch",
        "group_name",
    )
    search_fields = (
        "user__phone_number",
        "group_name",
        "parent_phone",
    )
    readonly_fields = (
        "external_id",
        "api_score",
        "local_test_score",
        "total_score",
        "api_coin",
        "test_coin",
        "lesson_last_coin",
        "total_coin",
        "all_debtor",
        "attendance_average_percent",
        "last_synced_at",
        "pdp_access_token",
        "created_at",
        "updated_at",
    )
    fields = (
        "user",
        "group_name",
        "course",
        "branch",
        "parent_phone",
        "address",
        "bio",
        "external_id",
        "api_score",
        "local_test_score",
        "total_score",
        "api_coin",
        "test_coin",
        "lesson_last_coin",
        "total_coin",
        "all_debtor",
        "attendance_average_percent",
        "last_synced_at",
        "pdp_access_token",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)