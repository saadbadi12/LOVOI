from rest_framework import serializers
from .models import Vehicule, Categorie, Maintenance, Document


class CategorieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categorie
        fields = ['id', 'type', 'description', 'icon']


class VehiculeListSerializer(serializers.ModelSerializer):
    categorie_nom = serializers.CharField(source='categorie.type', read_only=True)

    class Meta:
        model = Vehicule
        fields = ['id', 'marque', 'modele', 'annee', 'immatriculation',
                  'carburant', 'transmission', 'places', 'couleur',
                  'prix_journalier', 'statut', 'categorie_nom', 'photo']


class VehiculeDetailSerializer(serializers.ModelSerializer):
    categorie = CategorieSerializer(read_only=True)
    maintenances = serializers.SerializerMethodField()

    class Meta:
        model = Vehicule
        fields = ['id', 'marque', 'modele', 'annee', 'immatriculation',
                  'carburant', 'transmission', 'places', 'couleur',
                  'prix_journalier', 'caution', 'kilometrage', 'statut',
                  'categorie', 'description', 'photo', 'maintenances']

    def get_maintenances(self, obj):
        return obj.maintenances.all().values('type', 'date_prevue', 'statut')[:5]


class MaintenanceSerializer(serializers.ModelSerializer):
    vehicule_imma = serializers.CharField(source='vehicule.immatriculation', read_only=True)

    class Meta:
        model = Maintenance
        fields = ['id', 'vehicule', 'vehicule_imma', 'type', 'date_prevue',
                  'date_realisee', 'kilometrage', 'cout', 'statut', 'description']


class DocumentSerializer(serializers.ModelSerializer):
    vehicule_imma = serializers.CharField(source='vehicule.immatriculation', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    expires_soon = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ['id', 'vehicule', 'vehicule_imma', 'type', 'numero',
                  'date_emission', 'date_expiration', 'document',
                  'is_expired', 'expires_soon']

    def get_expires_soon(self, obj):
        return obj.expires_soon()
