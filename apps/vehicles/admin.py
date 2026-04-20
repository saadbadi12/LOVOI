from django.contrib import admin
from .models import Vehicule, Categorie, Maintenance, Document, VehiculePhoto


class VehiculePhotoInline(admin.TabularInline):
    model = VehiculePhoto
    extra = 1


@admin.register(Vehicule)
class VehiculeAdmin(admin.ModelAdmin):
    list_display = ('immatriculation', 'marque', 'modele', 'annee',
                    'prix_journalier', 'statut', 'categorie')
    list_filter = ('statut', 'carburant', 'transmission', 'categorie', 'annee')
    search_fields = ('marque', 'modele', 'immatriculation')
    inlines = [VehiculePhotoInline]


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('type', 'description')


@admin.register(Maintenance)
class MaintenanceAdmin(admin.ModelAdmin):
    list_display = ('vehicule', 'type', 'date_prevue', 'statut', 'technicien')
    list_filter = ('statut', 'type')
    search_fields = ('vehicule__immatriculation',)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('vehicule', 'type', 'numero', 'date_expiration', 'is_expired_display')
    list_filter = ('type',)
    search_fields = ('vehicule__immatriculation', 'numero')

    def is_expired_display(self, obj):
        return obj.is_expired()
    is_expired_display.boolean = True
    is_expired_display.short_description = 'Expiré'


@admin.register(VehiculePhoto)
class VehiculePhotoAdmin(admin.ModelAdmin):
    list_display = ('vehicule', 'titre')
