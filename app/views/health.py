"""Health check endpointlari.

Hosting platformasi (Render, Railway, k8s) va monitoring tizimi uchun.

* `GET /health/`  — liveness. Bazaga ham, Redis'ga ham tegmaydi, shuning
  uchun yuk ostida ham darhol javob beradi. Platforma shu endpointga
  qarab jarayonni qayta ishga tushiradi.
* `GET /health/ready/` — readiness. Baza va keshni tekshiradi. Ulardan
  biri ishlamasa 503 qaytadi va load balancer bu instansiyaga trafik
  yubormaydi.
"""

import time

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthAPIView(APIView):
    """Liceness: jarayon tirikmi?"""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []
    swagger_schema = None

    def get(self, request, *args, **kwargs):
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class ReadinessAPIView(APIView):
    """Readiness: baza va kesh javob beryaptimi?"""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []
    swagger_schema = None

    def get(self, request, *args, **kwargs):
        checks = {}
        healthy = True

        started = time.perf_counter()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            checks["database"] = {"ok": True, "ms": round((time.perf_counter() - started) * 1000, 1)}
        except Exception as exc:
            healthy = False
            checks["database"] = {"ok": False, "error": exc.__class__.__name__}

        started = time.perf_counter()
        try:
            probe_key = "health:probe"
            cache.set(probe_key, "1", 10)
            hit = cache.get(probe_key) == "1"
            checks["cache"] = {
                "ok": hit,
                "backend": settings.CACHES["default"]["BACKEND"].rsplit(".", 1)[-1],
                "ms": round((time.perf_counter() - started) * 1000, 1),
            }
            # Kesh yiqilsa sayt ishlashda davom etadi (throttle fail-open,
            # kesh o'qishlari None qaytaradi), shuning uchun uni "not ready"
            # deb hisoblamaymiz — faqat belgilab qo'yamiz.
        except Exception as exc:
            checks["cache"] = {"ok": False, "error": exc.__class__.__name__}

        checks["celery_enabled"] = getattr(settings, "CELERY_ENABLED", False)

        return Response(
            {"status": "ready" if healthy else "degraded", "checks": checks},
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
