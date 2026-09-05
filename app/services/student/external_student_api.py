import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PDPStudentAPIError(Exception):
    pass


class PDPStudentAPIClient:
    BASE_URL = getattr(settings, "PDP_STUDENT_BASE_URL", "https://adminapi.pdp.uz/api")

    def __init__(self, token=None):
        self.timeout = getattr(settings, "PDP_API_TIMEOUT", 15)
        self.token = self._normalize_token(token)

    @staticmethod
    def _normalize_token(token):
        token = (token or "").strip()
        if not token:
            return None
        if token.lower().startswith("bearer "):
            return token
        return f"Bearer {token}"

    def get_headers(self):
        headers = {
            "Accept": "application/json",
        }
        if self.token:
            headers["Authorization"] = self.token
        return headers

    def _get(self, endpoint: str, params=None) -> dict:
        url = f"{self.BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
        try:
            response = requests.get(
                url,
                params=params or {},
                headers=self.get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise PDPStudentAPIError("External student API timeout bo‘ldi.")
        except requests.exceptions.HTTPError:
            # XAVFSIZLIK: tashqi servisning javob tanasi (stack trace,
            # ichki yo'llar, framework versiyalari) foydalanuvchiga
            # ko'rsatilmaydi — u faqat logga yoziladi.
            try:
                detail = response.json()
            except Exception:
                detail = response.text[:500]
            logger.warning("PDP student API HTTP %s: %s", response.status_code, detail)
            raise PDPStudentAPIError(
                f"Tashqi servis xatosi (HTTP {response.status_code})."
            )
        except requests.exceptions.RequestException as e:
            raise PDPStudentAPIError(str(e))

        try:
            payload = response.json()
        except ValueError:
            raise PDPStudentAPIError("External student API JSON qaytarmadi")

        if not isinstance(payload, dict):
            raise PDPStudentAPIError("External student API noto‘g‘ri formatda javob qaytardi")

        if payload.get("success") is False:
            raise PDPStudentAPIError(payload.get("message") or "External student API success=false qaytardi")

        return payload

    def get_student_info(self, student_id: str) -> dict:
        return self._get(f"education/v1/junior-app/info-student/{student_id}")

    def get_student_payment_history(self, student_id: str) -> dict:
        return self._get(f"education/v1/junior-app/payment-history/{student_id}")

    def get_student_invoices(self, student_id: str) -> dict:
        return self._get(f"education/v1/junior-app/student-invoices/{student_id}")
