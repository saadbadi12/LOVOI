from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Utilisateur, Notification
from .serializers import (
    UtilisateurSerializer,
    UtilisateurCreateSerializer,
    NotificationSerializer
)


class UtilisateurViewSet(viewsets.ModelViewSet):
    """API endpoint for users."""
    queryset = Utilisateur.objects.all().order_by('-date_inscription')
    serializer_class = UtilisateurSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return UtilisateurCreateSerializer
        return UtilisateurSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class NotificationViewSet(viewsets.ModelViewSet):
    """API endpoint for notifications."""
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(utilisateur=self.request.user).order_by('-date_envoi')

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read."""
        self.get_queryset().filter(lue=False).update(lue=True)
        return Response({'status': 'done'})
