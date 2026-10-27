from django.http import HttpResponse


class SimpleCorsMiddleware:
    """Minimal CORS so the Next.js dashboard (another port) can call the API."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response
