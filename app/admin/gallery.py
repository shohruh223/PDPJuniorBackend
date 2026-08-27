from django import forms
from django.contrib import admin
from django.utils import timezone

from app.admin.media import MultipleFileField, save_uploaded_file
from app.admin.mixins import RowActionsAdminMixin
from app.admin.resources import GalleryPostResource, PrettyImportExportModelAdmin
from app.models.gallery import GalleryPost


def _lang_text(value, lang):
    if isinstance(value, dict):
        return (value.get(lang) or "").strip()
    if isinstance(value, str) and lang == "uz":
        return value.strip()
    return ""


def _i18n(uz):
    """Hozircha bitta matn; ru/en keyinchalik alohida to‘ldiriladi."""
    text = (uz or "").strip()
    return {"uz": text, "ru": text, "en": text}


def _media_src(item):
    if isinstance(item, dict):
        return (item.get("src") or "").strip()
    return ""


class GalleryPostAdminForm(forms.ModelForm):
    title_uz = forms.CharField(
        label="Sarlavha",
        max_length=255,
        help_text="Post sarlavhasi. Kategoriya sifatida ham ishlatiladi.",
    )
    description_uz = forms.CharField(
        label="Tavsif",
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    cover_file = forms.ImageField(
        label="Asosiy rasm",
        required=False,
        help_text="Kompyuterdan rasm yuklang.",
    )
    extra_files = MultipleFileField(
        label="Qo‘shimcha rasmlar",
        required=False,
        help_text="Bir nechta rasmni birga tanlash mumkin.",
    )

    class Meta:
        model = GalleryPost
        fields = ("is_active",)
        labels = {
            "is_active": "Faol",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        title = getattr(instance, "title", None) or {}
        category = getattr(instance, "category", None) or {}
        description = getattr(instance, "description", None) or {}

        self.fields["title_uz"].initial = (
            _lang_text(title, "uz") or _lang_text(category, "uz")
        )
        self.fields["description_uz"].initial = _lang_text(description, "uz")

        cover = (getattr(instance, "cover_image", None) or "").strip()
        media = getattr(instance, "media", None) or []
        if not cover and media:
            cover = _media_src(media[0])

        extra_count = 0
        for item in media:
            src = _media_src(item)
            if src and src != cover:
                extra_count += 1

        if instance.pk:
            self.fields["cover_file"].required = not bool(cover)
            if cover:
                self.fields["cover_file"].help_text = (
                    "Yangi rasm yuklansa, hozirgisi almashtiriladi."
                )
            if extra_count:
                self.fields["extra_files"].help_text = (
                    f"Hozir {extra_count} ta qo‘shimcha rasm bor. "
                    "Yangi yuklanganlar ularga qo‘shiladi."
                )
        else:
            self.fields["cover_file"].required = True

    def clean(self):
        cleaned = super().clean()
        cover = (getattr(self.instance, "cover_image", None) or "").strip()
        if not self.instance.pk and not cleaned.get("cover_file") and not cover:
            self.add_error("cover_file", "Asosiy rasm yuklash shart.")
        if self.instance.pk and not cleaned.get("cover_file") and not cover:
            media = getattr(self.instance, "media", None) or []
            if not any(_media_src(item) for item in media):
                self.add_error("cover_file", "Asosiy rasm yuklash shart.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)

        title = _i18n(self.cleaned_data.get("title_uz"))
        obj.title = title
        obj.category = title
        obj.description = _i18n(self.cleaned_data.get("description_uz"))

        old_cover = (obj.cover_image or "").strip()
        cover = old_cover
        uploaded_cover = self.cleaned_data.get("cover_file")
        if uploaded_cover:
            cover = save_uploaded_file(uploaded_cover, "gallery")
        elif not cover:
            media = getattr(obj, "media", None) or []
            cover = _media_src(media[0]) if media else ""

        extra_urls = []
        for item in getattr(obj, "media", None) or []:
            src = _media_src(item)
            if src and src != cover and src != old_cover:
                extra_urls.append(src)

        for uploaded in self.cleaned_data.get("extra_files") or []:
            extra_urls.append(save_uploaded_file(uploaded, "gallery"))

        obj.cover_image = cover
        obj.cover_contain = False
        obj.cover_bg = ""
        if not obj.icon:
            obj.icon = "📰"
        if not obj.date:
            obj.date = timezone.localtime(timezone.now()).strftime("%d.%m.%Y")

        media = []
        if cover:
            media.append({"type": "image", "src": cover, "contain": False, "bg": ""})
        for src in extra_urls:
            if src == cover:
                continue
            media.append({"type": "image", "src": src, "contain": False, "bg": ""})
        obj.media = media

        if commit:
            obj.save()
        return obj


@admin.register(GalleryPost)
class GalleryPostAdmin(PrettyImportExportModelAdmin):
    resource_class = GalleryPostResource
    form = GalleryPostAdminForm
    list_display = (
        "title_preview",
        "date",
        "views_count",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("date", "title", "description")
    ordering = ("sort_order", "-created_at")
    fields = (
        "title_uz",
        "description_uz",
        "cover_file",
        "extra_files",
        "is_active",
    )

    @admin.display(description="Sarlavha")
    def title_preview(self, obj):
        title = obj.title or {}
        if isinstance(title, dict):
            return title.get("uz") or title.get("en") or str(obj.id)
        return title or str(obj.id)
