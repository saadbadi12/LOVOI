from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.accounts.urls')),
    path('vehicles/', include('apps.vehicles.urls')),
    path('reservations/', include('apps.reservations.urls')),
    path('payments/', include('apps.payments.urls')),
    path('api/', include('apps.accounts.api_urls')),
    path('api/vehicles/', include('apps.vehicles.api_urls')),
    path('api/reservations/', include('apps.reservations.api_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
