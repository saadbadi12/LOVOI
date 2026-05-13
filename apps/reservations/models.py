from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta


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
    DELIVERY_CHOICES = [
        ('RETRAIT_AGENCE', _("Retrait a l'agence")),
        ('LIVRAISON_DOMICILE', _('Livraison a domicile')),
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
    latitude_depart = models.DecimalField(_('Latitude départ'), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude_depart = models.DecimalField(_('Longitude départ'), max_digits=9, decimal_places=6, null=True, blank=True)
    latitude_retour = models.DecimalField(_('Latitude retour'), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude_retour = models.DecimalField(_('Longitude retour'), max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_option = models.CharField(_('Option de livraison'), max_length=30, choices=DELIVERY_CHOICES, default='RETRAIT_AGENCE')
    delivery_address = models.CharField(_('Adresse de livraison'), max_length=255, blank=True)
    delivery_distance_km = models.DecimalField(_('Distance livraison (km)'), max_digits=8, decimal_places=2, default=Decimal('0.00'))
    delivery_fee = models.DecimalField(_('Frais de livraison (MAD)'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    price_per_km = models.DecimalField(_('Tarif livraison par km (MAD)'), max_digits=6, decimal_places=2, default=Decimal('5.00'))
    statut_reservation = models.CharField(_('Statut'), max_length=20,
                                         choices=STATUT_CHOICES, default='EN_ATTENTE')
    montant_total = models.DecimalField(_('Montant total (MAD)'), max_digits=10,
                                       decimal_places=2, null=True, blank=True)
    caution_versee = models.BooleanField(_('Caution versée'), default=False)
    nombre_jours = models.IntegerField(_('Nombre de jours'), default=1)
    reference = models.IntegerField(_('Référence client'), default=0)

    class Meta:
        verbose_name = _('Réservation')
        verbose_name_plural = _('Réservations')
        ordering = ['-date_reservation']

    def __str__(self):
        return f"Réservation {self.reference} - {self.client} - {self.vehicule}"

    @property
    def facture(self):
        return self.factures.filter(type='LOCATION').order_by('date_facture').first()

    def has_overlap(self):
        if not self.vehicule_id or not self.date_debut or not self.date_fin:
            return False

        reservations = Reservation.objects.filter(
            vehicule=self.vehicule,
            statut_reservation__in=['EN_ATTENTE', 'CONFIRMEE', 'EN_COURS'],
            date_debut__lt=self.date_fin,
            date_fin__gt=self.date_debut,
        )

        if self.pk:
            reservations = reservations.exclude(pk=self.pk)

        return reservations.exists()

    def clean(self):
        super().clean()

        if self.date_debut and self.date_fin:
            if self.date_fin <= self.date_debut:
                raise ValidationError({
                    'date_fin': _("La date de fin doit être après la date de début.")
                })

            if self.statut_reservation in ['EN_ATTENTE', 'CONFIRMEE', 'EN_COURS'] and self.has_overlap():
                raise ValidationError(
                    _("Ce véhicule est déjà réservé sur cette période.")
                )

        if self.delivery_option == 'LIVRAISON_DOMICILE' and not self.delivery_address:
            raise ValidationError({
                'delivery_address': _("Veuillez saisir une adresse de livraison.")
            })

    def calculer_total(self):
        from decimal import Decimal
        if self.date_debut and self.date_fin and self.vehicule:
            jours = max((self.date_fin - self.date_debut).days, 1)
            self.nombre_jours = jours
            location_total = Decimal(jours) * self.vehicule.prix_journalier * Decimal("1.20")
            delivery_fee = self.delivery_fee if self.delivery_option == 'LIVRAISON_DOMICILE' else Decimal('0.00')
            self.montant_total = (location_total + delivery_fee).quantize(Decimal("0.01"))
        return self.montant_total

    def save(self, *args, **kwargs):

        if not self.reference:

            last = Reservation.objects.filter(client=self.client).order_by('-reference').first()
            self.reference = (last.reference + 1) if last and last.reference else 1

        self.calculer_total()
        self.full_clean()

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
            if isinstance(nouvelle_date_fin, str):
                nouvelle_date_fin = date.fromisoformat(nouvelle_date_fin)
            self.date_fin = nouvelle_date_fin
            self.calculer_total()
            self.save()
            return True
        return False


class DemandeProlongation(models.Model):
    """Client request to extend a reservation."""
    STATUS = [
        ('EN_ATTENTE', _('En attente')),
        ('ACCEPTEE', _('Acceptée')),
        ('REFUSEE', _('Refusée')),
    ]

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE,
                                    related_name='demandes_prolongation')
    nouvelle_date_fin = models.DateField(_('Nouvelle date de fin'))
    statut = models.CharField(_('Statut'), max_length=20, choices=STATUS, default='EN_ATTENTE')
    motif_refus = models.TextField(_('Motif de refus'), null=True, blank=True)
    created_at = models.DateTimeField(_('Créée le'), auto_now_add=True)

    class Meta:
        verbose_name = _('Demande de prolongation')
        verbose_name_plural = _('Demandes de prolongation')
        ordering = ['-created_at']

    def __str__(self):
        return f"DemandeProlongation {self.id} - Réservation {self.reservation.id} - {self.get_statut_display()}"

class Contrat(models.Model):
    """Rental contract PDF."""
    STATUT_CHOICES = [
        ('NON_SIGNE', _('Non signé')),
        ('SIGNE', _('Signé')),
        ('ANNULE', _('Annulé')),
    ]

    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE,
                                       related_name='contrat')
    date_generation = models.DateTimeField(_('Date de génération'), auto_now_add=True)
    fichier_pdf = models.FileField(_('Fichier PDF'), upload_to='contrats/', blank=True)
    statut_signature = models.CharField(_('Statut signature'), max_length=20,
                                      choices=STATUT_CHOICES, default='NON_SIGNE')
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
        ('EN_ATTENTE', _('En attente')),
        ('EN_COURS', _('En cours')),
        ('TERMINEE', _('Terminée')),
        ('ECHEC', _('Échec')),
    ]

    TYPE_CHOICES = [
        ('LIVRAISON', _('Livraison')),
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
    latitude = models.DecimalField(_('Latitude'), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(_('Longitude'), max_digits=9, decimal_places=6, null=True, blank=True)
    statut = models.CharField(_('Statut'), max_length=20, choices=STATUT_CHOICES, default='EN_ATTENTE')
    motif_echec = models.TextField(_("Motif d'échec"), blank=True)
    kilometrage_depart = models.IntegerField(_('Kilométrage départ'), null=True, blank=True)
    kilometrage_retour = models.IntegerField(_('Kilométrage retour'), null=True, blank=True)

    class Meta:
        verbose_name = _('Livraison')
        verbose_name_plural = _('Livraisons')
        ordering = ['-date_livraison']

    def __str__(self):
        return f"Livraison {self.id} - {self.reservation}"

    def trigger_refund(self):
        """When livraison fails, automatically refund the client."""
        if self.statut == 'ECHEC' and self.motif_echec:
            Paiement.objects.create(
                reservation=self.reservation,
                type='REMBOURSEMENT',
                amount=self.reservation.montant_total,
                mode='CARTE_BANCAIRE',
                statut='COMPLETE',
                transaction_id=f'REFUND-LIVraison-{self.id}'
            )


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
        ('FRAIS_SUPPLEMENTAIRES', _('Frais supplémentaires')),
    ]

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE,
                                  related_name='paiements')
    type = models.CharField(_('Type'), max_length=30, choices=TYPE_CHOICES, default='TOTAL')
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
    TYPE_CHOICES = [
        ('LOCATION', _('Location')),
        ('PROLONGEMENT', _('Prolongement')),
        ('FRAIS_SUPPLEMENTAIRES', _('Frais supplémentaires')),
    ]

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE,
                                      related_name='factures')
    paiement = models.ForeignKey(Paiement, on_delete=models.SET_NULL, null=True,
                                related_name='facture')
    type = models.CharField(_('Type'), max_length=30, choices=TYPE_CHOICES, default='LOCATION')
    description = models.CharField(_('Description'), max_length=255, blank=True)
    date_facture = models.DateTimeField(_('Date de facture'), auto_now_add=True)
    montant_ht = models.DecimalField(_('Montant HT (MAD)'), max_digits=10, decimal_places=2)
    tva = models.DecimalField(_('TVA (%)'), max_digits=5, decimal_places=2, default=20.0)
    montant_ttc = models.DecimalField(_('Montant TTC (MAD)'), max_digits=10, decimal_places=2)
    montant_tva = models.DecimalField(_('Montant TVA (MAD)'), max_digits=10, decimal_places=2, default=0)
    fichier_pdf = models.FileField(_('Fichier PDF'), upload_to='factures/', blank=True)

    class Meta:
        verbose_name = _('Facture')
        verbose_name_plural = _('Factures')

    def __str__(self):
        if self.type == 'PROLONGEMENT':
            return f"Facture de prolongement - Réservation {self.reservation.id}"
        return f"Facture {self.id} - Réservation {self.reservation.id}"

    def save(self, *args, **kwargs):
        montant_source = self.montant_ttc or (self.reservation.montant_total if self.reservation else None)

        if montant_source:
            self.montant_ttc = montant_source.quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            self.montant_ht = (self.montant_ttc / Decimal("1.20")).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            self.montant_tva = (self.montant_ttc - self.montant_ht).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

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
    niveau_carburant = models.CharField(_('Niveau de carburant'), max_length=20,
                                       choices=[
                                           ('VIDE', _('Vide')),
                                           ('QUART', _('Quart')),
                                           ('MOITIE', _('Moitié')),
                                           ('TROIS_QUARTS', _('Trois quarts')),
                                           ('PLEIN', _('Plein')),
                                       ], default='PLEIN')
    commentaire = models.TextField(_('Commentaire'), blank=True)
    photos = models.ImageField(_('Photos'), upload_to='etat_des_lieux/', blank=True)
    signature_client = models.ImageField(_('Signature client'), upload_to='signatures/', blank=True)

    class Meta:
        verbose_name = _('État des lieux')
        verbose_name_plural = _('États des lieux')
        ordering = ['-date']

    def __str__(self):
        return f"État des lieux {self.get_type_display()} - Réservation {self.reservation.id}"


class Stat(models.Model):
    """Statistics for vehicles (occupation rate, revenue per month)."""
    vehicule = models.ForeignKey('vehicles.Vehicule', on_delete=models.CASCADE,
                                related_name='stats')
    month = models.IntegerField(_('Mois'))
    year = models.IntegerField(_('Année'))
    reservation_count = models.IntegerField(_('Nombre de réservations'), default=0)
    revenue = models.DecimalField(_('Revenus (MAD)'), max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = _('Statistique')
        verbose_name_plural = _('Statistiques')
        unique_together = ('vehicule', 'month', 'year')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"Stats {self.vehicule} - {self.month}/{self.year}"
