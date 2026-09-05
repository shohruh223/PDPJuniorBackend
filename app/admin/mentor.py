from django import forms
from django.contrib import admin
from app.admin.media import save_uploaded_file
from app.admin.mixins import RowActionsAdminMixin
from app.admin.resources import PrettyImportExportModelAdmin, MentorResource
from app.models import Mentor


class MentorAdminForm(forms.ModelForm):
    avatar_file = forms.ImageField(
        label="Mentor rasmi",
        required=False,
    )

    class Meta:
        model = Mentor
        fields = (
            "name",
            "role",
            "branch",
            "exp",
            "students_count",
            "working_period_start",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        current_avatar = {}
        if self.instance and isinstance(self.instance.avatar, dict):
            current_avatar = self.instance.avatar

        self.fields["avatar_file"].help_text = current_avatar.get("url", "")

    def save(self, commit=True):
        obj = super().save(commit=False)

        uploaded = self.cleaned_data.get("avatar_file")
        if uploaded:
            saved_path = save_uploaded_file(uploaded, "mentors")
            obj.avatar = {
                "url": saved_path,
            }

        if commit:
            obj.save()

        return obj


@admin.register(Mentor)
class MentorAdmin(RowActionsAdminMixin, PrettyImportExportModelAdmin):
    list_select_related = ("branch",)
    resource_class = MentorResource
    form = MentorAdminForm

    fields = (
        "name",
        "role",
        "branch",
        "exp",
        "students_count",
        "working_period_start",
        "is_active",
        "avatar_file",
    )

    list_display = (
        "id",
        "name",
        "role",
        "branch",
        "exp",
        "students_count",
        "is_active",
        "row_actions",
    )
    list_filter = (
        "role",
        "branch",
        "is_active",
    )
    search_fields = (
        "name",
        "role",
        "branch__name",
    )
    ordering = ("id",)
