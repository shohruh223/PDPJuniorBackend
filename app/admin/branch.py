from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from app.admin.mixins import RowActionsAdminMixin
from app.admin.resources import BranchResource, PrettyImportExportModelAdmin
from app.admin.media import MultipleFileField, save_uploaded_file
from app.models.branch import Branch
from app.serializers.media import build_file_url


class BranchAdminForm(forms.ModelForm):
    cover_image = forms.ImageField(
        label="Asosiy rasm (cover)",
        required=False,
        help_text="Yuklanganda Cloudflare R2 ga saqlanadi. API dagi image maydoni shu URL bo‘ladi.",
    )
    album_images = MultipleFileField(
        label="Album rasmlari",
        required=False,
        help_text="Bir nechta rasm yuklash mumkin (R2).",
    )

    video_links = forms.CharField(
        label="Video linklar",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Har bir video linkni yangi qatordan kiriting",
            }
        ),
        help_text="Har bir video linkni alohida qatordan kiriting.",
    )

    class Meta:
        model = Branch
        fields = (
            "name",
            "address",
            "phone",
            "map_url",
            "image_url",
            "is_opened",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image_url"].label = "Joriy image URL / path"
        self.fields["image_url"].required = False
        self.fields["image_url"].help_text = (
            "Qo‘lda URL yoki path. Cover yuklasangiz avtomatik yangilanadi."
        )
        if self.instance and self.instance.pk and self.instance.image_url:
            self.fields["cover_image"].help_text = (
                f"Hozirgi: {build_file_url(self.instance.image_url) or self.instance.image_url}"
            )

    def clean_video_links(self):
        value = self.cleaned_data.get("video_links") or ""

        links = [
            link.strip()
            for link in value.splitlines()
            if link.strip()
        ]

        for link in links:
            if not link.startswith(("http://", "https://")):
                raise ValidationError(
                    "Video link http:// yoki https:// bilan boshlanishi kerak."
                )

        return links

    def save(self, commit=True):
        obj = super().save(commit=False)

        cover = self.cleaned_data.get("cover_image")
        if cover:
            obj.image_url = save_uploaded_file(cover, "branches/cover")

        album = obj.album if isinstance(obj.album, list) else []

        uploaded_images = self.cleaned_data.get("album_images") or []
        video_links = self.cleaned_data.get("video_links") or []

        for uploaded in uploaded_images:
            saved_path = save_uploaded_file(uploaded, "branches/album")
            album.append(
                {
                    "type": "image",
                    "url": saved_path,
                }
            )

        for video_link in video_links:
            album.append(
                {
                    "type": "video",
                    "url": video_link,
                }
            )

        obj.album = album

        if commit:
            obj.save()

        return obj


@admin.register(Branch)
class BranchAdmin(RowActionsAdminMixin, PrettyImportExportModelAdmin):
    resource_class = BranchResource
    form = BranchAdminForm

    fields = (
        "name",
        "address",
        "phone",
        "map_url",
        "cover_image",
        "image_url",
        "is_opened",
        "is_active",
        "album_images",
        "video_links",
    )

    list_display = (
        "id",
        "name",
        "phone",
        "is_opened",
        "is_active",
        "row_actions",
    )
    list_filter = (
        "is_opened",
        "is_active",
    )
    search_fields = (
        "name",
        "address",
        "phone",
    )
    ordering = ("id",)
