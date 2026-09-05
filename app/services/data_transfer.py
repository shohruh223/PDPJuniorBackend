"""
Database JSON import/export konfiguratsiyasi.

Django dumpdata/loaddata formatida ishlaydi — ID va FK lar saqlanadi.
Media fayllar (rasmlar) alohida ko'chirilishi kerak (media/ yoki R2).

Ikki rejim:
  1) combined  — bitta JSON fayl (to'liq preset)
  2) per-table — har bir model alohida JSON + manifest.json
"""

from __future__ import annotations

import json
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core import serializers


# FK bog'lanish tartibida: avval parent, keyin child.
# Transient (JWT, django session, admin log) kiritilmaydi.
EXPORT_GROUPS: dict[str, list[str]] = {
    "catalog": [
        "app.Course",
        "app.Module",
        "app.Lesson",
        "app.Question",
    ],
    "content": [
        "app.Branch",
        "app.Mentor",
        "app.Portfolio",
        "app.GalleryPost",
        "app.CoinProduct",
        "app.MonthHero",
    ],
    "users": [
        "app.User",
        "app.StudentProfile",
        "app.StudentMark",
        "app.StudentPaymentHistory",
        "app.StudentInvoice",
    ],
    "runtime": [
        "app.CoinOrder",
        "app.TestSession",
        "app.TestSessionQuestion",
        "app.TestSessionAnswer",
        "app.StudentQuestionReward",
    ],
}

DEFAULT_PRESET = "essential"

PRESETS: dict[str, list[str]] = {
    "essential": ["catalog", "content"],
    "with-users": ["catalog", "content", "users"],
    "full": ["catalog", "content", "users", "runtime"],
    "catalog": ["catalog"],
    "content": ["content"],
    "users": ["users"],
    "runtime": ["runtime"],
}

EXPORT_MODES = ("combined", "per-table", "both")

EXCLUDED_APPS = (
    "contenttypes",
    "auth.Permission",
    "admin",
    "sessions",
    "token_blacklist",
)


def resolve_labels(preset: str | None = None, labels: list[str] | None = None) -> list[str]:
    """Preset yoki qo'lda berilgan label lardan yakuniy model label ro'yxatini yasaydi."""
    if labels:
        return list(dict.fromkeys(labels))

    preset = preset or DEFAULT_PRESET
    if preset not in PRESETS:
        raise ValueError(
            f"Noma'lum preset: {preset}. Mumkin: {', '.join(sorted(PRESETS))}"
        )

    result: list[str] = []
    for group_name in PRESETS[preset]:
        result.extend(EXPORT_GROUPS[group_name])
    return list(dict.fromkeys(result))


def default_export_dir() -> Path:
    path = Path(settings.BASE_DIR) / "data" / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_manifest_name(preset: str) -> str:
    return f"pdp_junior_{preset}.json"


def label_to_filename(label: str) -> str:
    """app.Course -> 01_app_Course.json emas, label asosida."""
    return label.replace(".", "_") + ".json"


def serialize_model(label: str, *, indent: int = 2) -> list[dict]:
    model = apps.get_model(label)
    qs = model.objects.all().order_by("pk")
    raw = serializers.serialize(
        "json",
        qs.iterator(chunk_size=500),
        indent=indent,
        use_natural_foreign_keys=False,
        use_natural_primary_keys=False,
    )
    return json.loads(raw)


def write_json(path: Path, payload: list[dict], *, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=indent),
        encoding="utf-8",
    )


def export_combined(labels: list[str], output_path: Path, *, indent: int = 2) -> dict:
    combined: list[dict] = []
    per_model_counts: dict[str, int] = {}
    for label in labels:
        rows = serialize_model(label, indent=indent)
        combined.extend(rows)
        per_model_counts[label] = len(rows)

    write_json(output_path, combined, indent=indent)
    return {
        "mode": "combined",
        "path": str(output_path),
        "total_objects": len(combined),
        "models": per_model_counts,
    }


def export_per_table(
    labels: list[str],
    output_dir: Path,
    *,
    preset: str = "custom",
    indent: int = 2,
) -> dict:
    """
    Har bir jadval alohida JSON + manifest.json (import tartibi uchun).
    Fayl nomlari: 01_app_Course.json, 02_app_Module.json, ...
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    files: list[dict] = []
    total = 0

    for index, label in enumerate(labels, start=1):
        rows = serialize_model(label, indent=indent)
        filename = f"{index:02d}_{label_to_filename(label)}"
        file_path = output_dir / filename
        write_json(file_path, rows, indent=indent)
        files.append(
            {
                "order": index,
                "model": label,
                "file": filename,
                "count": len(rows),
            }
        )
        total += len(rows)

    manifest = {
        "format": "pdp_junior_per_table_v1",
        "preset": preset,
        "total_objects": total,
        "files": files,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=indent),
        encoding="utf-8",
    )

    return {
        "mode": "per-table",
        "path": str(output_dir),
        "manifest": str(manifest_path),
        "total_objects": total,
        "files": files,
    }


def discover_import_files(path: Path) -> list[Path]:
    """
    Bitta JSON yoki papka (manifest yoki tartiblangan per-table fayllar).
    """
    if path.is_file():
        return [path]

    if not path.is_dir():
        raise FileNotFoundError(f"Yo'l topilmadi: {path}")

    manifest_path = path / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = []
        for item in manifest.get("files", []):
            # XAVFSIZLIK: `item["file"]` ishonchsiz manbadan kelishi mumkin.
            # Nisbiy `../` ham, absolyut yo'l ham bazaviy papkadan chiqib
            # ketadi (Path("/a") / "/etc/passwd" == Path("/etc/passwd")).
            file_path = (path / item["file"]).resolve()
            if not file_path.is_relative_to(path.resolve()):
                raise ValueError(
                    f"Manifestdagi yo'l papkadan tashqariga chiqmoqda: {item['file']}"
                )
            if file_path.exists():
                files.append(file_path)
        if files:
            return files

    # Manifest yo'q bo'lsa — raqamli prefix bo'yicha tartib
    json_files = sorted(
        p for p in path.glob("*.json") if p.name != "manifest.json"
    )
    if not json_files:
        raise FileNotFoundError(f"Papkada JSON fayl yo'q: {path}")
    return json_files
