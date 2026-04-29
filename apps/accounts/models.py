from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class Utilisateur(AbstractUser):
    """Parent model for all users."""
    telephone = models.CharField(_('Téléphone'), max_length=20, blank=True)
    adresse = models.TextField(_('Adresse'), blank=True)
    permis_numero = models.CharField(_('Numéro de permis'), max_length=50, blank=True)
    permis_date = models.DateField(_('Date de délivrance du permis'), null=True, blank=True)
    date_inscription = models.DateField(_("Date d'inscription"), auto_now_add=True)
    photo = models.ImageField(_('Photo'), upload_to='profiles/', blank=True)

    # Role constants
    ROLE_CLIENT = 'CLIENT'
    ROLE_ADMIN = 'ADMIN'
    ROLE_EMPLOYE = 'EMPLOYE'
    ROLE_TECHNICIEN = 'TECHNICIEN'
    ROLE_LIVREUR = 'LIVREUR'

    ROLE_CHOICES = [
        (ROLE_CLIENT, _('Client')),
        (ROLE_ADMIN, _('Administrateur')),
        (ROLE_EMPLOYE, _('Employé')),
        (ROLE_TECHNICIEN, _('Technicien')),
        (ROLE_LIVREUR, _('Livreur')),
    ]

    role = models.CharField(_('Rôle'), max_length=20, choices=ROLE_CHOICES, default=ROLE_CLIENT)
    actif = models.BooleanField(_('Actif'), default=True)

    # Common extra fields for all roles
    poste = models.CharField(_('Poste'), max_length=100, blank=True, default='')
    specialite = models.CharField(_('Spécialité'), max_length=100, blank=True, default='')

    # Client-specific fields
    cin = models.CharField(_('CIN'), max_length=20, blank=True)
    permis_conduire = models.CharField(_('Permis de conduire'), max_length=30, blank=True)
    date_naissance = models.DateField(_('Date de naissance'), null=True, blank=True)
    nb_locations = models.IntegerField(_('Nombre de locations'), default=0)

    # Admin-specific field
    niveau_acces = models.CharField(_('Niveau d\'accès'), max_length=20,
                                   choices=[('SUPER_ADMIN', _('Super Administrateur')),
                                           ('ADMIN', _('Administrateur'))],
                                   default='ADMIN')

    # Employee-specific field
    matricule = models.CharField(_('Matricule'), max_length=20, blank=True)

    # Technician-specific field
    certifications = models.TextField(_('Certifications'), blank=True)

    # Livreur-specific fields
    zone_couverte = models.CharField(_('Zone couverte'), max_length=100, blank=True)
    vehicule_service = models.CharField(_('Véhicule de service'), max_length=50, blank=True)

    class Meta:
        verbose_name = _('Utilisateur')
        verbose_name_plural = _('Utilisateurs')

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def is_client(self):
        return self.role == self.ROLE_CLIENT

    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    def is_employe(self):
        return self.role == self.ROLE_EMPLOYE

    def is_technicien(self):
        return self.role == self.ROLE_TECHNICIEN

    def is_livreur(self):
        return self.role == self.ROLE_LIVREUR


class Client(Utilisateur):
    """Proxy model for Client."""
    class Meta:
        proxy = True
        verbose_name = _('Client')
        verbose_name_plural = _('Clients')

    def signer_contrat(self):
        pass


class Admin(Utilisateur):
    """Proxy model for Administrator."""
    class Meta:
        proxy = True
        verbose_name = _('Administrateur')

    def gerer_documents(self):
        pass


class Employe(Utilisateur):
    """Proxy model for Employee."""
    class Meta:
        proxy = True
        verbose_name = _('Employé')
        verbose_name_plural = _('Employés')


class Technicien(Utilisateur):
    """Proxy model for Technician."""
    class Meta:
        proxy = True
        verbose_name = _('Technicien')
        verbose_name_plural = _('Techniciens')


class Livreur(Utilisateur):
    """Proxy model for Delivery driver."""
    class Meta:
        proxy = True
        verbose_name = _('Livreur')
        verbose_name_plural = _('Livreurs')


class Notification(models.Model):
    """Notifications for users."""
    TYPE_CHOICES = [
        ('RESERVATION', _('Réservation')),
        ('PAIEMENT', _('Paiement')),
        ('MAINTENANCE', _('Maintenance')),
        ('DOCUMENT', _('Document')),
        ('GENERAL', _('Général')),
    ]

    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(_('Type'), max_length=20, choices=TYPE_CHOICES)
    titre = models.CharField(_('Titre'), max_length=200)
    message = models.TextField(_('Message'))
    date_envoi = models.DateTimeField(_("Date d'envoi"), auto_now_add=True)
    lue = models.BooleanField(_('Lue'), default=False)

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-date_envoi']

    def __str__(self):
        return f"{self.titre} - {self.utilisateur}"
