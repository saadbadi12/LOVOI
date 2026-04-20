from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone


class Slot(models.Model):
    """Parking/storage slot."""
    TYPE_CHOICES = [
        ('STANDARD', _('Standard')),
        ('COUVERT', _('Couvert')),
        ('SECURISE', _('Sécurisé')),
    ]

    localisation = models.CharField(_('Localisation'), max_length=255)
    type = models.CharField(_('Type'), max_length=50, choices=TYPE_CHOICES, default='STANDARD')
    disponible = models.BooleanField(_('Disponible'), default=True)

    class Meta:
        verbose_name = _('Slot')
        verbose_name_plural = _('Slots')
        ordering = ['localisation']

    def __str__(self):
        return f"Slot {self.id} - {self.localisation}"


class Reservation(models.Model):
    """Core booking between client and vehicle."""
    STATUT_CHOICES = [
        ('EN_ATTENTE', _('En attente')),
        ('CONFIRMEE', _('Confirmée')),
        ('EN_COURS', _('En cours')),
        ('TERMINEE', _('Terminée')),
        ('ANNULEE', _('Annulée')),
    ]

    client = models.ForeignKey('accounts.Utilisateur', on_delete=models.CASCADE,
                              related_name='reservations', limit_choices_to={'role': 'CLIENT'})
    vehicule = models.ForeignKey('vehicles.Vehicule', on_delete=models.CASCADE,
                                 related_name='reservations')
    slot = models.ForeignKey(Slot, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='reservations')
    date_reservation = models.DateTimeField(_('Date de réservation'), auto_now_add=True)
    date_debut = models.DateField(_('Date de début'))
    date_fin = models.DateField(_('Date de fin'))
    lieu_depart = models.CharField(_('Lieu de départ'), max_length=255)
    lieu_retour = models.CharField(_('Lieu de retour'), max_length=255)
    statut_reservation = models.CharField(_('Statut'), max_length=20,
                                         choices=STATUT_CHOICES, default='EN_ATTENTE')
    montant_total = models.DecimalField(_('Montant total (MAD)'), max_digits=10,
                                       decimal_places=2, null=True, blank=True)
    caution_versee = models.BooleanField(_('Caution versée'), default=False)
    nombre_jours = models.IntegerField(_('Nombre de jours'), default=1)

    class Meta:
        verbose_name = _('Réservation')
        verbose_name_plural = _('Réservations')
        ordering = ['-date_reservation']

    def __str__(self):
        return f"Réservation {self.id} - {self.client} - {self.vehicule}"

    def calculer_total(self):
        """Calculate total price based on duration and vehicle daily rate."""
        if self.date_debut and self.date_fin and self.vehicule:
            delta = self.date_fin - self.date_debut
            self.nombre_jours = max(delta.days, 1)
            self.montant_total = Decimal(self.nombre_jours) * self.vehicule.prix_journalier
        return self.montant_total

    def save(self, *args, **kwargs):
        if not self.montant_total:
            self.calculer_total()
        super().save(*args, **kwargs)

    def confirmer(self):
        if self.statut_reservation == 'EN_ATTENTE':
            self.statut_reservation = 'CONFIRMEE'
            self.save()
            return True
        return False

    def annuler(self):
        if self.statut_reservation in ['EN_ATTENTE', 'CONFIRMEE']:
            self.statut_reservation = 'ANNULEE'
            self.vehicule.statut = 'DISPONIBLE'
            self.vehicule.save()
            self.save()
            return True
        return False

    def demarrer(self):
        if self.statut_reservation == 'CONFIRMEE':
            self.statut_reservation = 'EN_COURS'
            self.vehicule.statut = 'INDISPONIBLE'
            self.vehicule.save()
            self.save()
            return True
        return False

    def terminer(self):
        if self.statut_reservation == 'EN_COURS':
            self.statut_reservation = 'TERMINEE'
            self.vehicule.statut = 'DISPONIBLE'
            self.vehicule.save()
            self.save()
            return True
        return False

    def prolonger(self, nouvelle_date_fin):
        """Extend rental."""
        if self.statut_reservation in ['CONFIRMEE', 'EN_COURS']:
            old_fin = self.date_fin
            self.date_fin = nouvelle_date_fin
            self.calculer_total()
            self.save()
            return True
        return False


