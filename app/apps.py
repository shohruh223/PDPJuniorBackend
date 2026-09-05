from django.apps import AppConfig


class AppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app"

    def ready(self):
        # Kesh invalidatsiyasi signal handlerlarini ro'yxatdan o'tkazadi.
        from app import signals  # noqa: F401
