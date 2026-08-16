from django.utils import translation


class AdminUzbekLocaleMiddleware:
    """Admin panel tilini brauzer tilidan qat’i nazar o‘zbekcha qiladi."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin"):
            translation.activate("uz")
            request.LANGUAGE_CODE = "uz"
        return self.get_response(request)