class Contrat(models.Model):
    """Rental contract PDF."""
    STATUT_CHOICES = [
        ('GENERE', _('Généré')),
        ('SIGNE', _('Signé')),
        ('ANNULE', _('Annulé')),
    ]

    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE,
                                       related_name='contrat')
    date_generation = models.DateTimeField(_('Date de génération'), auto_now_add=True)
    fichier_pdf = models.FileField(_('Fichier PDF'), upload_to='contrats/', blank=True)
    statut_signature = models.CharField(_('Statut signature'), max_length=20,
                                      choices=STATUT_CHOICES, default='GENERE')
    signature_client = models.ImageField(_('Signature client'), upload_to='signatures/', blank=True)

    class Meta:
        verbose_name = _('Contrat')
        verbose_name_plural = _('Contrats')

    def __str__(self):
        return f"Contrat {self.id} - Réservation {self.reservation.id}"

    def signer(self, signature_image=None):
        self.statut_signature = 'SIGNE'
        if signature_image:
            self.signature_client = signature_image
        self.save()


class Livraison(models.Model):
    """Vehicle delivery/recovery."""
    STATUT_CHOICES = [
        ('PLANIFIEE', _('Planifiée')),
        ('EN_COURS', _('En cours')),
        ('TERMINEE', _('Terminée')),
        ('ECHEC', _('Échec')),
    ]

    TYPE_CHOICES = [
        ('LIVRAISON', _('Livraison')),
        ('RECUPERATION', _('Récupération')),
    ]

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE,
                                   related_name='livraisons')
    livreur = models.ForeignKey('accounts.Utilisateur', on_delete=models.SET_NULL,
                               null=True, limit_choices_to={'role': 'LIVREUR'},
                               related_name='livraisons')
    type = models.CharField(_('Type'), max_length=20, choices=TYPE_CHOICES, default='LIVRAISON')
    date_livraison = models.DateField(_('Date'))
    heure_livraison = models.TimeField(_('Heure'))
    lieu_livraison = models.CharField(_('Lieu'), max_length=255)
    statut = models.CharField(_('Statut'), max_length=20, choices=STATUT_CHOICES, default='PLANIFIEE')
    motif_echec = models.TextField(_("Motif d'échec"), blank=True)
    kilometrage_depart = models.IntegerField(_('Kilométrage départ'), null=True, blank=True)
    kilometrage_retour = models.IntegerField(_('Kilométrage retour'), null=True, blank=True)

    class Meta:
        verbose_name = _('Livraison')
        verbose_name_plural = _('Livraisons')
        ordering = ['-date_livraison']

    def __str__(self):
        return f"Livraison {self.id} - {self.reservation}"


class Paiement(models.Model):
    """Payment for a reservation."""
    MODE_CHOICES = [
        ('CARTE_BANCAIRE', _('Carte bancaire')),
        ('ESPECES', _('Espèces')),
        ('VIREMENT', _('Virement')),
        ('PAYPAL', _('PayPal')),
    ]

    STATUT_CHOICES = [
        ('EN_ATTENTE', _('En attente')),
        ('COMPLETE', _('Complète')),
        ('ECHEC', _('Échec')),
        ('REMBOURSE', _('Remboursé')),
    ]

    TYPE_CHOICES = [
        ('ACOMPTE', _('Acompte')),
        ('TOTAL', _('Paiement total')),
        ('CAUTION', _('Caution')),
        ('REMBOURSEMENT', _('Remboursement')),
    ]

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE,
                                  related_name='paiements')
    type = models.CharField(_('Type'), max_length=20, choices=TYPE_CHOICES, default='TOTAL')
    amount = models.DecimalField(_('Montant (MAD)'), max_digits=10, decimal_places=2)
    mode = models.CharField(_('Mode de paiement'), max_length=20, choices=MODE_CHOICES)
    statut = models.CharField(_('Statut'), max_length=20, choices=STATUT_CHOICES, default='EN_ATTENTE')
    transaction_id = models.CharField(_('ID Transaction'), max_length=100, blank=True)
    date_paiement = models.DateTimeField(_('Date de paiement'), auto_now_add=True)

    class Meta:
        verbose_name = _('Paiement')
        verbose_name_plural = _('Paiements')
        ordering = ['-date_paiement']

    def __str__(self):
        return f"Paiement {self.id} - {self.reservation} - {self.amount} MAD"

    def confirmer(self):
        if self.statut == 'EN_ATTENTE':
            self.statut = 'COMPLETE'
            self.save()
            return True
        return False


