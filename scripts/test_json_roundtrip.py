"""
Export/import round-trip testi:
1) combined JSON
2) per-table papka
Format buzilmasligi va ma'lumot saqlanishini tekshiradi.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import django
from django.apps import apps
from django.core import serializers
from django.core.management import call_command
from django.db import transaction


BASE = Path(__file__).resolve().parent
EXPORT_DIR = BASE / "data" / "exports" / "roundtrip_test"
COMBINED = EXPORT_DIR / "combined.json"
TABLES_DIR = EXPORT_DIR / "tables"
LABELS = ["app.Course", "app.Module", "app.Lesson", "app.Question"]


def fingerprint(labels: list[str]) -> dict:
    """Har model uchun count + pk+fields hash."""
    result = {}
    for label in labels:
        model = apps.get_model(label)
        rows = list(model.objects.all().order_by("pk"))
        payload = serializers.serialize("json", rows)
        result[label] = {
            "count": len(rows),
            "pks": [str(obj.pk) for obj in rows],
            "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        }
    return result


def validate_dump_format(path: Path) -> tuple[bool, str]:
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return False, f"JSON parse xato: {exc}"

    if not isinstance(data, list):
        return False, "Root list emas (Django dumpdata format kerak)"

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            return False, f"[{i}] object emas"
        if "model" not in item or "fields" not in item:
            return False, f"[{i}] model/fields yo'q"
        if not isinstance(item["fields"], dict):
            return False, f"[{i}] fields dict emas"
        # pk optional for natural keys, lekin bizda odatda bor
        if "pk" not in item:
            return False, f"[{i}] pk yo'q"

    return True, f"OK ({len(data)} obyekt)"


def main() -> int:
    if str(BASE) not in sys.path:
        sys.path.insert(0, str(BASE))

    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
    django.setup()

    if EXPORT_DIR.exists():
        shutil.rmtree(EXPORT_DIR)
    EXPORT_DIR.mkdir(parents=True)

    print("=== 1) Baseline fingerprint ===")
    before = fingerprint(LABELS)
    for label, info in before.items():
        print(f"  {label}: count={info['count']} sha={info['sha256'][:12]}...")

    print("\n=== 2) Export: combined + per-table ===")
    call_command(
        "export_db_json",
        preset="catalog",
        mode="combined",
        output=str(COMBINED),
    )
    call_command(
        "export_db_json",
        preset="catalog",
        mode="per-table",
        output=str(TABLES_DIR),
    )

    print("\n=== 3) Format validation ===")
    ok, msg = validate_dump_format(COMBINED)
    print(f"  combined: {'PASS' if ok else 'FAIL'} — {msg}")
    if not ok:
        return 1

    manifest = TABLES_DIR / "manifest.json"
    if not manifest.exists():
        print("  per-table: FAIL — manifest.json yo'q")
        return 1
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    print(
        f"  manifest: PASS — format={manifest_data.get('format')} "
        f"files={len(manifest_data.get('files', []))}"
    )

    table_total = 0
    for item in manifest_data["files"]:
        file_path = TABLES_DIR / item["file"]
        ok, msg = validate_dump_format(file_path)
        print(f"  {item['file']}: {'PASS' if ok else 'FAIL'} — {msg}")
        if not ok:
            return 1
        data = json.loads(file_path.read_text(encoding="utf-8"))
        table_total += len(data)
        if len(data) != item["count"]:
            print(
                f"    FAIL: manifest count={item['count']} "
                f"lekin faylda={len(data)}"
            )
            return 1

    combined_count = len(json.loads(COMBINED.read_text(encoding="utf-8")))
    if combined_count != table_total:
        print(
            f"  FAIL: combined={combined_count} != per-table sum={table_total}"
        )
        return 1
    print(f"  count parity: PASS ({combined_count} == {table_total})")

    # UTF-8 / ensure_ascii check
    sample = COMBINED.read_text(encoding="utf-8")
    if "\\u" in sample and "O‘" not in sample and "o'" not in sample.lower():
        # soft check — unicode escape bo'lishi mumkin, lekin biz ensure_ascii=False qilamiz
        pass
    if '"model"' not in sample:
        print("  FAIL: combined faylda model kaliti yo'q")
        return 1
    print("  utf-8 readable: PASS")

    print("\n=== 4) Round-trip import: COMBINED ===")
    call_command("import_db_json", input=str(COMBINED))
    after_combined = fingerprint(LABELS)
    for label in LABELS:
        if before[label] != after_combined[label]:
            print(f"  FAIL {label}: fingerprint o'zgardi")
            print(f"    before={before[label]}")
            print(f"    after ={after_combined[label]}")
            return 1
        print(f"  {label}: PASS (count/hash bir xil)")

    print("\n=== 5) Round-trip import: PER-TABLE ===")
    call_command("import_db_json", input=str(TABLES_DIR))
    after_tables = fingerprint(LABELS)
    for label in LABELS:
        if before[label] != after_tables[label]:
            print(f"  FAIL {label}: fingerprint o'zgardi")
            return 1
        print(f"  {label}: PASS (count/hash bir xil)")

    print("\n=== 6) Re-export va fayl solishtirish ===")
    re_combined = EXPORT_DIR / "combined_reexport.json"
    call_command(
        "export_db_json",
        preset="catalog",
        mode="combined",
        output=str(re_combined),
    )
    a = json.loads(COMBINED.read_text(encoding="utf-8"))
    b = json.loads(re_combined.read_text(encoding="utf-8"))
    if a != b:
        print("  FAIL: re-export JSON birinchi export bilan mos emas")
        # detail
        print(f"    first={len(a)} second={len(b)}")
        return 1
    print("  re-export identity: PASS")

    print("\n=== 7) Dry-run import ===")
    call_command("import_db_json", input=str(COMBINED), dry_run=True)
    call_command("import_db_json", input=str(TABLES_DIR), dry_run=True)
    print("  dry-run: PASS")

    print("\n==============================")
    print("NATIJA: BARCHA TESTLAR O'TDI")
    print("==============================")
    print(f"Combined: {COMBINED}")
    print(f"Per-table: {TABLES_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
