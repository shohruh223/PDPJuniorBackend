from django.core.management.base import BaseCommand

from app.services.maintenance.cleanup_service import (
    cleanup_django_sessions,
    cleanup_jwt_blacklist,
    dedupe_finished_test_sessions,
    expire_stale_test_sessions,
    run_full_maintenance,
    run_test_data_maintenance,
)


class Command(BaseCommand):
    help = "Database maintenance: test cleanup, JWT blacklist va session tozalash."

    def add_arguments(self, parser):
        parser.add_argument(
            "--task",
            choices=[
                "all",
                "tests",
                "expire",
                "dedupe",
                "jwt",
                "sessions",
            ],
            default="all",
            help="Qaysi maintenance task ishga tushirilishini tanlang.",
        )

    def handle(self, *args, **options):
        task = options["task"]

        if task == "all":
            result = run_full_maintenance()
        elif task == "tests":
            result = run_test_data_maintenance()
        elif task == "expire":
            result = expire_stale_test_sessions()
        elif task == "dedupe":
            result = dedupe_finished_test_sessions()
        elif task == "jwt":
            result = cleanup_jwt_blacklist()
        elif task == "sessions":
            result = cleanup_django_sessions()
        else:
            result = {}

        self.stdout.write(self.style.SUCCESS(str(result)))
