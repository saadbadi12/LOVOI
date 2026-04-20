from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings

# Stripe is optional - only import if available
try:
    import stripe
    stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False


@login_required
def payment_page(request, reservation_id):
    """Payment page for a reservation."""
    from apps.reservations.models import Reservation
    reservation = Reservation.objects.get(pk=reservation_id)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        amount = request.POST.get('amount')

        # In production, integrate with Stripe/PayPal
        # For now, simulate success
        messages.success(request, 'Paiement traité avec succès!')
        return redirect('reservations:reservation_detail', pk=reservation_id)

    context = {
        'reservation': reservation,
        'stripe_pub_key': getattr(settings, 'STRIPE_PUBLISHABLE_KEY', ''),
        'stripe_available': STRIPE_AVAILABLE,
    }
    return render(request, 'payments/payment_page.html', context)


@login_required
def payment_success(request):
    return render(request, 'payments/success.html')


@login_required
def payment_cancel(request):
    return render(request, 'payments/cancel.html')
