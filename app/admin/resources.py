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


# ---------------------------------------------------------------------
# Resource'lar fabrikasi
#
# Ilgari bu yerda 20 dan ortiq bir xil klass bor edi — ular faqat `model`
# maydoni bilan farq qilardi va bazaviy klass allaqachon bergan
# sozlamalarni (`import_id_fields`, `skip_unchanged`, ...) qayta e'lon
# qilardi. Aynan shu bir xillik tufayli `StudentProfileResource` da
# `exclude` yo'qligi ko'zga tashlanmagan va `pdp_access_token` eksport
# faylida chiqib ketardi.
# ---------------------------------------------------------------------


def resource_for(model, *, exclude=None, name=None):
    """Berilgan model uchun standart import/export resource klassi."""
    meta_attrs = {
        "model": model,
        "import_id_fields": ("id",),
        "skip_unchanged": True,
        "report_skipped": True,
        "use_bulk": False,
    }
    if exclude:
        meta_attrs["exclude"] = tuple(exclude)

    return type(
        name or f"{model.__name__}Resource",
        (SafeDynamicModelResource,),
        {"Meta": type("Meta", (), meta_attrs)},
    )


UserResource = resource_for(User, exclude=("password", "groups", "user_permissions", "last_login",), name="UserResource")
StudentProfileResource = resource_for(StudentProfile, exclude=("pdp_access_token",), name="StudentProfileResource")
BranchResource = resource_for(Branch, name="BranchResource")
CoinProductResource = resource_for(CoinProduct, name="CoinProductResource")
MentorResource = resource_for(Mentor, name="MentorResource")
MonthHeroResource = resource_for(MonthHero, name="MonthHeroResource")
StudentPaymentHistoryResource = resource_for(StudentPaymentHistory, name="StudentPaymentHistoryResource")
StudentInvoiceResource = resource_for(StudentInvoice, name="StudentInvoiceResource")
PortfolioResource = resource_for(Portfolio, name="PortfolioResource")
CourseResource = resource_for(Course, name="CourseResource")
ModuleResource = resource_for(Module, name="ModuleResource")
LessonResource = resource_for(Lesson, name="LessonResource")
TestSessionResource = resource_for(TestSession, name="TestSessionResource")
TestSessionQuestionResource = resource_for(TestSessionQuestion, name="TestSessionQuestionResource")
TestSessionAnswerResource = resource_for(TestSessionAnswer, name="TestSessionAnswerResource")
StudentQuestionRewardResource = resource_for(StudentQuestionReward, name="StudentQuestionRewardResource")
GalleryPostResource = resource_for(GalleryPost, name="GalleryPostResource")
StudentMarkResource = resource_for(StudentMark, name="StudentMarkResource")
CoinOrderResource = resource_for(CoinOrder, name="CoinOrderResource")


# QuestionResource fabrikaga to'g'ri kelmaydi: unda i18n JSON maydonlari
# va FK widget'lari uchun aniq ta'riflar kerak.
class QuestionResource(SafeDynamicModelResource):
    lesson = Field(
        column_name="lesson",
        attribute="lesson",
        widget=ForeignKeyWidget(Lesson, "id"),
    )
    text = Field(column_name="text", attribute="text", widget=JSONWidget())
    images = Field(column_name="images", attribute="images", widget=JSONWidget())
    options = Field(column_name="options", attribute="options", widget=JSONWidget())

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
        export_order = fields
        import_id_fields = ("id",)
        skip_unchanged = True
        report_skipped = True
        use_bulk = False
