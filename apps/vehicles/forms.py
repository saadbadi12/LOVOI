from django import forms
from .models import Vehicule, Categorie, Maintenance, Document, VehiculePhoto


class VehiculeForm(forms.ModelForm):
    class Meta:
        model = Vehicule
        fields = ['marque', 'modele', 'annee', 'immatriculation', 'carburant',
                  'transmission', 'places', 'couleur', 'prix_journalier', 'caution',
                  'kilometrage', 'statut', 'categorie', 'description', 'photo']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class VehiculePhotoForm(forms.ModelForm):
    class Meta:
        model = VehiculePhoto
        fields = ['photo', 'titre']


class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        fields = ['vehicule', 'type', 'date_prevue', 'date_realisee',
                  'kilometrage', 'cout', 'statut', 'description', 'technicien']
        widgets = {
            'date_prevue': forms.DateInput(attrs={'type': 'date'}),
            'date_realisee': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['vehicule', 'type', 'numero', 'date_emission', 'date_expiration', 'document']
        widgets = {
            'date_emission': forms.DateInput(attrs={'type': 'date'}),
            'date_expiration': forms.DateInput(attrs={'type': 'date'}),
        }


class CategorieForm(forms.ModelForm):
    class Meta:
        model = Categorie
        fields = ['type', 'description', 'icon']
