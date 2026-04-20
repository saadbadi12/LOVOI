from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'', api_views.ReservationViewSet, basename='reservation')

urlpatterns = router.urls
