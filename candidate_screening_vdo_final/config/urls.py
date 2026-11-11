from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.shortcuts import redirect


def devtools_json(request):
    """Silence Chrome DevTools 404 — it expects this endpoint to exist."""
    return JsonResponse({})


def csrf_failure(request, reason=''):
    """Replace the raw 403 page with a clean redirect + message."""
    from django.contrib import messages
    messages.error(request, 'Your session expired. Please log in again.')
    return redirect('hr_login')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('.well-known/appspecific/com.chrome.devtools.json', devtools_json),
    path('', include('screening.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = csrf_failure
