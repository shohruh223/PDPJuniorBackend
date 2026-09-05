"""
Export/import round-trip: combined va per-table format buzilmasligini tekshiradi.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from django.apps import apps
from django.core import serializers
from django.core.management import BaseCommand, CommandError, call_command
from django.conf import settings


class Command(BaseCommand):
    help = "JSON export/import round-trip test (combined + per-table)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Tasdiqlash: bu buyruq JONLI bazaga yozadi!",
        )
        parser.add_argument(
            "--preset",
            default="catalog",
            help="Test uchun preset (default: catalog)",
        )

    def handle(self, *args, **options):
        # DIQQAT: nomida "test" bo'lsa-da, bu management buyrug'i —
        # u alohida test bazasida emas, DATABASES["default"] ustida
        # ishlaydi va export bilan import orasida qilingan o'zgarishlarni
        # jimgina orqaga qaytarishi mumkin.
        from django.conf import settings as dj_settings

        if not dj_settings.DEBUG and not options.get("yes"):
            raise CommandError(
                "Bu buyruq JONLI bazaga yozadi. Davom etish uchun --yes bering."
            )
        preset = options["preset"]
        export_dir = Path(settings.BASE_DIR) / "data" / "exports" / "roundtrip_test"
        combined = export_dir / "combined.json"
        tables_dir = export_dir / "tables"

        from app.services.data_transfer import resolve_labels

        labels = resolve_labels(preset=preset)

        if export_dir.exists():
            shutil.rmtree(export_dir)
        export_dir.mkdir(parents=True)

        before = self._fingerprint(labels)
        self.stdout.write(self.style.NOTICE(f"Preset={preset}, models={len(labels)}"))

        call_command("export_db_json", preset=preset, mode="combined", output=str(combined))
        call_command("export_db_json", preset=preset, mode="per-table", output=str(tables_dir))

        ok, msg = self._validate_dump(combined)
        if not ok:
            raise CommandError(f"combined format FAIL: {msg}")
        self.stdout.write(self.style.SUCCESS(f"combined format: {msg}"))

        manifest_path = tables_dir / "manifest.json"
        if not manifest_path.exists():
            raise CommandError("per-table manifest.json yo'q")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        total = 0
        for item in manifest["files"]:
            path = tables_dir / item["file"]
            ok, msg = self._validate_dump(path)
            if not ok:
                raise CommandError(f"{item['file']} FAIL: {msg}")
            count = len(json.loads(path.read_text(encoding="utf-8")))
            if count != item["count"]:
                raise CommandError(
                    f"{item['file']}: manifest={item['count']} fayl={count}"
                )
            total += count
            self.stdout.write(self.style.SUCCESS(f"{item['file']}: {msg}"))

        combined_count = len(json.loads(combined.read_text(encoding="utf-8")))
        if combined_count != total:
            raise CommandError(
                f"count parity FAIL: combined={combined_count} tables={total}"
            )
        self.stdout.write(self.style.SUCCESS(f"count parity: {combined_count}"))

        call_command("import_db_json", input=str(combined))
        after_combined = self._fingerprint(labels)
        self._assert_same(before, after_combined, "combined import")

        call_command("import_db_json", input=str(tables_dir))
        after_tables = self._fingerprint(labels)
        self._assert_same(before, after_tables, "per-table import")

        re_combined = export_dir / "combined_reexport.json"
        call_command(
            "export_db_json",
            preset=preset,
            mode="combined",
            output=str(re_combined),
        )
        a = json.loads(combined.read_text(encoding="utf-8"))
        b = json.loads(re_combined.read_text(encoding="utf-8"))
        if a != b:
            raise CommandError("re-export JSON birinchi export bilan mos emas")
        self.stdout.write(self.style.SUCCESS("re-export identity: PASS"))

        self.stdout.write(self.style.SUCCESS("BARCHA TESTLAR O'TDI"))

    def _fingerprint(self, labels):
        result = {}
        for label in labels:
            model = apps.get_model(label)
            rows = list(model.objects.all().order_by("pk"))
            payload = serializers.serialize("json", rows)
            result[label] = {
                "count": len(rows),
                "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            }
        return result

    def _validate_dump(self, path: Path):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return False, f"JSON parse xato: {exc}"
        if not isinstance(data, list):
            return False, "root list emas"
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                return False, f"[{i}] object emas"
            if "model" not in item or "pk" not in item or "fields" not in item:
                return False, f"[{i}] model/pk/fields yo'q"
            if not isinstance(item["fields"], dict):
                return False, f"[{i}] fields dict emas"
        return True, f"OK ({len(data)} obyekt)"

    def _assert_same(self, before, after, title):
        for label in before:
            if before[label] != after[label]:
                raise CommandError(f"{title} FAIL: {label} fingerprint o'zgardi")
            self.stdout.write(
                self.style.SUCCESS(
                    f"{title}: {label} count={before[label]['count']} hash OK"
                )
            )
