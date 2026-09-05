"""Matn bilan ishlash yordamchilari."""


def split_full_name(full_name: str) -> tuple[str, str]:
    """To'liq ismni (ism, familiya) juftligiga ajratadi.

    Ilgari bu funksiya `auth_service.py` va `student_dashboard_service.py`
    da alohida-alohida yozilgan edi.
    """
    full_name = (full_name or "").strip()
    if not full_name:
        return "", ""
    parts = full_name.split()
    return parts[0], " ".join(parts[1:]) if len(parts) > 1 else ""


def build_initials(user) -> str | None:
    """Foydalanuvchi ismidan avatar initsiallari: "Ali Valiyev" -> "AV"."""
    first = (user.first_name or "")[:1].upper()
    last = (user.last_name or "")[:1].upper()
    initials = f"{first}{last}"
    if initials:
        return initials
    if user.phone_number:
        return user.phone_number[-2:]
    return None


def estimated_test_minutes(questions_count) -> int:
    """Test uchun ajratilgan vaqt (daqiqa).

    YAGONA MANBA. Ilgari bu hisob uch joyda uch xil edi
    (`count`, `count + 1`, `max(1, count + 1)`), natijada bitta dars
    dashboardda "10 daqiqa", test ekranida "11 daqiqa" ko'rinardi.
    Haqiqiy taymer `TestSession.save()` da `total_questions + 1` bo'lgani
    uchun to'g'ri qiymat shu.
    """
    try:
        count = int(questions_count or 0)
    except (TypeError, ValueError):
        count = 0
    return max(1, count + 1)
