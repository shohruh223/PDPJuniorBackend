from django.contrib import admin

from app.admin.resources import (
    PrettyImportExportModelAdmin,
    StudentQuestionRewardResource,
    TestSessionAnswerResource,
    TestSessionQuestionResource,
    TestSessionResource,
)
from app.models.test import (
    StudentQuestionReward,
    TestSession,
    TestSessionAnswer,
    TestSessionQuestion,
)


class TestSessionQuestionInline(admin.TabularInline):
    model = TestSessionQuestion
    extra = 0
    autocomplete_fields = ("question",)
    fields = ("order", "question")
    ordering = ("order",)


class TestSessionAnswerInline(admin.TabularInline):
    model = TestSessionAnswer
    extra = 0
    autocomplete_fields = ("question",)
    fields = ("question", "selected_option", "is_correct")


@admin.register(TestSession)
class TestSessionAdmin(PrettyImportExportModelAdmin):
    resource_class = TestSessionResource
    list_display = (
        "session_id",
        "student",
        "lesson",
        "total_questions",
        "duration_minutes",
        "is_finished",
        "started_at",
    )
    list_filter = (
        "is_finished",
        "started_at",
        "lesson__course",
        "lesson__module",
    )
    search_fields = (
        "session_id",
        "student__phone_number",
        "student__first_name",
        "student__last_name",
        "lesson__name",
    )
    autocomplete_fields = ("student", "lesson")
    readonly_fields = ("session_id", "started_at")
    ordering = ("-started_at",)
    date_hierarchy = "started_at"
    inlines = (TestSessionQuestionInline, TestSessionAnswerInline)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "student",
            "lesson",
            "lesson__course",
            "lesson__module",
        )


@admin.register(TestSessionQuestion)
class TestSessionQuestionAdmin(PrettyImportExportModelAdmin):
    list_select_related = ("session", "question", "question__lesson")
    resource_class = TestSessionQuestionResource
    list_display = ("id", "session", "order", "question")
    list_filter = ("session__is_finished", "session__lesson__course")
    search_fields = (
        "session__session_id",
        "session__student__phone_number",
        "question__text__uz",
    )
    autocomplete_fields = ("session", "question")
    ordering = ("session", "order")


@admin.register(TestSessionAnswer)
class TestSessionAnswerAdmin(PrettyImportExportModelAdmin):
    list_select_related = ("session", "question", "question__lesson")
    resource_class = TestSessionAnswerResource
    list_display = (
        "id",
        "session",
        "question",
        "selected_option",
        "is_correct",
    )
    list_filter = (
        "is_correct",
        "selected_option",
        "session__is_finished",
        "session__lesson__course",
    )
    search_fields = (
        "session__session_id",
        "session__student__phone_number",
        "question__text__uz",
    )


@admin.register(StudentQuestionReward)
class StudentQuestionRewardAdmin(PrettyImportExportModelAdmin):
    resource_class = StudentQuestionRewardResource
    list_display = ("student", "question", "session", "awarded_at")
    search_fields = (
        "student__phone_number",
        "student__first_name",
        "student__last_name",
    )
    autocomplete_fields = ("student", "question", "session")
    list_select_related = ("student", "question", "session")