import requests
from django.conf import settings


class PDPAPIError(Exception):
    def __init__(self, message, *, status_code=502, payload=None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class PDPAuthAPIClient:
    BASE_URL = getattr(
        settings,
        "PDP_AUTH_BASE_URL",
        "https://adminapi.pdp.uz/api/auth/v1/junior-app"
    )

    def __init__(self, token=None):
        self.timeout = getattr(settings, "PDP_API_TIMEOUT", 15)
        self.token = token

    def get_headers(self) -> dict:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = self.token
        return headers

    def _post(self, endpoint: str, data: dict) -> dict:
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = requests.post(
                url,
                json=data,
                headers=self.get_headers(),
                timeout=self.timeout,
            )

            response.raise_for_status()

        except requests.exceptions.Timeout:
            raise PDPAPIError("External auth API timeout bo‘ldi.", status_code=504)
        except requests.exceptions.ConnectionError:
            raise PDPAPIError(
                "External auth API bilan ulanishda xatolik yuz berdi.",
                status_code=502,
            )
        except requests.exceptions.HTTPError:
            try:
                error_payload = response.json()
            except Exception:
                error_payload = {"raw": response.text}

            raise PDPAPIError(
                f"External auth API HTTP {response.status_code} xato qaytardi: {error_payload}",
                status_code=response.status_code,
                payload=error_payload,
            )
        except requests.exceptions.RequestException as e:
            raise PDPAPIError(
                f"External auth API so‘rovida xatolik: {str(e)}",
                status_code=502,
            )

        try:
            payload = response.json()
        except ValueError:
            raise PDPAPIError("External auth API JSON formatda javob qaytarmadi.")

        if not isinstance(payload, dict):
            raise PDPAPIError("External auth API noto‘g‘ri formatda javob qaytardi.")

        if not payload.get("success"):
            raise PDPAPIError(
                payload.get("message") or "External auth API success=false qaytardi.",
                status_code=400,
                payload=payload,
            )

        return payload

    def check_phone(self, phone_number: str) -> dict:
        return self._post("login", {
            "phoneNumber": phone_number,
        })

    def enter_password(self, phone_number: str, password: str) -> dict:
        return self._post("enter-password", {
            "phoneNumber": phone_number,
            "password": password,
        })

    def check_sms_code(self, sms_code_id: str, sms_code: str, phone_number: str) -> dict:
        return self._post("check-sms-code", {
            "smsCodeId": sms_code_id,
            "smsCode": sms_code,
            "phoneNumber": phone_number,
        })

    def forgot_password(self, phone_number: str) -> dict:
        return self._post("forgot-password", {
            "phoneNumber": phone_number,
        })

    def verify_sms_code(self, sms_code_id: str, sms_code: str, phone_number: str) -> dict:
        return self._post("verify-sms-code", {
            "smsCodeId": sms_code_id,
            "smsCode": sms_code,
            "phoneNumber": phone_number,
        })

    def set_new_password(
        self,
        phone_number: str,
        sms_code_id: str,
        sms_code: str,
        password: str,
        repeat_password: str,
    ) -> dict:
        return self._post("set-new-password", {
            "phoneNumber": phone_number,
            "smsCodeId": sms_code_id,
            "smsCode": sms_code,
            "password": password,
            "repeatPassword": repeat_password,
        })

    def resend_sms(self, sms_code_id: str, phone_number: str) -> dict:
        return self._post("resend-sms", {
            "smsCodeId": sms_code_id,
            "phoneNumber": phone_number,
        })