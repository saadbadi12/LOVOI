from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Reservation, Slot, Paiement, Livraison, Avis, EtatDesLieux
from .serializers import (
    ReservationListSerializer, ReservationDetailSerializer,
    ReservationCreateSerializer, SlotSerializer, PaiementSerializer,
    LivraisonSerializer, AvisSerializer, EtatDesLieuxSerializer
)


class ReservationViewSet(viewsets.ModelViewSet):
    """API endpoint for reservations."""
    queryset = Reservation.objects.all().order_by('-date_reservation')
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['date_reservation', 'date_debut']

    def get_serializer_class(self):
        if self.action == 'create':
            return ReservationCreateSerializer
        if self.action in ['list']:
            return ReservationListSerializer
        return ReservationDetailSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'my_reservations']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    @action(detail=False, methods=['get'])
    def my(self, request):
        """Get current user's reservations."""
        reservations = self.queryset.filter(client=request.user)
        serializer = ReservationListSerializer(reservations, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        reservation = self.get_object()
        if reservation.confirmer():
            return Response({'status': 'confirmed'})
        return Response({'error': 'Cannot confirm'}, status=400)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        reservation = self.get_object()
        if reservation.annuler():
            return Response({'status': 'cancelled'})
        return Response({'error': 'Cannot cancel'}, status=400)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        reservation = self.get_object()
        if reservation.demarrer():
            return Response({'status': 'started'})
        return Response({'error': 'Cannot start'}, status=400)

    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        reservation = self.get_object()
        if reservation.terminer():
            return Response({'status': 'ended'})
        return Response({'error': 'Cannot end'}, status=400)

    @action(detail=True, methods=['get'])
    def paiements(self, request, pk=None):
        reservation = self.get_object()
        paiements = reservation.paiements.all()
        serializer = PaiementSerializer(paiements, many=True)
        return Response(serializer.data)


class SlotViewSet(viewsets.ModelViewSet):
    queryset = Slot.objects.all()
    serializer_class = SlotSerializer
    permission_classes = [permissions.IsAuthenticated]


class PaiementViewSet(viewsets.ModelViewSet):
    queryset = Paiement.objects.all().order_by('-date_paiement')
    serializer_class = PaiementSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        paiement = self.get_object()
        if paiement.confirmer():
            return Response({'status': 'confirmed'})
        return Response({'error': 'Cannot confirm'}, status=400)


class LivraisonViewSet(viewsets.ModelViewSet):
    queryset = Livraison.objects.all().order_by('-date_livraison')
    serializer_class = LivraisonSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]


class AvisViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Avis.objects.all().order_by('-date')
    serializer_class = AvisSerializer
    permission_classes = [permissions.AllowAny]


class EtatDesLieuxViewSet(viewsets.ModelViewSet):
    queryset = EtatDesLieux.objects.all().order_by('-date')
    serializer_class = EtatDesLieuxSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]
