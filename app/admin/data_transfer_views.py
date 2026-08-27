"""Admin panel: butun database JSON export/import."""

from __future__ import annotations

import json
from datetime import datetime

from django.contrib import messages
from django.core import serializers
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from app.services.data_transfer import (
    default_manifest_name,
    export_combined,
    resolve_labels,
)


ALLOWED_PRESETS = ("essential", "with-users", "full")


def _require_staff(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponseForbidden("Faqat staff foydalanuvchi.")
    return None


@require_http_methods(["GET"])
def admin_db_export(request):
    denied = _require_staff(request)
    if denied:
        return denied

    preset = request.GET.get("preset", "full")
    if preset not in ALLOWED_PRESETS:
        preset = "full"

    labels = resolve_labels(preset=preset)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"pdp_junior_{preset}_{stamp}.json"

    # Vaqtinchalik fayl yozmasdan memoryda yig'amiz
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / default_manifest_name(preset)
        result = export_combined(labels, out, indent=2)
        content = Path(result["path"]).read_bytes()

    response = HttpResponse(content, content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["X-PDP-Export-Objects"] = str(result["total_objects"])
    return response


@require_http_methods(["GET", "POST"])
def admin_db_import(request):
    denied = _require_staff(request)
    if denied:
        return denied

    context = {
        "title": "Butun database import",
        "presets": ALLOWED_PRESETS,
        "site_header": "PDP Junior Admin",
        "has_permission": True,
    }

    if request.method == "GET":
        return render(request, "admin/db_import.html", context)

    upload = request.FILES.get("json_file")
    if not upload:
        messages.error(request, "JSON fayl tanlanmadi.")
        return redirect("admin:pdp_db_import")

    if not upload.name.lower().endswith(".json"):
        messages.error(request, "Faqat .json fayl qabul qilinadi.")
        return redirect("admin:pdp_db_import")

    try:
        raw = upload.read().decode("utf-8")
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        messages.error(request, f"JSON o‘qilmadi: {exc}")
        return redirect("admin:pdp_db_import")

    if not isinstance(payload, list):
        messages.error(
            request,
            "Noto‘g‘ri format. Django dumpdata ro‘yxati (list) kutilgan.",
        )
        return redirect("admin:pdp_db_import")

    created = 0
    updated = 0
    errors = []

    try:
        with transaction.atomic():
            for obj in serializers.deserialize("json", raw):
                try:
                    model = obj.object.__class__
                    pk = obj.object.pk
                    exists = (
                        model.objects.filter(pk=pk).exists()
                        if pk is not None
                        else False
                    )
                    obj.save()
                    if exists:
                        updated += 1
                    else:
                        created += 1
                except Exception as exc:  # noqa: BLE001
                    errors.append(
                        f"{obj.object.__class__.__name__} pk={obj.object.pk}: {exc}"
                    )
                    if len(errors) >= 15:
                        break
            if errors:
                raise ValueError("; ".join(errors[:5]))
    except Exception as exc:  # noqa: BLE001
        messages.error(request, f"Import xatosi (hech narsa saqlanmadi): {exc}")
        return redirect("admin:pdp_db_import")

    messages.success(
        request,
        f"Butun DB import yakunlandi: yaratildi={created}, yangilandi={updated}, "
        f"jami={created + updated}.",
    )
    return redirect("admin:index")
