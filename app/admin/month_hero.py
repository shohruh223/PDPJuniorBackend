from datetime import date
from urllib.parse import urlencode

from django import forms
from django.contrib import admin
from django.db.models import Count
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import path, reverse
from django.utils import timezone

from app.admin.resources import PrettyImportExportModelAdmin, MonthHeroResource
from app.models.auth import StudentProfile
from app.models.branch import Branch
from app.models.month_hero import MonthHero
from app.models.question import Course


def _requested_year(request, hero_id=None) -> int:
    """AJAX so'rovidagi yil: aniq berilgan, yoki tahrirlanayotgan yozuvniki."""
    raw = request.GET.get("year")
    if raw:
        try:
            value = int(raw)
            if 2000 <= value <= 2100:
                return value
        except (TypeError, ValueError):
            pass

    if hero_id:
        period = (
            MonthHero.objects.filter(pk=hero_id)
            .values_list("period", flat=True)
            .first()
        )
        if period:
            return period.year

    return timezone.localdate().year


class MonthHeroAdminForm(forms.ModelForm):
    MONTH_NAMES = (
        "Yanvar",
        "Fevral",
        "Mart",
        "Aprel",
        "May",
        "Iyun",
        "Iyul",
        "Avgust",
        "Sentabr",
        "Oktabr",
        "Noyabr",
        "Dekabr",
    )

    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(is_active=True),
        required=True,
        label="Kurs",
        empty_label="Kursni tanlang",
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.none(),
        required=True,
        label="Filial",
        empty_label="Avval kursni tanlang",
    )
    group_name = forms.ChoiceField(
        choices=(("", "Avval filialni tanlang"),),
        required=True,
        label="Guruh",
    )
    student_profile = forms.ModelChoiceField(
        queryset=StudentProfile.objects.none(),
        required=True,
        label="Student",
        empty_label="Avval guruhni tanlang",
    )
    period = forms.TypedChoiceField(
        choices=(),
        coerce=date.fromisoformat,
        required=True,
        label="Oy",
        empty_value=None,
    )

    class Meta:
        model = MonthHero
        fields = (
            "student_profile",
            "period",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        today = timezone.localdate()
        choice_year = (
            self.instance.period.year
            if self.instance and self.instance.pk and self.instance.period
            else today.year
        )
        self.fields["period"].choices = [
            (
                date(choice_year, month_number, 1).isoformat(),
                f"{month_name} {choice_year}",
            )
            for month_number, month_name in enumerate(self.MONTH_NAMES, start=1)
        ]

        selected_course_id = self.data.get("course") or self.initial.get("course")
        selected_branch_id = self.data.get("branch") or self.initial.get("branch")
        selected_group = self.data.get("group_name") or self.initial.get("group_name")

        if self.instance and self.instance.pk and self.instance.student_profile_id:
            student = self.instance.student_profile
            selected_course_id = selected_course_id or student.course_id
            selected_branch_id = selected_branch_id or student.branch_id
            selected_group = selected_group or student.group_name

            self.fields["course"].initial = student.course_id
            self.fields["branch"].initial = student.branch_id
            self.fields["group_name"].initial = student.group_name
            self.fields["student_profile"].initial = student.pk
            self.fields["period"].initial = self.instance.period
        else:
            self.fields["period"].initial = today.replace(day=1)

        if selected_course_id:
            self.fields["branch"].queryset = (
                Branch.objects.filter(
                    is_active=True,
                    student_profiles__course_id=selected_course_id,
                )
                .distinct()
                .order_by("name", "id")
            )

        if selected_course_id and selected_branch_id:
            groups = (
                StudentProfile.objects.filter(
                    course_id=selected_course_id,
                    branch_id=selected_branch_id,
                )
                .exclude(group_name="")
                .values_list("group_name", flat=True)
                .distinct()
                .order_by("group_name")
            )
            self.fields["group_name"].choices = [
                ("", "Guruhni tanlang"),
                *((group_name, group_name) for group_name in groups),
            ]

        if selected_course_id and selected_branch_id and selected_group:
            self.fields["student_profile"].queryset = (
                StudentProfile.objects.filter(
                    course_id=selected_course_id,
                    branch_id=selected_branch_id,
                    group_name=selected_group,
                )
                .select_related("user", "course", "branch")
                .order_by("user__first_name", "user__last_name", "id")
            )

    def clean(self):
        cleaned_data = super().clean()

        course = cleaned_data.get("course")
        branch = cleaned_data.get("branch")
        group_name = cleaned_data.get("group_name")
        student_profile = cleaned_data.get("student_profile")
        period = cleaned_data.get("period")

        if not student_profile:
            return cleaned_data

        if course and student_profile.course_id != course.pk:
            self.add_error("student_profile", "Student tanlangan kursga tegishli emas.")
        if branch and student_profile.branch_id != branch.pk:
            self.add_error("student_profile", "Student tanlangan filialga tegishli emas.")
        if group_name and student_profile.group_name != group_name:
            self.add_error("student_profile", "Student tanlangan guruhga tegishli emas.")

        if period:
            exists = MonthHero.objects.filter(
                student_profile=student_profile,
                period=period,
            )

            if self.instance and self.instance.pk:
                exists = exists.exclude(pk=self.instance.pk)

            if exists.exists():
                raise forms.ValidationError(
                    "Bu student shu oy uchun allaqachon Oy qahramoni sifatida "
                    "qo‘shilgan. Yangisini qo‘shmang, mavjud yozuvni edit qiling."
                )

        return cleaned_data


@admin.register(MonthHero)
class MonthHeroAdmin(PrettyImportExportModelAdmin):
    resource_class = MonthHeroResource
    form = MonthHeroAdminForm
    change_list_template = "admin/app/monthhero/change_list.html"
    import_export_change_list_template = None
    actions = None

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
        "student_profile__user__phone_number",
        "student_profile__group_name",
        "student_profile__course__name",
        "student_profile__branch__name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-period",
        "-student_profile__total_score",
    )

    MONTH_NAMES = (
        "Yanvar",
        "Fevral",
        "Mart",
        "Aprel",
        "May",
        "Iyun",
        "Iyul",
        "Avgust",
        "Sentabr",
        "Oktabr",
        "Noyabr",
        "Dekabr",
    )

    class Media:
        js = ("app/admin/js/month_hero_filter.js",)

    def add_view(self, request, form_url="", extra_context=None):
        context = {
            "title": "Oy qahramonini qo‘shish",
        }
        if extra_context:
            context.update(extra_context)
        return super().add_view(request, form_url, extra_context=context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "get-branches/",
                self.admin_site.admin_view(self.get_hero_branches),
                name="monthhero-get-branches",
            ),
            path(
                "get-groups/",
                self.admin_site.admin_view(self.get_hero_groups),
                name="monthhero-get-groups",
            ),
            path(
                "get-students/",
                self.admin_site.admin_view(self.get_hero_students),
                name="monthhero-get-students",
            ),
            path(
                "get-months/",
                self.admin_site.admin_view(self.get_hero_months),
                name="monthhero-get-months",
            ),
        ]
        return custom_urls + urls

    def get_hero_branches(self, request):
        course_id = request.GET.get("course_id")
        branches = Branch.objects.none()

        if course_id:
            branches = (
                Branch.objects.filter(
                    is_active=True,
                    student_profiles__course_id=course_id,
                )
                .distinct()
                .order_by("name", "id")
            )

        return JsonResponse(
            {
                "results": [
                    {"id": branch.pk, "name": branch.name}
                    for branch in branches
                ]
            }
        )

    def get_hero_groups(self, request):
        course_id = request.GET.get("course_id")
        branch_id = request.GET.get("branch_id")
        groups = StudentProfile.objects.none()

        if course_id and branch_id:
            groups = (
                StudentProfile.objects.filter(
                    course_id=course_id,
                    branch_id=branch_id,
                )
                .exclude(group_name="")
                .values_list("group_name", flat=True)
                .distinct()
                .order_by("group_name")
            )

        return JsonResponse(
            {
                "results": [
                    {"id": group_name, "name": group_name}
                    for group_name in groups
                ]
            }
        )

    def get_hero_students(self, request):
        course_id = request.GET.get("course_id")
        branch_id = request.GET.get("branch_id")
        group_name = request.GET.get("group_name")
        students = StudentProfile.objects.none()

        if course_id and branch_id and group_name:
            students = (
                StudentProfile.objects.filter(
                    course_id=course_id,
                    branch_id=branch_id,
                    group_name=group_name,
                )
                .select_related("user")
                .order_by("user__first_name", "user__last_name", "id")
            )

        return JsonResponse(
            {
                "results": [
                    {
                        "id": student.pk,
                        "name": (
                            f"{student.user.full_name} · "
                            f"{student.total_score} score"
                        ),
                    }
                    for student in students
                ]
            }
        )

    def get_hero_months(self, request):
        student_id = request.GET.get("student_id")
        hero_id = request.GET.get("hero_id")

        # DIQQAT: ilgari bu yerda yil har doim JORIY yil edi, forma esa
        # variantlarni tahrirlanayotgan yozuvning yilidan qurardi. 2026-yilda
        # 2025-03-01 davriga ega heroni tahrirlaganda JS ro'yxatni yangilashi
        # bilan variantlar 2026 sanalariga aylanardi va saqlash yozuvni
        # jimgina bir yil oldinga surib yuborardi (dublikat tekshiruvi ham
        # yangi davrni ko'rgani uchun buni ushlamasdi).
        year = _requested_year(request, hero_id)
        used_months = set()

        if student_id:
            heroes = MonthHero.objects.filter(
                student_profile_id=student_id,
                period__year=year,
            )
            if hero_id:
                heroes = heroes.exclude(pk=hero_id)
            used_months = set(heroes.values_list("period__month", flat=True))

        results = [
            {
                "id": date(year, month_number, 1).isoformat(),
                "name": f"{month_name} {year}",
            }
            for month_number, month_name in enumerate(self.MONTH_NAMES, start=1)
            if month_number not in used_months
        ]
        return JsonResponse({"results": results})

    def _filter_url(
        self,
        period,
        course_id=None,
        branch_id=None,
    ):
        params = {"period__exact": period.isoformat()}

        if course_id:
            params["student_profile__course__id__exact"] = course_id
        if branch_id:
            params["student_profile__branch__id__exact"] = branch_id

        return f"{reverse('admin:app_monthhero_changelist')}?{urlencode(params)}"

    def changelist_view(self, request, extra_context=None):
        period_value = request.GET.get("period__exact")

        # Oldingi katalog URLlari ochilsa ham Django uni model filteri deb
        # qabul qilmasligi uchun custom parametrni olib tashlaymiz.
        if "view" in request.GET:
            request.GET = request.GET.copy()
            request.GET.pop("view")

        selected_period = None

        if period_value:
            try:
                selected_period = date.fromisoformat(period_value)
            except ValueError:
                return HttpResponseRedirect(reverse("admin:app_monthhero_changelist"))

            if selected_period.day != 1:
                return HttpResponseRedirect(reverse("admin:app_monthhero_changelist"))

        today = timezone.localdate()
        catalog_year = selected_period.year if selected_period else today.year
        totals = {
            item["period"].month: item["total"]
            for item in MonthHero.objects.filter(period__year=catalog_year)
            .values("period")
            .annotate(total=Count("id"))
        }
        months = []

        for month_number, month_name in enumerate(self.MONTH_NAMES, start=1):
            period = date(catalog_year, month_number, 1)
            months.append(
                {
                    "number": month_number,
                    "name": month_name,
                    "period": period,
                    "total": totals.get(month_number, 0),
                    "url": self._filter_url(period),
                }
            )

        selected_course_id = request.GET.get(
            "student_profile__course__id__exact"
        )
        selected_branch_id = request.GET.get(
            "student_profile__branch__id__exact"
        )
        course_totals = {}
        branch_totals = {}

        if selected_period:
            month_heroes = MonthHero.objects.filter(period=selected_period)
            course_totals = {
                item["student_profile__course_id"]: item["total"]
                for item in month_heroes.values(
                    "student_profile__course_id"
                ).annotate(total=Count("id"))
            }
            branch_totals = {
                item["student_profile__branch_id"]: item["total"]
                for item in month_heroes.values(
                    "student_profile__branch_id"
                ).annotate(total=Count("id"))
            }

        courses = (
            [
                {
                    "object": course,
                    "selected": str(course.pk) == selected_course_id,
                    "total": course_totals.get(course.pk, 0),
                    "url": self._filter_url(
                        selected_period,
                        course_id=course.pk,
                    ),
                }
                for course in Course.objects.filter(is_active=True).order_by(
                    "sort_order", "name", "id"
                )
            ]
            if selected_period
            else []
        )
        branches = (
            [
                {
                    "object": branch,
                    "selected": str(branch.pk) == selected_branch_id,
                    "total": branch_totals.get(branch.pk, 0),
                    "url": self._filter_url(
                        selected_period,
                        branch_id=branch.pk,
                    ),
                }
                for branch in Branch.objects.filter(is_active=True).order_by(
                    "name", "id"
                )
            ]
            if selected_period
            else []
        )

        catalog_context = {
            "hero_catalog_year": catalog_year,
            "hero_months": months,
            "selected_period": selected_period,
            "selected_month_name": (
                self.MONTH_NAMES[selected_period.month - 1]
                if selected_period
                else None
            ),
            "selected_month_total": (
                totals.get(selected_period.month, 0)
                if selected_period
                else 0
            ),
            "hero_courses": courses,
            "hero_branches": branches,
            "selected_course_id": selected_course_id,
            "selected_branch_id": selected_branch_id,
            "all_heroes_url": (
                self._filter_url(selected_period)
                if selected_period
                else ""
            ),
            "has_import_permission": self.has_import_permission(request),
            "has_export_permission": self.has_export_permission(request),
        }

        if extra_context:
            catalog_context.update(extra_context)

        return super().changelist_view(request, extra_context=catalog_context)

    def get_fields(self, request, obj=None):
        if obj is None:
            return (
                "course",
                "branch",
                "group_name",
                "student_profile",
                "period",
                "is_active",
            )

        return (
            "course",
            "branch",
            "group_name",
            "student_profile",
            "period",
            "is_active",
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