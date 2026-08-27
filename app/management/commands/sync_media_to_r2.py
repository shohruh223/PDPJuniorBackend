from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.files.storage import default_storage


class Command(BaseCommand):
    help = "Lokal media/ fayllarni hozirgi default storage (R2) ga yuklaydi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default=str(Path(settings.BASE_DIR) / "media"),
            help="Lokal media papka (default: BASE_DIR/media)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Faqat ro'yxat, yuklamasdan",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "USE_R2", False):
            raise CommandError("USE_R2=1 bo'lishi kerak.")

        source = Path(options["source"])
        if not source.exists():
            raise CommandError(f"Papka topilmadi: {source}")

        uploaded = 0
        skipped = 0
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(source).as_posix()
            if options["dry_run"]:
                self.stdout.write(f"DRY {rel}")
                continue
            if default_storage.exists(rel):
                skipped += 1
                self.stdout.write(f"SKIP exists {rel}")
                continue
            with path.open("rb") as fh:
                saved = default_storage.save(rel, fh)
            uploaded += 1
            self.stdout.write(self.style.SUCCESS(f"OK {saved}"))

        self.stdout.write(
            self.style.NOTICE(f"uploaded={uploaded} skipped={skipped} dry_run={options['dry_run']}")
        )
