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
            success_url=request.build_absolute_uri(f'/payments/success/?reservation_id={reservation.id}'),
            cancel_url=request.build_absolute_uri(f'/payments/cancel/?reservation_id={reservation.id}'),
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
    """Payment successful page - redirect to reservation detail."""
    reservation_id = request.GET.get('reservation_id')
    if reservation_id:
        # Clear session data
        if 'pending_reservation_id' in request.session:
            del request.session['pending_reservation_id']
        if 'reservation_data' in request.session:
            del request.session['reservation_data']
        if 'contract_signed' in request.session:
            del request.session['contract_signed']
        if 'signature_name' in request.session:
            del request.session['signature_name']

        return redirect('reservations:reservation_detail', pk=reservation_id)
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
        metadata = session.get('metadata', {})
        reservation_id = metadata.get('reservation_id')

        from apps.reservations.models import Paiement, Reservation
        if reservation_id:
            paiement = Paiement.objects.filter(
                stripe_payment_intent_id=payment_intent_id,
                reservation_id=reservation_id
            ).first()
        else:
            paiement = Paiement.objects.filter(
                stripe_payment_intent_id=payment_intent_id
            ).first()

        if paiement and paiement.statut != 'COMPLETE':
            paiement.statut = 'COMPLETE'
            paiement.stripe_charge_id = payment_intent_id
            paiement.save()

            reservation = paiement.reservation
            reservation.confirmer()

            # Mark vehicle as unavailable
            vehicule = reservation.vehicule
            vehicule.statut = 'INDISPONIBLE'
            vehicule.save(update_fields=['statut'])

    return HttpResponse(status=200)