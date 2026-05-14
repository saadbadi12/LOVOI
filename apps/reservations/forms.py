from django import forms
from django.core.exceptions import ValidationError
from datetime import date
from .models import (Reservation, Slot, Contrat, Livraison, Paiement,
                     Facture, Avis,EtatDesLieux, DemandeProlongation)


class ReservationForm(forms.ModelForm):
    latitude_depart = forms.DecimalField(required=False, widget=forms.HiddenInput())
    longitude_depart = forms.DecimalField(required=False, widget=forms.HiddenInput())
    latitude_retour = forms.DecimalField(required=False, widget=forms.HiddenInput())
    longitude_retour = forms.DecimalField(required=False, widget=forms.HiddenInput())
    lieu_depart = forms.CharField(required=False)
    lieu_retour = forms.CharField(required=False)
    delivery_address = forms.CharField(required=False)

    class Meta:
        model = Reservation
        fields = ['vehicule', 'date_debut', 'date_fin', 'lieu_depart', 'lieu_retour',
                  'latitude_depart', 'longitude_depart', 'latitude_retour', 'longitude_retour',
                  'delivery_option', 'delivery_address']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        if date_debut and date_fin:
            if date_fin < date_debut:
                raise ValidationError("La date de fin doit être après la date de début.")
            if date_debut < date.today():
                raise ValidationError("La date de début ne peut pas être dans le passé.")

        delivery_option = cleaned_data.get('delivery_option')
        delivery_address = cleaned_data.get('delivery_address')
        if delivery_option == 'LIVRAISON_DOMICILE' and not delivery_address:
            raise ValidationError("Veuillez saisir une adresse de livraison.")

        return cleaned_data

    def clean_lieu_depart(self):
        value = self.cleaned_data.get("lieu_depart")
        delivery_option = self.cleaned_data.get('delivery_option')
        # Only require if LIVRAISON_DOMICILE
        if delivery_option == 'LIVRAISON_DOMICILE':
            if not value or value.strip() == "" or value == "À définir":
                raise forms.ValidationError("Veuillez saisir une adresse de départ.")
        return value or 'Agence LOVOI'

    def clean_lieu_retour(self):
        value = self.cleaned_data.get("lieu_retour")
        delivery_option = self.cleaned_data.get('delivery_option')
        # Only require if LIVRAISON_DOMICILE
        if delivery_option == 'LIVRAISON_DOMICILE':
            if not value or value.strip() == "" or value == "À définir":
                raise forms.ValidationError("Veuillez saisir une adresse de retour.")
        return value or 'Agence LOVOI'


class SlotForm(forms.ModelForm):
    class Meta:
        model = Slot
        fields = ['localisation', 'type', 'disponible']


class LivraisonForm(forms.ModelForm):
    latitude = forms.DecimalField(required=False, widget=forms.HiddenInput())
    longitude = forms.DecimalField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Livraison
        fields = ['reservation', 'livreur', 'date_livraison',
                  'heure_livraison', 'lieu_livraison', 'latitude', 'longitude',
                  'statut', 'motif_echec']
        widgets = {
            'date_livraison': forms.DateInput(attrs={'type': 'date'}),
            'heure_livraison': forms.TimeInput(attrs={'type': 'time'}),
        }


class PaiementForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = ['reservation', 'type', 'amount', 'mode']
        widgets = {
            'amount': forms.NumberInput(attrs={'step': '0.01'}),
        }


class AvisForm(forms.ModelForm):
    class Meta:
        model = Avis
        fields = ['note', 'commentaire']
        widgets = {
            'commentaire': forms.Textarea(attrs={'rows': 3}),
        }


class EtatDesLieuxForm(forms.ModelForm):
    class Meta:
        model = EtatDesLieux
        fields = ['reservation', 'kilometrage',
                  'niveau_carburant', 'commentaire', 'photos', 'signature_client']
        widgets = {
            'commentaire': forms.Textarea(attrs={'rows': 3}),
        }


class DemandeProlongationForm(forms.ModelForm):
    class Meta:
        model = DemandeProlongation
        fields = ['reservation', 'nouvelle_date_fin']
        widgets = {
            'nouvelle_date_fin': forms.DateInput(attrs={'type': 'date'})
        }
