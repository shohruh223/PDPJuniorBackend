from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from app.services.data_transfer import (
    DEFAULT_PRESET,
    EXPORT_MODES,
    PRESETS,
    default_export_dir,
    default_manifest_name,
    export_combined,
    export_per_table,
    resolve_labels,
)


class Command(BaseCommand):
    help = (
        "Database ma'lumotlarini JSON ga eksport qiladi. "
        "Rejimlar: combined (bitta fayl), per-table (har jadval alohida), both."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--preset",
            default=DEFAULT_PRESET,
            choices=sorted(PRESETS.keys()),
            help=(
                "Ma'lumotlar to'plami: essential, with-users, full, "
                "catalog, content, users, runtime"
            ),
        )
        parser.add_argument(
            "--models",
            "--tables",
            dest="models",
            nargs="+",
            default=None,
            help="Faqat tanlangan jadvallar: app.Course app.Question ...",
        )
        parser.add_argument(
            "--mode",
            default="both",
            choices=EXPORT_MODES,
            help=(
                "combined=bitta JSON, per-table=har jadval alohida, "
                "both=ikkala (default)"
            ),
        )
        parser.add_argument(
            "--output",
            "-o",
            default=None,
            help=(
                "combined uchun fayl yo'li yoki per-table uchun papka. "
                "Default: data/exports/"
            ),
        )
        parser.add_argument(
            "--indent",
            type=int,
            default=2,
            help="JSON indent (default: 2)",
        )

    def handle(self, *args, **options):
        preset = options["preset"]
        mode = options["mode"]
        indent = options["indent"]

        try:
            labels = resolve_labels(preset=preset, labels=options["models"])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        base_dir = default_export_dir()
        output = options["output"]

        self.stdout.write(f"Rejim: {mode} | Preset: {preset}")
        self.stdout.write(f"Jadvallar ({len(labels)}):")
        for label in labels:
            self.stdout.write(f"  - {label}")

        results = []

        if mode in ("combined", "both"):
            if output and mode == "combined":
                combined_path = Path(output)
                if combined_path.suffix.lower() != ".json":
                    combined_path = combined_path / default_manifest_name(preset)
            else:
                combined_path = base_dir / default_manifest_name(preset)

            result = export_combined(labels, combined_path, indent=indent)
            results.append(result)
            size_kb = Path(result["path"]).stat().st_size / 1024
            self.stdout.write(
                self.style.SUCCESS(
                    f"[combined] {result['total_objects']} obyekt -> "
                    f"{result['path']} ({size_kb:.1f} KB)"
                )
            )

        if mode in ("per-table", "both"):
            if output and mode == "per-table":
                tables_dir = Path(output)
            elif output and mode == "both":
                # both da --output combined fayl bo'lishi mumkin; per-table alohida papka
                tables_dir = base_dir / f"pdp_junior_{preset}_tables"
            else:
                tables_dir = base_dir / f"pdp_junior_{preset}_tables"

            result = export_per_table(
                labels,
                tables_dir,
                preset=preset if not options["models"] else "custom",
                indent=indent,
            )
            results.append(result)
            self.stdout.write(
                self.style.SUCCESS(
                    f"[per-table] {result['total_objects']} obyekt -> "
                    f"{result['path']} ({len(result['files'])} fayl + manifest)"
                )
            )
            for item in result["files"]:
                self.stdout.write(
                    f"  {item['order']:02d}. {item['model']}: "
                    f"{item['count']} -> {item['file']}"
                )

        self.stdout.write("")
        self.stdout.write("Import misollari:")
        for result in results:
            if result["mode"] == "combined":
                self.stdout.write(
                    f'  python manage.py import_db_json -i "{result["path"]}"'
                )
            else:
                self.stdout.write(
                    f'  python manage.py import_db_json -i "{result["path"]}"'
                )
        self.stdout.write(
            "Eslatma: media/ yoki R2 fayllarini alohida ko'chiring. "
            "Admin panelda ham har bir jadval uchun JSON Import/Export bor."
        )
