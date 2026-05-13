from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0010_demandeprolongation'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='delivery_option',
            field=models.CharField(
                choices=[
                    ('RETRAIT_AGENCE', "Retrait a l'agence"),
                    ('LIVRAISON_DOMICILE', 'Livraison a domicile'),
                ],
                default='RETRAIT_AGENCE',
                max_length=30,
                verbose_name='Option de livraison',
            ),
        ),
        migrations.AddField(
            model_name='reservation',
            name='delivery_address',
            field=models.CharField(blank=True, max_length=255, verbose_name='Adresse de livraison'),
        ),
        migrations.AddField(
            model_name='reservation',
            name='delivery_distance_km',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                max_digits=8,
                verbose_name='Distance livraison (km)',
            ),
        ),
        migrations.AddField(
            model_name='reservation',
            name='delivery_fee',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                max_digits=10,
                verbose_name='Frais de livraison (MAD)',
            ),
        ),
        migrations.AddField(
            model_name='reservation',
            name='price_per_km',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('5.00'),
                max_digits=6,
                verbose_name='Tarif livraison par km (MAD)',
            ),
        ),
    ]
