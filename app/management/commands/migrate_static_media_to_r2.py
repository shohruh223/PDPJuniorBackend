"""
DB dagi static/img/... assetlarni frontenddan olib R2 ga yuklaydi.

Ishlatish:
  python manage.py migrate_static_media_to_r2
  python manage.py migrate_static_media_to_r2 --dry-run
"""

from __future__ import annotations

import mimetypes
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


FRONTEND_ORIGIN_DEFAULT = "https://pdp-junior-test.netlify.app"


def _collect_static_paths() -> set[str]:
    from app.models.auth import StudentProfile
    from app.models.branch import Branch
    from app.models.gallery import GalleryPost
    from app.models.mentors import Mentor
    from app.models.portfolio import Portfolio
    from app.models import Course

    paths: set[str] = set()

    def add(value: str | None):
        if not value:
            return
        value = str(value).strip()
        if value.startswith("static/"):
            paths.add(value)

    for course in Course.objects.all().only("image_url"):
        add(course.image_url)

    for branch in Branch.objects.all().only("image_url", "album"):
        add(branch.image_url)
        for item in branch.album or []:
            if isinstance(item, dict):
                add(item.get("url"))

    for mentor in Mentor.objects.all().only("avatar"):
        avatar = mentor.avatar or {}
        if isinstance(avatar, dict):
            add(avatar.get("url"))

    for portfolio in Portfolio.objects.all().only("image"):
        image = portfolio.image or {}
        if isinstance(image, dict):
            add(image.get("url"))

    for post in GalleryPost.objects.all().only("cover_image", "media"):
        add(post.cover_image)
        for item in post.media or []:
            if isinstance(item, dict):
                add(item.get("src") or item.get("url"))

    for profile in StudentProfile.objects.exclude(avatar_url="").only("avatar_url"):
        add(profile.avatar_url)

    return paths


def _download(url: str) -> tuple[bytes, str | None]:
    req = Request(url, headers={"User-Agent": "PDPJuniorMediaMigrator/1.0"})
    with urlopen(req, timeout=40) as resp:
        content_type = resp.headers.get("Content-Type")
        return resp.read(), content_type


class Command(BaseCommand):
    help = "DB dagi static/* fayllarni frontenddan R2 ga ko'chiradi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--frontend-origin",
            default=getattr(settings, "FRONTEND_ORIGIN", None)
            or FRONTEND_ORIGIN_DEFAULT,
            help="Assetlarni olish uchun frontend origin",
        )
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--force",
            action="store_true",
            help="R2 da bor bo'lsa ham qayta yukla",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "USE_R2", False):
            raise CommandError("USE_R2=1 bo'lishi kerak.")

        origin = options["frontend_origin"].rstrip("/")
        dry_run = options["dry_run"]
        force = options["force"]

        paths = sorted(_collect_static_paths())
        self.stdout.write(f"Topilgan unique static path: {len(paths)}")
        self.stdout.write(f"Frontend origin: {origin}")

        uploaded = 0
        skipped = 0
        failed = 0

        for path in paths:
            source_url = f"{origin}/{path}"
            if dry_run:
                self.stdout.write(f"DRY {path} <- {source_url}")
                continue

            if not force and default_storage.exists(path):
                skipped += 1
                self.stdout.write(f"SKIP exists {path}")
                continue

            try:
                payload, content_type = _download(source_url)
            except (HTTPError, URLError, TimeoutError) as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"FAIL download {path}: {exc}"))
                continue

            if not content_type:
                content_type, _ = mimetypes.guess_type(path)

            # django-storages S3: ContentFile + save
            if default_storage.exists(path):
                default_storage.delete(path)

            saved = default_storage.save(path, ContentFile(payload))
            uploaded += 1
            public_url = default_storage.url(saved)
            self.stdout.write(self.style.SUCCESS(f"OK {saved} -> {public_url}"))

        self.stdout.write(
            self.style.NOTICE(
                f"done uploaded={uploaded} skipped={skipped} failed={failed} dry_run={dry_run}"
            )
        )
        if failed:
            raise CommandError(f"{failed} ta fayl yuklanmadi.")
