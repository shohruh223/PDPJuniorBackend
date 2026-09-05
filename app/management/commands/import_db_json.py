import json
from pathlib import Path

from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from app.services.data_transfer import discover_import_files


class Command(BaseCommand):
    help = (
        "JSON dump(lar)dan ma'lumot import qiladi. "
        "Bitta fayl YOKI per-table papka (manifest.json bilan) qabul qiladi."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--input",
            "-i",
            required=True,
            help="Bitta JSON fayl yoki per-table papka yo'li",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Faqat tekshiradi, DB ga yozmaydi",
        )
        parser.add_argument(
            "--ignorenonexistent",
            action="store_true",
            help="Model/field yo'q bo'lsa o'tkazib yuboradi",
        )

    def handle(self, *args, **options):
        input_path = Path(options["input"])
        if not input_path.exists():
            raise CommandError(f"Yo'l topilmadi: {input_path}")

        try:
            files = discover_import_files(input_path)
        except FileNotFoundError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            f"Import manba: {input_path} "
            f"({'papka' if input_path.is_dir() else 'fayl'}, {len(files)} JSON)"
        )

        all_payloads: list[tuple[Path, list]] = []
        model_counts: dict[str, int] = {}

        for file_path in files:
            raw = file_path.read_text(encoding="utf-8")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise CommandError(f"JSON noto'g'ri ({file_path}): {exc}") from exc

            if not isinstance(payload, list):
                raise CommandError(
                    f"{file_path}: Django dumpdata list formati kutilgan."
                )

            all_payloads.append((file_path, payload))
            for item in payload:
                model = item.get("model", "?")
                model_counts[model] = model_counts.get(model, 0) + 1

            self.stdout.write(f"  - {file_path.name}: {len(payload)} obyekt")

        total = sum(len(p) for _, p in all_payloads)
        self.stdout.write(f"Jami: {total} obyekt, {len(model_counts)} model")

        if options["dry_run"]:
            self.stdout.write("Dry-run — modelllar:")
            for model, count in sorted(model_counts.items()):
                self.stdout.write(f"  - {model}: {count}")
            self.stdout.write(self.style.WARNING("DB o'zgartirilmadi (--dry-run)."))
            return

        created = 0
        updated = 0
        errors = []

        with transaction.atomic():
            for file_path, payload in all_payloads:
                raw = json.dumps(payload)
                for obj in serializers.deserialize(
                    "json",
                    raw,
                    ignorenonexistent=options["ignorenonexistent"],
                ):
                    try:
                        # Har bir obyekt o'z savepoint'ida — aks holda
                        # PostgreSQL'da bitta xato tranzaksiyani "aborted"
                        # holatiga tushirib, keyingi barcha so'rovlarni
                        # TransactionManagementError bilan yiqitadi.
                        with transaction.atomic():
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
                            f"{file_path.name} | "
                            f"{obj.object.__class__.__name__} "
                            f"pk={obj.object.pk}: {exc}"
                        )
                        if len(errors) >= 20:
                            break
                if len(errors) >= 20:
                    break

            if errors:
                raise CommandError(
                    "Import xatolari (rollback):\n" + "\n".join(errors)
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"OK: yaratildi={created}, yangilandi={updated}, "
                f"jami={created + updated}"
            )
        )
