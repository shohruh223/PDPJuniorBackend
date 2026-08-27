from django.contrib.auth.forms import AuthenticationForm


def normalize_uzb_phone(value: str) -> str:
    """Login uchun telefonni +998XXXXXXXXX formatiga keltiradi."""
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if digits.startswith("998") and len(digits) >= 12:
        digits = digits[3:]
    digits = digits[-9:] if len(digits) > 9 else digits
    if len(digits) == 9:
        return f"+998{digits}"
    raw = str(value or "").strip()
    return raw


class AdminPhoneAuthenticationForm(AuthenticationForm):
    """Admin login: username maydonidagi telefonni normalizatsiya qiladi."""

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": (
            "Xodimlar akkaunti uchun to‘g‘ri telefon raqami (+998...) "
            "va parolni kiriting. Hisob staff huquqiga ega bo‘lishi kerak."
        ),
    }

    def clean_username(self):
        username = self.cleaned_data.get("username", "")
        return normalize_uzb_phone(username)
