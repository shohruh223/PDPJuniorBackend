from django.contrib import admin
from django.contrib.admin.utils import quote
from django.urls import reverse
from django.utils.html import format_html


class RowActionsAdminMixin:
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
            "</svg><span>Update</span></a>"
            '<a class="pdp-row-action pdp-row-action--delete" href="{}" '
            'title="O‘chirish" aria-label="O‘chirish">'
            '<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M3 6h18M8 6V4h8v2M19 6l-1 15H6L5 6M10 11v6M14 11v6"/>'
            "</svg><span>Delete</span></a>"
            "</span>",
            change_url,
            delete_url,
        )
