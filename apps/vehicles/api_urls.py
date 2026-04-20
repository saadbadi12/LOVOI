from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'', api_views.VehicleViewSet, basename='vehicle')

urlpatterns = router.urls
