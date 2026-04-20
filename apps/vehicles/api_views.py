from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Vehicule, Categorie, Maintenance, Document
from .serializers import (
    VehiculeListSerializer,
    VehiculeDetailSerializer,
    CategorieSerializer,
    MaintenanceSerializer,
    DocumentSerializer,
)


class VehicleViewSet(viewsets.ModelViewSet):
    """API endpoint for vehicles."""
    queryset = Vehicule.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['marque', 'modele', 'immatriculation']
    ordering_fields = ['prix_journalier', 'annee', 'date_ajout']

    def get_serializer_class(self):
        if self.action == 'list':
            return VehiculeListSerializer
        return VehiculeDetailSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get available vehicles."""
        vehicles = self.queryset.filter(statut='DISPONIBLE')
        serializer = VehiculeListSerializer(vehicles, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_km(self, request, pk=None):
        """Update vehicle mileage."""
        vehicle = self.get_object()
        km = request.data.get('kilometrage')
        if km:
            vehicle.kilometrage = km
            vehicle.save()
            return Response({'status': 'updated', 'kilometrage': vehicle.kilometrage})
        return Response({'error': 'kilometrage required'}, status=400)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """List all categories."""
        cats = Categorie.objects.all()
        serializer = CategorieSerializer(cats, many=True)
        return Response(serializer.data)


class CategorieViewSet(viewsets.ModelViewSet):
    queryset = Categorie.objects.all()
    serializer_class = CategorieSerializer
    permission_classes = [permissions.IsAdminUser]


class MaintenanceViewSet(viewsets.ModelViewSet):
    queryset = Maintenance.objects.all().order_by('-date_prevue')
    serializer_class = MaintenanceSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all().order_by('date_expiration')
    serializer_class = DocumentSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """Get documents expiring soon."""
        from django.utils import timezone
        from datetime import timedelta
        docs = self.queryset.filter(
            date_expiration__lte=timezone.now().date() + timedelta(days=30),
            date_expiration__gte=timezone.now().date()
        )
        serializer = DocumentSerializer(docs, many=True)
        return Response(serializer.data)