class Facture(models.Model):
    """Invoice for a reservation."""
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE,
                                      related_name='facture')
    date_facture = models.DateTimeField(_('Date de facture'), auto_now_add=True)
    montant_ht = models.DecimalField(_('Montant HT (MAD)'), max_digits=10, decimal_places=2)
    tva = models.DecimalField(_('TVA (%)'), max_digits=5, decimal_places=2, default=20.0)
    montant_ttc = models.DecimalField(_('Montant TTC (MAD)'), max_digits=10, decimal_places=2)
    fichier_pdf = models.FileField(_('Fichier PDF'), upload_to='factures/', blank=True)

    class Meta:
        verbose_name = _('Facture')
        verbose_name_plural = _('Factures')

    def __str__(self):
        return f"Facture {self.id} - Réservation {self.reservation.id}"

    def save(self, *args, **kwargs):
        self.montant_ht = self.reservation.montant_total
        self.montant_ttc = self.montant_ht * (1 + self.tva / 100)
        super().save(*args, **kwargs)


class Avis(models.Model):
    """Client review for a vehicle."""
    client = models.ForeignKey('accounts.Utilisateur', on_delete=models.CASCADE,
                             related_name='avis', limit_choices_to={'role': 'CLIENT'})
    vehicule = models.ForeignKey('vehicles.Vehicule', on_delete=models.CASCADE,
                                related_name='avis')
    note = models.IntegerField(_('Note'), validators=[MinValueValidator(1), MaxValueValidator(5)])
    commentaire = models.TextField(_('Commentaire'), blank=True)
    date = models.DateTimeField(_('Date'), auto_now_add=True)

    class Meta:
        verbose_name = _('Avis')
        verbose_name_plural = _('Avis')
        ordering = ['-date']
        unique_together = ('client', 'vehicule')

    def __str__(self):
        return f"Avis {self.client} - {self.vehicule} - {self.note}/5"


class EtatDesLieux(models.Model):
    """Vehicle inspection at pickup and return."""
    TYPE_CHOICES = [
        ('ENTREE', _('Entrée')),
        ('SORTIE', _('Sortie')),
    ]

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE,
                                  related_name='etats_des_lieux')
    type = models.CharField(_('Type'), max_length=20, choices=TYPE_CHOICES)
    date = models.DateTimeField(_('Date'), auto_now_add=True)
    employe = models.ForeignKey('accounts.Utilisateur', on_delete=models.SET_NULL, null=True,
                               limit_choices_to={'role': 'EMPLOYE'},
                               related_name='etats_des_lieux')
    kilometrage = models.IntegerField(_('Kilométrage'))
    niveau_carburant = models.IntegerField(_('Niveau de carburant (%)'),
                                         validators=[MinValueValidator(0), MaxValueValidator(100)],
                                         default=100)
    commentaire = models.TextField(_('Commentaire'), blank=True)
    photos = models.ImageField(_('Photos'), upload_to='etat_des_lieux/', blank=True)
    signature_client = models.ImageField(_('Signature client'), upload_to='signatures/', blank=True)

    class Meta:
        verbose_name = _('État des lieux')
        verbose_name_plural = _('États des lieux')
        ordering = ['-date']

    def __str__(self):
        return f"État des lieux {self.get_type_display()} - Réservation {self.reservation.id}"
