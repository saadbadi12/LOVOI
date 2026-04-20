from rest_framework import serializers
from .models import Reservation, Slot, Contrat, Livraison, Paiement, Facture, Avis,EtatDesLieux


class SlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slot
        fields = ['id', 'localisation', 'type', 'disponible']


class ReservationListSerializer(serializers.ModelSerializer):
    client_nom = serializers.CharField(source='client.get_full_name', read_only=True)
    vehicule_nom = serializers.CharField(source='vehicule.__str__', read_only=True)

    class Meta:
        model = Reservation
        fields = ['id', 'client_nom', 'vehicule_nom', 'date_debut', 'date_fin',
                  'statut_reservation', 'montant_total', 'date_reservation']


class ReservationDetailSerializer(serializers.ModelSerializer):
    client = serializers.StringRelatedField()
    vehicule = serializers.StringRelatedField()
    slot = SlotSerializer(read_only=True)

    class Meta:
        model = Reservation
        fields = ['id', 'client', 'vehicule', 'slot', 'date_reservation',
                  'date_debut', 'date_fin', 'lieu_depart', 'lieu_retour',
                  'statut_reservation', 'montant_total', 'caution_versee',
                  'nombre_jours']


class ReservationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ['vehicule', 'date_debut', 'date_fin', 'lieu_depart', 'lieu_retour']

    def validate(self, data):
        if data['date_fin'] < data['date_debut']:
            raise serializers.ValidationError("Date fin must be after date debut")
        return data


class PaiementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paiement
        fields = ['id', 'reservation', 'type', 'amount', 'mode', 'statut', 'date_paiement']


class LivraisonSerializer(serializers.ModelSerializer):
    livreur_nom = serializers.CharField(source='livreur.get_full_name', read_only=True)

    class Meta:
        model = Livraison
        fields = ['id', 'reservation', 'livreur', 'livreur_nom', 'type',
                  'date_livraison', 'heure_livraison', 'lieu_livraison', 'statut']


class AvisSerializer(serializers.ModelSerializer):
    client_nom = serializers.CharField(source='client.get_full_name', read_only=True)

    class Meta:
        model = Avis
        fields = ['id', 'client', 'client_nom', 'vehicule', 'note', 'commentaire', 'date']


class EtatDesLieuxSerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.get_full_name', read_only=True)

    class Meta:
        model = EtatDesLieux
        fields = ['id', 'reservation', 'type', 'date', 'employe', 'employe_nom',
                  'kilometrage', 'niveau_carburant', 'commentaire']
