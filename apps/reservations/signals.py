"""
Signals for reservations app - creates notifications on key events.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Reservation


@receiver(post_save, sender=Reservation)
def reservation_notification(sender, instance, created, **kwargs):
    """Create notifications when reservation status changes."""
    from apps.accounts.models import Notification, Utilisateur

    if created:
        # New reservation created - notify admins
        admins = Utilisateur.objects.filter(role=Utilisateur.ROLE_ADMIN)
        for admin in admins:
            Notification.objects.create(
                utilisateur=admin,
                type='RESERVATION',
                titre=f'Nouvelle réservation #{instance.id}',
                message=f'Une nouvelle réservation a été créée par {instance.client.get_full_name()} '
                        f'pour le véhicule {instance.vehicule}.'
            )
    else:
        # Status change
        if instance.statut_reservation == 'CONFIRMEE':
            Notification.objects.create(
                utilisateur=instance.client,
                type='RESERVATION',
                titre=f'Réservation #{instance.id} confirmée',
                message=f'Votre réservation pour {instance.vehicule} a été confirmée.'
            )
        elif instance.statut_reservation == 'ANNULEE':
            Notification.objects.create(
                utilisateur=instance.client,
                type='RESERVATION',
                titre=f'Réservation #{instance.id} annulée',
                message=f'Votre réservation pour {instance.vehicule} a été annulée.'
            )
        elif instance.statut_reservation == 'EN_COURS':
            Notification.objects.create(
                utilisateur=instance.client,
                type='RESERVATION',
                titre=f'Location #{instance.id} démarrée',
                message=f'Votre location pour {instance.vehicule} a commencé. '
                        f'Bonne route!'
            )
        elif instance.statut_reservation == 'TERMINEE':
            Notification.objects.create(
                utilisateur=instance.client,
                type='RESERVATION',
                titre=f'Location #{instance.id} terminée',
                message=f'Votre location pour {instance.vehicule} est terminée. '
                        f'Merci de retourner le véhicule.'
            )
