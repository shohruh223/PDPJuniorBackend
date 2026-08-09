from django import forms
from django.contrib import admin
from app.admin.media import save_uploaded_file
from app.admin.mixins import RowActionsAdminMixin
from app.admin.resources import PrettyImportExportModelAdmin, PortfolioResource
from app.models.portfolio import Portfolio


class PortfolioAdminForm(forms.ModelForm):
    image_file = forms.ImageField(
        label="Portfolio rasmi",
        required=False,
    )

    class Meta:
        model = Portfolio
        fields = (
            "name",
            "url",
            "desc",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        current_image = {}

        if self.instance and isinstance(self.instance.image, dict):
            current_image = self.instance.image

        self.fields["image_file"].help_text = current_image.get("url", "")

    def save(self, commit=True):
        obj = super().save(commit=False)

        uploaded = self.cleaned_data.get("image_file")

        if uploaded:
            saved_path = save_uploaded_file(uploaded, "portfolios")
            obj.image = {
                "url": saved_path,
            }

        if commit:
            obj.save()

        return obj


@admin.register(Portfolio)
class PortfolioAdmin(RowActionsAdminMixin, PrettyImportExportModelAdmin):
    resource_class = PortfolioResource
    form = PortfolioAdminForm

    fields = (
        "name",
        "url",
        "desc",
        "is_active",
        "image_file",
    )

    list_display = (
        "id",
        "name",
        "url",
        "desc",
        "is_active",
        "row_actions",
    )
    list_filter = ("is_active",)
    search_fields = (
        "name",
        "url",
        "desc",
    )
    ordering = ("id",)