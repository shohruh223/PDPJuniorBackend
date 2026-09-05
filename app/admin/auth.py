from urllib.parse import urlencode

from django import forms
from django.contrib import admin
from django.contrib.admin.options import IS_POPUP_VAR
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse

from app.admin.forms import AdminPhoneAuthenticationForm
from app.admin.mixins import NoFilterSidebarChangeList
from app.admin.resources import (
    PrettyImportExportModelAdmin,
    StudentProfileResource,
    UserResource,
)
from app.models.auth import User, StudentProfile
from app.models.branch import Branch


admin.site.login_form = AdminPhoneAuthenticationForm


class UserAdminForm(forms.ModelForm):
    password = forms.CharField(
        label="Parol",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Yangi parol kiriting",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = User
        fields = (
            "phone_number",
            "password",
            "first_name",
            "last_name",
            "role",
            "photo",
            "is_active",
            "is_staff",
            "is_superuser",
        )
        labels = {
            "phone_number": "Telefon raqami",
            "first_name": "Ism",
            "last_name": "Familiya",
            "role": "Rol",
            "photo": "Rasm",
            "is_active": "Faol",
            "is_staff": "Admin",
            "is_superuser": "Superuser",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["password"].help_text = (
                "Bo‘sh qoldirilsa, eski parol o‘zgarmaydi."
            )
        else:
            self.fields["password"].help_text = (
                "Kirish uchun parol. Bo‘sh qoldirilsa, parol o‘rnatilmaydi."
            )
        if "is_active" in self.fields:
            self.fields["is_active"].help_text = (
                "Admin kirish huquqiga ega emas."
            )
        if "is_staff" in self.fields:
            self.fields["is_staff"].help_text = (
                "Belgilansa, foydalanuvchi admin panelga kira oladi."
            )
        if "is_superuser" in self.fields:
            self.fields["is_superuser"].help_text = (
                "Belgilansa, foydalanuvchi barcha ruxsatlarga ega bo‘ladi."
            )

    def save(self, commit=True):
        obj = super().save(commit=False)

        password = self.cleaned_data.get("password")

        if password:
            obj.set_password(password)
        elif obj.pk:
            old_obj = User.objects.get(pk=obj.pk)
            obj.password = old_obj.password
        else:
            obj.set_unusable_password()

        if commit:
            obj.save()

        return obj


class UserCatalogChangeList(NoFilterSidebarChangeList):
    """Katalog query parametrlarini Django lookup sifatida qabul qilmaydi."""

    def get_filters_params(self, params=None):
        lookup_params = super().get_filters_params(params)
        for key in ("branch", "course", "group", "no_profile"):
            lookup_params.pop(key, None)
        return lookup_params


@admin.register(User)
class UserAdmin(PrettyImportExportModelAdmin):
    resource_class = UserResource
    form = UserAdminForm
    change_list_template = "admin/app/user/change_list.html"
    import_export_change_list_template = None
    actions = None

    fields = (
        "phone_number",
        "password",
        "first_name",
        "last_name",
        "role",
        "photo",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    list_display = (
        "phone_number",
        "full_name_display",
        "student_group_display",
        "student_score_display",
        "role",
        "is_active",
        "created_at",
    )
    search_fields = (
        "phone_number",
        "first_name",
        "last_name",
        "email",
        "student_profile__group_name",
        "student_profile__course__name",
        "student_profile__branch__name",
    )
    ordering = ("-created_at",)
    list_select_related = (
        "student_profile",
        "student_profile__branch",
        "student_profile__course",
    )

    EMPTY_KEY = "none"

    def get_changelist(self, request, **kwargs):
        return UserCatalogChangeList

    def _is_popup(self, request):
        return IS_POPUP_VAR in request.GET

    def _catalog_stage(self, request):
        if self._is_popup(request) or request.GET.get("no_profile"):
            return "users"
        if "group" in request.GET:
            return "users"
        branch = request.GET.get("branch")
        if branch and branch != self.EMPTY_KEY:
            return "groups"
        return "branches"

    def _catalog_url(self, **params):
        query = {key: value for key, value in params.items() if value is not None}
        base = reverse("admin:app_user_changelist")
        if not query:
            return base
        return f"{base}?{urlencode(query)}" if query else base

    def _add_user_url(self, request):
        params = {}
        for key in ("branch", "course", "group", "no_profile"):
            if key in request.GET and request.GET.get(key) not in (None, ""):
                params[key] = request.GET.get(key)
        base = reverse("admin:app_user_add")
        if not params:
            return base
        return f"{base}?{urlencode(params)}"

    def _catalog_params(self, request):
        return {
            key: request.GET.get(key)
            for key in ("branch", "course", "group", "no_profile")
            if request.GET.get(key) not in (None, "")
        }

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        for key in ("branch", "course", "group", "no_profile"):
            initial.pop(key, None)
        return initial

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None and request.GET.get("no_profile"):
            form.base_fields["role"].initial = User.RoleChoices.ADMIN
            form.base_fields["is_staff"].initial = True
        return form

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.role != User.RoleChoices.STUDENT:
            return

        profile, created = StudentProfile.objects.get_or_create(user=obj)
        if change and not created:
            return

        branch_id = request.GET.get("branch")
        course_id = request.GET.get("course")
        group = request.GET.get("group")

        if branch_id and branch_id != self.EMPTY_KEY:
            profile.branch_id = branch_id

        if course_id == self.EMPTY_KEY:
            profile.course = None
        elif course_id:
            profile.course_id = course_id

        if group == self.EMPTY_KEY:
            profile.group_name = ""
        elif group:
            profile.group_name = group

        profile.save()

    def response_add(self, request, obj, post_url_continue=None):
        if "_continue" not in request.POST and "_addanother" not in request.POST:
            catalog = self._catalog_params(request)
            if catalog:
                return HttpResponseRedirect(self._catalog_url(**catalog))
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        if "_continue" not in request.POST and "_addanother" not in request.POST:
            catalog = self._catalog_params(request)
            if catalog:
                return HttpResponseRedirect(self._catalog_url(**catalog))
        return super().response_change(request, obj)

    def _profile_of(self, obj):
        try:
            return obj.student_profile
        except ObjectDoesNotExist:
            return None

    @admin.display(description="F.I.Sh.")
    def full_name_display(self, obj):
        return obj.full_name

    @admin.display(description="Guruh")
    def student_group_display(self, obj):
        profile = self._profile_of(obj)
        if not profile:
            return "—"
        return profile.group_name or "Guruhsiz"

    @admin.display(description="Ball")
    def student_score_display(self, obj):
        profile = self._profile_of(obj)
        return profile.total_score if profile else "—"

    def _is_changelist_request(self, request):
        match = getattr(request, "resolver_match", None)
        return bool(match and match.url_name == "app_user_changelist")

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            "student_profile",
            "student_profile__branch",
            "student_profile__course",
        )

        if self._is_popup(request) or not self._is_changelist_request(request):
            return qs

        if request.GET.get("no_profile"):
            return qs.filter(
                Q(role=User.RoleChoices.ADMIN) | Q(is_staff=True) | Q(is_superuser=True)
            )

        if self._catalog_stage(request) != "users":
            return qs.none()

        branch_id = request.GET.get("branch")
        course_id = request.GET.get("course")
        group = request.GET.get("group")

        qs = qs.filter(student_profile__isnull=False)

        if branch_id and branch_id != self.EMPTY_KEY:
            qs = qs.filter(student_profile__branch_id=branch_id)

        if course_id == self.EMPTY_KEY:
            qs = qs.filter(student_profile__course__isnull=True)
        elif course_id:
            qs = qs.filter(student_profile__course_id=course_id)

        if group == self.EMPTY_KEY:
            qs = qs.filter(Q(student_profile__group_name="") | Q(student_profile__group_name__isnull=True))
        elif group:
            qs = qs.filter(student_profile__group_name=group)

        return qs

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(self._user_catalog_context(request))
        return super().changelist_view(request, extra_context=extra_context)

    def _user_catalog_context(self, request):
        stage = self._catalog_stage(request)
        branch_id = request.GET.get("branch")
        group_key = request.GET.get("group")

        selected_branch = None
        selected_group = None
        selected_group_label = None

        if branch_id and branch_id != self.EMPTY_KEY:
            selected_branch = get_object_or_404(Branch, pk=branch_id)
        if group_key is not None:
            selected_group = group_key
            selected_group_label = (
                "Guruhsiz" if group_key == self.EMPTY_KEY else group_key
            )

        profiles = StudentProfile.objects.all()
        if selected_branch:
            profiles = profiles.filter(branch=selected_branch)

        catalog_branches = list(
            Branch.objects.annotate(
                student_count=Count("student_profiles", distinct=True),
            ).order_by("name", "id")
        )
        no_profile_count = User.objects.filter(
            Q(role=User.RoleChoices.ADMIN) | Q(is_staff=True) | Q(is_superuser=True)
        ).count()

        catalog_groups = []
        ungrouped_count = 0
        if stage in {"groups", "users"}:
            catalog_groups = list(
                profiles.exclude(group_name="")
                .values("group_name")
                .annotate(student_count=Count("id"))
                .order_by("group_name")
            )
            ungrouped_count = profiles.filter(
                Q(group_name="") | Q(group_name__isnull=True)
            ).count()

        titles = {
            "branches": "Filiallar",
            "groups": (
                f"{selected_branch.name} guruhlari"
                if selected_branch
                else "Guruhlar"
            ),
            "users": (
                "Adminlar"
                if request.GET.get("no_profile")
                else f"{selected_group_label} guruh foydalanuvchilari"
            ),
        }

        return {
            "catalog_stage": stage,
            "selected_branch": selected_branch,
            "selected_group": selected_group,
            "selected_group_label": selected_group_label,
            "branch_is_empty": branch_id == self.EMPTY_KEY,
            "group_is_empty": group_key == self.EMPTY_KEY,
            "no_profile": bool(request.GET.get("no_profile")),
            "catalog_branches": catalog_branches,
            "catalog_groups": catalog_groups,
            "ungrouped_count": ungrouped_count,
            "no_profile_count": no_profile_count,
            "empty_key": self.EMPTY_KEY,
            "branches_url": self._catalog_url(),
            "groups_url": self._catalog_url(
                branch=branch_id,
            ) if branch_id else self._catalog_url(),
            "add_user_url": self._add_user_url(request),
            "title": titles[stage],
        }


@admin.register(StudentProfile)
class StudentProfileAdmin(PrettyImportExportModelAdmin):
    list_select_related = ("user", "course", "branch")
    resource_class = StudentProfileResource

    def get_model_perms(self, request):
        return {}

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
        "avatar_url",
        "streak_days",
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