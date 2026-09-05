from django.contrib import admin
from django.contrib.admin.utils import quote
from django.contrib.admin.views.main import ChangeList
from django.urls import reverse
from django.utils.html import format_html


class NoFilterSidebarChangeList(ChangeList):
    """URL orqali filterlashni saqlab, o‘ng FILTER panelini chiqarmaydi."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_popup:
            self.title = f"{self.opts.verbose_name} tanlang"
        else:
            self.title = str(self.opts.verbose_name_plural)

    def get_filters(self, request):
        filter_specs, _has_filters, lookup_params, may_have_duplicates, has_active_filters = (
            super().get_filters(request)
        )
        return filter_specs, False, lookup_params, may_have_duplicates, has_active_filters


class HideChangelistFilterMixin:
    """Django changelist o‘ng tomonidagi FILTER sidebarini yashiradi."""

    actions = None

    @admin.display(description="ID")
    def id_short(self, obj):
        """UUID'ning qisqartirilgan ko‘rinishi.

        Modellarning kaliti — 36 belgili UUID. U jadvalning BIRINCHI
        ustuni bo‘lganida to‘rt qatorga bo‘linib ketardi va aynan o‘sha
        o‘qib bo‘lmaydigan matn qatorning yagona havolasi edi. Endi
        birinchi ustun — odam o‘qiy oladigan nom, UUID esa oxirida
        qisqargan holda turadi; to‘liq qiymati `title` da, ya‘ni sichqoncha
        ustiga olib borilsa ko‘rinadi va nusxa olish uchun ochib bo‘ladi.
        """
        value = str(getattr(obj, "pk", "") or "")
        if not value:
            return "—"
        return format_html(
            '<span class="pdp-id-chip" title="{}">{}</span>', value, value[:8]
        )

    def get_changelist(self, request, **kwargs):
        return NoFilterSidebarChangeList

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        name = self.model._meta.verbose_name
        extra_context.setdefault(
            "title",
            f"{name} qo‘shish" if object_id is None else f"{name}ni tahrirlash",
        )
        return super().changeform_view(request, object_id, form_url, extra_context)

    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        extra_context.setdefault(
            "title",
            f"{self.model._meta.verbose_name}ni o‘chirish",
        )
        return super().delete_view(request, object_id, extra_context)


class RowActionsAdminMixin(HideChangelistFilterMixin):
    """Changelist jadvalida aniq update va delete tugmalarini ko‘rsatadi."""

    def get_list_display(self, request):
        list_display = tuple(super().get_list_display(request))
        if "row_actions" not in list_display:
            list_display += ("row_actions",)
        return list_display

    @admin.display(description="Amallar")
    def row_actions(self, obj):
        opts = obj._meta
        object_id = quote(obj.pk)
        change_url = reverse(
            f"admin:{opts.app_label}_{opts.model_name}_change",
            args=(object_id,),
        )
        delete_url = reverse(
            f"admin:{opts.app_label}_{opts.model_name}_delete",
            args=(object_id,),
        )

        return format_html(
            '<span class="pdp-row-actions">'
            '<a class="pdp-row-action pdp-row-action--edit" href="{}" '
            'title="Tahrirlash" aria-label="Tahrirlash">'
            '<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"/>'
            "</svg><span>Tahrirlash</span></a>"
            '<a class="pdp-row-action pdp-row-action--delete" href="{}" '
            'title="O‘chirish" aria-label="O‘chirish">'
            '<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M3 6h18M8 6V4h8v2M19 6l-1 15H6L5 6M10 11v6M14 11v6"/>'
            "</svg><span>O‘chirish</span></a>"
            "</span>",
            change_url,
            delete_url,
        )
