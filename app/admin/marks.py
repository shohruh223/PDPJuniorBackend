from django.contrib import admin

from app.models import StudentMark


@admin.register(StudentMark)
class StudentMarkAdmin(admin.ModelAdmin):
    list_display = (
        "student_profile",
        "course",
        "lesson",
        "record_date",
        "attendance",
        "grade",
        "verified",
    )
    list_filter = ("course", "attendance", "verified", "record_date")
    search_fields = (
        "student_profile__user__first_name",
        "student_profile__user__last_name",
        "student_profile__user__phone_number",
        "student_profile__group_name",
        "course__name",
        "lesson__name",
    )
    autocomplete_fields = ("student_profile", "course", "lesson")
    date_hierarchy = "record_date"
    ordering = ("-record_date", "student_profile__user__first_name")
    list_select_related = ("student_profile__user", "course", "lesson")
