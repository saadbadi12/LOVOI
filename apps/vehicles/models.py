from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from decimal import Decimal


class Categorie(models.Model):
    """Vehicle category (SUV, Economy, etc.)."""
    type = models.CharField(_('Type'), max_length=100, unique=True)
    description = models.TextField(_('Description'), blank=True)
    icon = models.CharField(_('Icône'), max_length=50, blank=True)

    class Meta:
        verbose_name = _('Catégorie')
        verbose_name_plural = _('Catégories')
        ordering = ['type']

    def __str__(self):
        return self.type


class Vehicule(models.Model):
    """Core vehicle model with full details."""
    STATUT_CHOICES = [
        ('DISPONIBLE', _('Disponible')),
        ('INDISPONIBLE', _('Indisponible')),
        ('MAINTENANCE_REQUISE', _('Maintenance requise')),
        ('EN_MAINTENANCE', _('En maintenance')),
        ('EN_LIVRAISON', _('En livraison')),
    ]

    CARBURANT_CHOICES = [
        ('ESSENCE', _('Essence')),
        ('DIESEL', _('Diesel')),
        ('ELECTRIQUE', _('Électrique')),
        ('HYBRIDE', _('Hybride')),
    ]

    TRANSMISSION_CHOICES = [
        ('MANUELLE', _('Manuelle')),
        ('AUTOMATIQUE', _('Automatique')),
    ]

    marque = models.CharField(_('Marque'), max_length=100)
    modele = models.CharField(_('Modèle'), max_length=100)
    annee = models.IntegerField(_('Année'), validators=[MinValueValidator(1990)])
    immatriculation = models.CharField(_('Immatriculation'), max_length=20, unique=True)
    carburant = models.CharField(_('Carburant'), max_length=20, choices=CARBURANT_CHOICES)
    transmission = models.CharField(_('Transmission'), max_length=20, choices=TRANSMISSION_CHOICES)
    places = models.IntegerField(_('Nombre de places'), validators=[MinValueValidator(1)])
    couleur = models.CharField(_('Couleur'), max_length=50, blank=True)
    prix_journalier = models.DecimalField(_('Prix journalier (MAD)'), max_digits=10, decimal_places=2,
                                          validators=[MinValueValidator(Decimal('0.01'))])
    caution = models.DecimalField(_('Caution (MAD)'), max_digits=10, decimal_places=2,
                                  validators=[MinValueValidator(Decimal('0.00'))])
    kilometrage = models.IntegerField(_('Kilométrage'), default=0)
    statut = models.CharField(_('Statut'), max_length=20, choices=STATUT_CHOICES, default='DISPONIBLE')
    categorie = models.ForeignKey(Categorie, on_delete=models.SET_NULL, null=True, related_name='vehicules')
    description = models.TextField(_('Description'), blank=True)
    photo = models.ImageField(_('Photo principale'), upload_to='vehicules/', blank=True)
    date_ajout = models.DateTimeField(_('Date d\'ajout'), auto_now_add=True)

    class Meta:
        verbose_name = _('Véhicule')
        verbose_name_plural = _('Véhicules')
        ordering = ['-date_ajout']

    def __str__(self):
        return f"{self.marque} {self.modele} ({self.immatriculation})"

    def is_available(self):
        return self.statut == 'DISPONIBLE'


class VehiculePhoto(models.Model):
    """Additional photos for a vehicle."""
    vehicule = models.ForeignKey(Vehicule, on_delete=models.CASCADE, related_name='photos')
    photo = models.ImageField(_('Photo'), upload_to='vehicules/')
    titre = models.CharField(_('Titre'), max_length=100, blank=True)

    class Meta:
        verbose_name = _('Photo du véhicule')
        verbose_name_plural = _('Photos des véhicules')


class Maintenance(models.Model):
    """Vehicle maintenance records."""
    STATUT_CHOICES = [
        ('MAINTENANCE_REQUISE', _('Maintenance requise')),
        ('EN_MAINTENANCE', _('En maintenance')),
        ('TERMINEE', _('Terminée')),
    ]

    TYPE_CHOICES = [
        ('PREVENTIVE', _('Préventive')),
        ('CORRECTIVE', _('Corrective')),
        ('REVISION', _('Révision')),
    ]

    vehicule = models.ForeignKey(Vehicule, on_delete=models.CASCADE, related_name='maintenances')
    type = models.CharField(_('Type'), max_length=20, choices=TYPE_CHOICES)
    date_prevue = models.DateField(_('Date prévue'))
    date_realisee = models.DateField(_('Date réalisée'), null=True, blank=True)
    kilometrage = models.IntegerField(_('Kilométrage'), null=True, blank=True)
    cout = models.DecimalField(_('Coût (MAD)'), max_digits=10, decimal_places=2, null=True, blank=True)
    statut = models.CharField(_('Statut'), max_length=20, choices=STATUT_CHOICES, default='MAINTENANCE_REQUISE')
    description = models.TextField(_('Description'), blank=True)
    technicien = models.ForeignKey('accounts.Utilisateur', on_delete=models.SET_NULL, null=True, blank=True,
                                  limit_choices_to={'role': 'TECHNICIEN'})

    class Meta:
        verbose_name = _('Maintenance')
        verbose_name_plural = _('Maintenances')
        ordering = ['-date_prevue']

    def __str__(self):
        return f"{self.vehicule} - {self.get_type_display()} ({self.date_prevue})"

    def save(self, *args, **kwargs):
        if self.statut == 'TERMINEE' and self.date_realisee is None:
            from django.utils import timezone
            self.date_realisee = timezone.now().date()
        super().save(*args, **kwargs)


class Document(models.Model):
    """Legal vehicle documents."""
    TYPE_CHOICES = [
        ('ASSURANCE', _('Assurance')),
        ('CARTE_GRISE', _('Carte grise')),
        ('VISITE_TECHNIQUE', _('Visite technique')),
    ]

    vehicule = models.ForeignKey(Vehicule, on_delete=models.CASCADE, related_name='documents')
    type = models.CharField(_('Type'), max_length=50, choices=TYPE_CHOICES)
    numero = models.CharField(_('Numéro'), max_length=100)
    date_emission = models.DateField(_('Date d\'émission'), null=True, blank=True)
    date_expiration = models.DateField(_("Date d'expiration"))
    document = models.FileField(_('Document'), upload_to='documents/', blank=True)
    alert_envoyee = models.BooleanField(_('Alerte envoyée'), default=False)

    class Meta:
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')
        ordering = ['date_expiration']

    def __str__(self):
        return f"{self.vehicule} - {self.get_type_display()}"

    def is_expired(self):
        from django.utils import timezone
        return self.date_expiration < timezone.now().date()

    def expires_soon(self, days=30):
        from django.utils import timezone
        from datetime import timedelta
        return self.date_expiration <= timezone.now().date() + timedelta(days=days)
