from django.contrib import admin
from .models import (Reservation, Slot, Contrat, Livraison, Paiement,
                     Facture, Avis,EtatDesLieux)
from .models import DemandeProlongation


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'localisation', 'type', 'disponible')
    list_filter = ('type', 'disponible')


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'vehicule', 'date_debut', 'date_fin',
                    'statut_reservation', 'montant_total', 'latitude_depart', 'longitude_depart')
    list_filter = ('statut_reservation', 'date_debut', 'date_fin')
    search_fields = ('client__username', 'vehicule__immatriculation', 'lieu_depart', 'lieu_retour')
    raw_id_fields = ('client', 'vehicule', 'slot')


@admin.register(Contrat)
class ContratAdmin(admin.ModelAdmin):
    list_display = ('id', 'reservation', 'date_generation', 'statut_signature')


@admin.register(Livraison)
class LivraisonAdmin(admin.ModelAdmin):
    list_display = ('id', 'reservation', 'livreur', 'type', 'date_livraison', 'statut', 'latitude', 'longitude')
    list_filter = ('statut', 'type')
    search_fields = ('lieu_livraison', 'reservation__client__username')
    raw_id_fields = ('reservation', 'livreur')


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('id', 'reservation', 'type', 'amount', 'mode', 'statut', 'date_paiement')
    list_filter = ('mode', 'statut', 'type')
    raw_id_fields = ('reservation',)


@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = ('id', 'reservation', 'type', 'date_facture', 'montant_ht', 'tva', 'montant_ttc')
    list_filter = ('type', 'date_facture')
    raw_id_fields = ('reservation',)


@admin.register(Avis)
class AvisAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'vehicule', 'note', 'date')
    list_filter = ('note',)
    raw_id_fields = ('client', 'vehicule')


@admin.register(EtatDesLieux)
class EtatDesLieuxAdmin(admin.ModelAdmin):
    list_display = ('id', 'reservation', 'type', 'date', 'employe', 'kilometrage')
    list_filter = ('type',)
    raw_id_fields = ('reservation', 'employe')


@admin.register(DemandeProlongation)
class DemandeProlongationAdmin(admin.ModelAdmin):
    list_display = ('id', 'reservation', 'nouvelle_date_fin', 'statut', 'created_at')
    list_filter = ('statut', 'created_at')
    raw_id_fields = ('reservation',)
