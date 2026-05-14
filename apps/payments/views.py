from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.conf import settings
import stripe
import json


@login_required
def payment_page(request, reservation_id):
    """Payment page - creates Stripe Checkout Session."""
    from apps.reservations.models import Reservation

    reservation = get_object_or_404(Reservation, pk=reservation_id)

    if request.method == 'POST':
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'mad',
                    'unit_amount': int(float(reservation.montant_total) * 100),  # convert to cents
                    'product_data': {
                        'name': f'Réservation #{reservation.reference} - {reservation.vehicule.marque} {reservation.vehicule.modele}',
                        'description': f'Location du {reservation.date_debut} au {reservation.date_fin}',
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.build_absolute_uri('/payments/success/'),
            cancel_url=request.build_absolute_uri('/payments/cancel/'),
            metadata={
                'reservation_id': reservation.id,
                'user_id': request.user.id,
            }
        )

        # Create Paiement in EN_ATTENTE status
        from apps.reservations.models import Paiement
        Paiement.objects.create(
            reservation=reservation,
            type='TOTAL',
            amount=reservation.montant_total,
            mode='CARTE_BANCAIRE',
            statut='EN_ATTENTE',
            stripe_payment_intent_id=checkout_session.payment_intent,
        )

        return redirect(checkout_session.url, code=303)

    context = {
        'reservation': reservation,
        'stripe_pub_key': getattr(settings, 'STRIPE_PUBLISHABLE_KEY', ''),
        'stripe_available': True,
    }
    return render(request, 'payments/payment_page.html', context)


@login_required
def payment_success(request):
    """Payment successful page."""
    return render(request, 'payments/success.html')


@login_required
def payment_cancel(request):
    """Payment cancelled page."""
    return render(request, 'payments/cancel.html')


@csrf_exempt
def stripe_webhook(request):
    """
    Webhook to confirm payment after Stripe Checkout completes.
    Updates Paiement and Reservation status.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        payment_intent_id = session.get('payment_intent')

        from apps.reservations.models import Paiement
        paiement = Paiement.objects.filter(
            stripe_payment_intent_id=payment_intent_id
        ).first()

        if paiement:
            paiement.statut = 'COMPLETE'
            paiement.stripe_charge_id = payment_intent_id
            paiement.save()

            reservation = paiement.reservation
            reservation.confirmer()

    return HttpResponse(status=200)