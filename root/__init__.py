try:
    from .celery import app as celery_app
except ImportError:  # Celery o'rnatilmagan lokal muhit
    celery_app = None

__all__ = ("celery_app",)
