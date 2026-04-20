from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'users', api_views.UtilisateurViewSet)
router.register(r'notifications', api_views.NotificationViewSet)

urlpatterns = router.urls
