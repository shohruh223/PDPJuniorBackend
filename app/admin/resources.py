import json

from django.db import models
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.fields import Field
from import_export.formats import base_formats
from import_export.widgets import ForeignKeyWidget, Widget

from app.admin.mixins import HideChangelistFilterMixin, RowActionsAdminMixin
from app.models.auth import User, StudentProfile
from app.models.branch import Branch
from app.models.coin import CoinOrder, CoinProduct
from app.models.gallery import GalleryPost
from app.models.marks import StudentMark
from app.models.mentors import Mentor
from app.models.month_hero import MonthHero
from app.models.payment import StudentInvoice, StudentPaymentHistory
from app.models.portfolio import Portfolio
from app.models.question import Course, Module, Lesson, Question
from app.models.test import (
    StudentQuestionReward,
    TestSession,
    TestSessionAnswer,
    TestSessionQuestion,
)


class JSONWidget(Widget):
    """
    JSONFieldlarni to'g'ri import/export qilish uchun.

    Exportda:
        "[{\"type\": \"image\"}]"
    emas, balki:
        [{"type": "image"}]
    ko'rinishida chiqaradi.

    Importda esa JSON string yoki real dict/list bo'lsa ham qabul qiladi.
    """

    def clean(self, value, row=None, **kwargs):
        if value in ("", None):
            return None

        if isinstance(value, (dict, list)):
            return value

        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return value

    def render(self, value, obj=None, **kwargs):
        if value in ("", None):
            return None

        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

        return value


class PrettyJSON(base_formats.JSON):
    """
    Django import-export JSON exportini o'qishga qulay formatda chiqaradi.
    """

    def export_data(self, dataset, **kwargs):
        return json.dumps(
            dataset.dict,
            ensure_ascii=False,
            indent=2,
            default=str,
        )


class PrettyImportExportModelAdmin(HideChangelistFilterMixin, ImportExportModelAdmin):
    """
    Admin panelda faqat JSON import/export ishlatish uchun custom admin.
    """

    formats = [
        PrettyJSON,
    ]

    row_actions = RowActionsAdminMixin.row_actions

    def get_list_display(self, request):
        list_display = tuple(super().get_list_display(request))
        if "row_actions" not in list_display:
            list_display += ("row_actions",)
        return list_display


class DynamicModelResource(resources.ModelResource):
    """
    Har bir model fieldlarini avtomatik import/export qiladi.

    - JSONField -> JSONWidget
    - ForeignKey / OneToOne -> id orqali
    - ManyToMany -> avtomatik kiritilmaydi
    """

    @classmethod
    def field_from_django_field(cls, field_name, django_field, readonly):
        if isinstance(django_field, models.JSONField):
            return Field(
                attribute=field_name,
                column_name=field_name,
                widget=JSONWidget(),
                readonly=readonly,
            )

        if isinstance(django_field, (models.ForeignKey, models.OneToOneField)):
            return Field(
                attribute=field_name,
                column_name=field_name,
                widget=ForeignKeyWidget(django_field.remote_field.model, "id"),
                readonly=readonly,
            )

        return super().field_from_django_field(field_name, django_field, readonly)


class SafeDynamicModelResource(DynamicModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class UserResource(SafeDynamicModelResource):
    class Meta:
        model = User
        import_id_fields = ("id",)
        exclude = (
            "password",
            "groups",
            "user_permissions",
            "last_login",
        )
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class StudentProfileResource(SafeDynamicModelResource):
    class Meta:
        model = StudentProfile
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class BranchResource(SafeDynamicModelResource):
    class Meta:
        model = Branch
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class CoinProductResource(SafeDynamicModelResource):
    class Meta:
        model = CoinProduct
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class MentorResource(SafeDynamicModelResource):
    class Meta:
        model = Mentor
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class MonthHeroResource(SafeDynamicModelResource):
    class Meta:
        model = MonthHero
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class StudentPaymentHistoryResource(SafeDynamicModelResource):
    class Meta:
        model = StudentPaymentHistory
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class StudentInvoiceResource(SafeDynamicModelResource):
    class Meta:
        model = StudentInvoice
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class PortfolioResource(SafeDynamicModelResource):
    class Meta:
        model = Portfolio
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class CourseResource(SafeDynamicModelResource):
    class Meta:
        model = Course
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class ModuleResource(SafeDynamicModelResource):
    class Meta:
        model = Module
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class LessonResource(SafeDynamicModelResource):
    class Meta:
        model = Lesson
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class QuestionResource(SafeDynamicModelResource):
    lesson = Field(
        column_name="lesson",
        attribute="lesson",
        widget=ForeignKeyWidget(Lesson, "id"),
    )

    text = Field(
        column_name="text",
        attribute="text",
        widget=JSONWidget(),
    )

    images = Field(
        column_name="images",
        attribute="images",
        widget=JSONWidget(),
    )

    options = Field(
        column_name="options",
        attribute="options",
        widget=JSONWidget(),
    )

    class Meta:
        model = Question
        fields = (
            "id",
            "lesson",
            "text",
            "images",
            "options",
            "correct_option",
            "created_at",
        )
        export_order = (
            "id",
            "lesson",
            "text",
            "images",
            "options",
            "correct_option",
            "created_at",
        )
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class TestSessionResource(SafeDynamicModelResource):
    class Meta:
        model = TestSession
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class TestSessionQuestionResource(SafeDynamicModelResource):
    class Meta:
        model = TestSessionQuestion
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class TestSessionAnswerResource(SafeDynamicModelResource):
    class Meta:
        model = TestSessionAnswer
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class StudentQuestionRewardResource(SafeDynamicModelResource):
    class Meta:
        model = StudentQuestionReward
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class GalleryPostResource(SafeDynamicModelResource):
    class Meta:
        model = GalleryPost
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class StudentMarkResource(SafeDynamicModelResource):
    class Meta:
        model = StudentMark
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False


class CoinOrderResource(SafeDynamicModelResource):
    class Meta:
        model = CoinOrder
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False