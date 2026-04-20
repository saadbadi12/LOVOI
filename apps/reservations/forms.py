from django import forms
from django.core.exceptions import ValidationError
from .models import (Reservation, Slot, Contrat, Livraison, Paiement,
                     Facture, Avis,EtatDesLieux)


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['vehicule', 'date_debut', 'date_fin', 'lieu_depart', 'lieu_retour']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        vehicule = cleaned_data.get('vehicule')

        if date_debut and date_fin:
            if date_fin < date_debut:
                raise ValidationError("La date de fin doit être après la date de début.")
            if date_debut < date.today():
                raise ValidationError("La date de début ne peut pas être dans le passé.")

        if vehicule and vehicule.statut != 'DISPONIBLE':
            raise ValidationError("Ce véhicule n'est pas disponible.")

        return cleaned_data


class SlotForm(forms.ModelForm):
    class Meta:
        model = Slot
        fields = ['localisation', 'type', 'disponible']


class LivraisonForm(forms.ModelForm):
    class Meta:
        model = Livraison
        fields = ['reservation', 'livreur', 'type', 'date_livraison',
                  'heure_livraison', 'lieu_livraison']
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
        fields = ['reservation', 'type', 'employe', 'kilometrage',
                  'niveau_carburant', 'commentaire', 'photos', 'signature_client']
        widgets = {
            'commentaire': forms.Textarea(attrs={'rows': 3}),
        }
