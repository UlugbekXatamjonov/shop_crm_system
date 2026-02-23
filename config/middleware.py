from django.http import HttpResponse


class HealthCheckMiddleware:
    """
    Railway health check uchun maxsus middleware.

    Railway health check so'rovlari 'healthcheck.railway.app' host bilan keladi.
    Bu host ALLOWED_HOSTS da bo'lmasa Django DisallowedHost xatosi beradi.

    Bu middleware /health/ URL ga kelgan so'rovlarni ALLOWED_HOSTS
    tekshiruvisiz to'g'ridan-to'g'ri 200 OK qaytaradi.

    MUHIM: Middleware zanjiridagi BIRINCHI bo'lishi shart!
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path_info == '/health/':
            return HttpResponse("OK", content_type="text/plain")
        return self.get_response(request)
