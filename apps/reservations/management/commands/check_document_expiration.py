"""
Management command to check for expiring vehicle documents.
Schedule daily via cron:
    0 8 * * * cd /path/to/LOVOI_2 && python manage.py check_document_expiration --days=30
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.vehicles.models import Document
from apps.accounts.models import Notification, Utilisateur


class Command(BaseCommand):
    help = 'Check for expiring vehicle documents and send alerts to admins'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days before expiration to send alert',
        )

    def handle(self, *args, **options):
        days = options['days']
        threshold = timezone.now().date() + timedelta(days=days)

        # Find documents expiring within threshold
        expiring_docs = Document.objects.filter(
            date_expiration__lte=threshold,
            date_expiration__gte=timezone.now().date(),
            alert_envoyee=False
        ).select_related('vehicule')

        admins = Utilisateur.objects.filter(role=Utilisateur.ROLE_ADMIN)
        count = 0

        for doc in expiring_docs:
            for admin in admins:
                Notification.objects.create(
                    utilisateur=admin,
                    type='DOCUMENT',
                    titre=f'Document expirant - {doc.vehicule}',
                    message=f'Le document {doc.get_type_display()} du véhicule '
                            f'{doc.vehicule} expire le {doc.date_expiration}. '
                            f'Veuilleez le renouvel er.'
                )

            doc.alert_envoyee = True
            doc.save()
            count += 1

            self.stdout.write(
                self.style.WARNING(
                    f'[ALERT] {doc.vehicule} - {doc.get_type_display()} '
                    f'expires {doc.date_expiration}'
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f'Sent {count} document expiration alerts to {admins.count()} admins')
        )
