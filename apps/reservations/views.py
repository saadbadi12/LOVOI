from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from .models import (Reservation, Slot, Contrat, Livraison, Paiement,
                     Facture, Avis,EtatDesLieux, DemandeProlongation)
from .forms import (ReservationForm, SlotForm, LivraisonForm, PaiementForm,
                    AvisForm,EtatDesLieuxForm, DemandeProlongationForm)
from .utils import (AGENCY_ADDRESS, AGENCY_LATITUDE, AGENCY_LONGITUDE,
                    DELIVERY_PRICE_PER_KM, calculate_delivery_quote)
from apps.vehicles.models import Vehicule
from apps.accounts.models import Utilisateur, Notification
import sys     


# ==================== CLIENT VIEWS ====================

def conditions_location(request):
    """Simple public rental conditions page."""
    return render(request, 'reservations/conditions_location.html')


@login_required
def reservation_create(request, vehicle_id):
    """Show reservation form and redirect to payment confirmation."""
    print(f"=== reservation_create called with vehicle_id={vehicle_id}, method={request.method} ===")
    vehicule = get_object_or_404(Vehicule, pk=vehicle_id)

    if request.method == 'POST':
        print(f"=== reservation_create POST with vehicle_id={vehicle_id} ===")
        form = ReservationForm(request.POST)
        if form.is_valid():
            delivery_option = form.cleaned_data.get('delivery_option') or 'RETRAIT_AGENCE'
            delivery_address = form.cleaned_data.get('delivery_address') or ''
            delivery_distance_km = Decimal('0.00')
            delivery_fee = Decimal('0.00')
            agency_latitude = str(AGENCY_LATITUDE)
            agency_longitude = str(AGENCY_LONGITUDE)
            lieu_depart = AGENCY_ADDRESS
            lieu_retour = AGENCY_ADDRESS
            latitude_depart = agency_latitude
            longitude_depart = agency_longitude
            latitude_retour = agency_latitude
            longitude_retour = agency_longitude

            if delivery_option == 'LIVRAISON_DOMICILE':
                try:
                    delivery_latitude = request.POST.get('delivery_latitude') or ''
                    delivery_longitude = request.POST.get('delivery_longitude') or ''
                    quote = calculate_delivery_quote(
                        address=delivery_address,
                        latitude=delivery_latitude,
                        longitude=delivery_longitude,
                    )
                    delivery_distance_km = quote['distance_km']
                    delivery_fee = quote['fee']
                    lieu_depart = delivery_address
                    latitude_depart = delivery_latitude
                    longitude_depart = delivery_longitude
                except Exception as exc:
                    messages.error(request, f"Impossible de calculer les frais de livraison: {exc}")
                    return redirect('reservations:reservation_create', vehicle_id=vehicle_id)

            # Store form data in session and redirect to contract signing
            request.session['reservation_data'] = {
                'vehicule_id': vehicle_id,
                'date_debut': str(form.cleaned_data['date_debut']),
                'date_fin': str(form.cleaned_data['date_fin']),
                'lieu_depart': lieu_depart,
                'lieu_retour': lieu_retour,
                'latitude_depart': latitude_depart,
                'longitude_depart': longitude_depart,
                'latitude_retour': latitude_retour,
                'longitude_retour': longitude_retour,
                'delivery_option': delivery_option,
                'delivery_address': delivery_address,
                'delivery_distance_km': str(delivery_distance_km),
                'delivery_fee': str(delivery_fee),
                'price_per_km': str(DELIVERY_PRICE_PER_KM),
            }
            return redirect('reservations:contract_sign', vehicle_id=vehicle_id)

        print(f"Form errors: {form.errors}", file=sys.stderr)

        for error in form.non_field_errors():
            messages.error(request, error)

        for field in form:
            for error in field.errors:
                messages.error(request, error)
    else:
        form = ReservationForm(initial={'vehicule': vehicule})

    from datetime import date
    return render(request, 'reservations/reservation_form.html',
                  {
                      'form': form,
                      'vehicule': vehicule,
                      'today': date.today().isoformat(),
                      'agency_address': AGENCY_ADDRESS,
                      'agency_latitude': AGENCY_LATITUDE,
                      'agency_longitude': AGENCY_LONGITUDE,
                  })


@login_required
def contract_sign(request, vehicle_id):
    """Show contract for signature before payment."""
    vehicule = get_object_or_404(Vehicule, pk=vehicle_id)

    if 'reservation_data' not in request.session:
        messages.error(request, 'Session expirée. Veuillez recommencer.')
        return redirect('reservations:reservation_create', vehicle_id=vehicle_id)

    data = request.session['reservation_data']
    from datetime import date
    date_debut = date.fromisoformat(data['date_debut'])
    date_fin = date.fromisoformat(data['date_fin'])
    nombre_jours = max((date_fin - date_debut).days, 1)

    from decimal import Decimal
    montant_ht = Decimal(nombre_jours) * vehicule.prix_journalier
    delivery_fee = Decimal(data.get('delivery_fee') or '0.00')
    montant_total = (montant_ht * Decimal("1.20") + delivery_fee).quantize(Decimal("0.01"))

    context = {
        'vehicule': vehicule,
        'date_debut': data['date_debut'],
        'date_fin': data['date_fin'],
        'lieu_depart': data['lieu_depart'],
        'lieu_retour': data['lieu_retour'],
        'delivery_option': data.get('delivery_option', 'RETRAIT_AGENCE'),
        'delivery_address': data.get('delivery_address', ''),
        'delivery_distance_km': data.get('delivery_distance_km', '0.00'),
        'delivery_fee': delivery_fee,
        'nombre_jours': nombre_jours,
        'montant_total': montant_total,
    }
    return render(request, 'reservations/contract_sign.html', context)


@login_required
def contract_sign_process(request, vehicle_id):
    """Process contract signature and redirect to payment."""
    vehicule = get_object_or_404(Vehicule, pk=vehicle_id)

    if 'reservation_data' not in request.session:
        messages.error(request, 'Session expirée. Veuillez recommencer.')
        return redirect('reservations:reservation_create', vehicle_id=vehicle_id)

    if request.method == 'POST':
        signature_name = request.POST.get('signature_name')
        payment_method = request.POST.get('payment_method')

        if signature_name:
            request.session['contract_signed'] = True
            request.session['signature_name'] = signature_name

            # If payment is already submitted via modal, go directly to process_payment
            if payment_method:
                return redirect('reservations:process_payment', vehicle_id=vehicle_id)

            return redirect('reservations:reservation_payment', vehicle_id=vehicle_id)

    return redirect('reservations:contract_sign', vehicle_id=vehicle_id)


@login_required
def reservation_payment(request, vehicle_id):
    """Show payment confirmation page before creating reservation."""
    vehicule = get_object_or_404(Vehicule, pk=vehicle_id)

    if 'reservation_data' not in request.session:
        messages.error(request, 'Session expirée. Veuillez recommencer.')
        return redirect('reservations:reservation_create', vehicle_id=vehicle_id)

    if 'contract_signed' not in request.session:
        return redirect('reservations:contract_sign', vehicle_id=vehicle_id)

    data = request.session['reservation_data']
    from datetime import date
    date_debut = date.fromisoformat(data['date_debut'])
    date_fin = date.fromisoformat(data['date_fin'])
    nombre_jours = max((date_fin - date_debut).days, 1)

    from decimal import Decimal
    montant_ht = Decimal(nombre_jours) * vehicule.prix_journalier
    delivery_fee = Decimal(data.get('delivery_fee') or '0.00')
    montant_total = (montant_ht * Decimal("1.20") + delivery_fee).quantize(Decimal("0.01"))

    context = {
        'vehicule': vehicule,
        'date_debut': data['date_debut'],
        'date_fin': data['date_fin'],
        'lieu_depart': data['lieu_depart'],
        'lieu_retour': data['lieu_retour'],
        'delivery_option': data.get('delivery_option', 'RETRAIT_AGENCE'),
        'delivery_address': data.get('delivery_address', ''),
        'delivery_distance_km': data.get('delivery_distance_km', '0.00'),
        'delivery_fee': delivery_fee,
        'nombre_jours': nombre_jours,
        'montant_total': montant_total,
        'signature_name': request.session.get('signature_name', ''),
    }
    return render(request, 'reservations/reservation_payment.html', context)


@login_required
def process_payment(request, vehicle_id):
    """Process payment and create reservation."""
    vehicule = get_object_or_404(Vehicule, pk=vehicle_id)

    if 'reservation_data' not in request.session:
        messages.error(request, 'Session expirée. Veuillez recommencer.')
        return redirect('reservations:reservation_create', vehicle_id=vehicle_id)

    if 'contract_signed' not in request.session:
        # Set it now since user is coming from payment modal
        request.session['contract_signed'] = True

    if request.method == 'POST':
        data = request.session['reservation_data']
        payment_method = 'CARTE_BANCAIRE'

        from datetime import date
        from decimal import Decimal as D

        def _parse_decimal(val):
            if not val or val in ('', 'None', 'null', 'undefined'):
                return None
            try:
                return D(str(val).strip())
            except:
                return None

        reservation = Reservation(
            client=request.user,
            vehicule=vehicule,
            date_debut=date.fromisoformat(data['date_debut']),
            date_fin=date.fromisoformat(data['date_fin']),
            lieu_depart=data['lieu_depart'],
            lieu_retour=data['lieu_retour'],
            latitude_depart=_parse_decimal(data.get('latitude_depart')),
            longitude_depart=_parse_decimal(data.get('longitude_depart')),
            latitude_retour=_parse_decimal(data.get('latitude_retour')),
            longitude_retour=_parse_decimal(data.get('longitude_retour')),
            delivery_option=data.get('delivery_option', 'RETRAIT_AGENCE'),
            delivery_address=data.get('delivery_address', ''),
            delivery_distance_km=_parse_decimal(data.get('delivery_distance_km')) or D('0.00'),
            delivery_fee=_parse_decimal(data.get('delivery_fee')) or D('0.00'),
            price_per_km=_parse_decimal(data.get('price_per_km')) or D('5.00'),
            statut_reservation='CONFIRMEE',
        )

        try:
            with transaction.atomic():
                reservation.full_clean()
                reservation.save()

                vehicule.statut = 'INDISPONIBLE'
                vehicule.save(update_fields=['statut'])
        except ValidationError as exc:
            for message in exc.messages:
                messages.error(request, message)
            return redirect('reservations:reservation_payment', vehicle_id=vehicle_id)

        # Create payment record
        Paiement.objects.create(
            reservation=reservation,
            type='ACOMPTE',
            amount=reservation.montant_total,
            mode=payment_method,
            statut='COMPLETE'
        )

        # Create contract with signature
        Contrat.objects.create(
            reservation=reservation,
            statut_signature='SIGNE',
            signature_client=request.session.get('signature_name', '')
        )

        # Create invoice
        Facture.objects.create(
            reservation=reservation,
            paiement=Paiement.objects.filter(reservation=reservation).first(),
            type='LOCATION',
            description=f'Facture de location - Réservation #{reservation.id}',
            montant_ht=Decimal('0.00'),
            montant_ttc=reservation.montant_total
        )

        # Livraison will be assigned by admin from the dashboard (no auto-assign here)

        # Notify admin
        admins = Utilisateur.objects.filter(role='ADMIN')
        for admin in admins:
            Notification.objects.create(
                utilisateur=admin,
                type='RESERVATION',
                titre='Nouvelle Réservation Confirmée',
                message=f'Réservation #{reservation.id} - {request.user} a réservé {vehicule.marque} {vehicule.modele}. Montant: {reservation.montant_total} MAD.'
            )

        # (No automatic notification to a livreur since assignment is manual)

        # Clear session
        if 'reservation_data' in request.session:
            del request.session['reservation_data']
        if 'contract_signed' in request.session:
            del request.session['contract_signed']
        if 'signature_name' in request.session:
            del request.session['signature_name']

        messages.success(request, 'Réservation confirmée! Merci pour votre confiance.')
        return redirect('reservations:reservation_detail', pk=reservation.id)

    return redirect('reservations:reservation_payment', vehicle_id=vehicle_id)


@login_required
def reservation_detail(request, pk):
    """Reservation detail."""
    reservation = get_object_or_404(Reservation, pk=pk)
    is_assigned_livreur = (
        request.user.is_livreur()
        and reservation.livraisons.filter(livreur=request.user).exists()
    )
    # Only client who made it, admin, or assigned livreur can view
    if reservation.client != request.user and not request.user.is_admin() and not is_assigned_livreur:
        messages.error(request, 'Accès non autorisé.')
        if request.user.is_livreur():
            return redirect('accounts:dashboard_livreur')
        return redirect('accounts:dashboard_client')
    return render(request, 'reservations/reservation_detail.html',
                  {'reservation': reservation, 'today': timezone.localdate()})


@login_required
def my_reservations(request):
    """Client's reservation history."""
    reservations = Reservation.objects.filter(client=request.user).order_by('-date_reservation')
    paginator = Paginator(reservations, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'reservations/my_reservations.html', {'page_obj': page_obj})


@login_required
def avis_create(request, vehicle_id):
    """Leave a review for a vehicle."""
    vehicule = get_object_or_404(Vehicule, pk=vehicle_id)

    # Check if client has completed a rental for this vehicle
    has_rental = Reservation.objects.filter(
        client=request.user, vehicule=vehicule, statut_reservation='TERMINEE'
    ).exists()

    if not has_rental:
        messages.error(request, "Vous devez avoir loué ce véhicule pour laisser un avis.")
        return redirect('vehicles:vehicle_detail', pk=vehicule.id)

    if request.method == 'POST':
        form = AvisForm(request.POST)
        if form.is_valid():
            avis = form.save(commit=False)
            avis.client = request.user
            avis.vehicule = vehicule
            avis.save()
            messages.success(request, 'Avis publié!')
            return redirect('vehicles:vehicle_detail', pk=vehicule.id)
    else:
        form = AvisForm()
    return render(request, 'reservations/avis_form.html', {'form': form, 'vehicule': vehicule})


# ==================== ADMIN VIEWS ====================

@login_required
@user_passes_test(lambda u: u.is_admin())
def reservation_list(request):
    """List all reservations (admin)."""
    reservations = Reservation.objects.all().order_by('-date_reservation')

    statut = request.GET.get('statut')
    if statut:
        reservations = reservations.filter(statut_reservation=statut)

    paginator = Paginator(reservations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'reservations/reservation_list_admin.html', {'page_obj': page_obj})


@login_required
@user_passes_test(lambda u: u.is_admin())
def reservation_confirm(request, pk):
    """Confirm a reservation."""
    reservation = get_object_or_404(Reservation, pk=pk)
    if reservation.confirmer():
        messages.success(request, 'Réservation confirmée!')
    else:
        messages.error(request, 'Impossible de confirmer cette réservation.')
    return redirect('reservations:reservation_list')


@login_required
@user_passes_test(lambda u: u.is_admin())
def reservation_cancel(request, pk):
    """Cancel a reservation."""
    reservation = get_object_or_404(Reservation, pk=pk)
    if reservation.annuler():
        messages.success(request, 'Réservation annulée!')
    else:
        messages.error(request, 'Impossible d\'annuler cette réservation.')
    return redirect('reservations:reservation_list')


@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_employe())
def reservation_start(request, pk):
    """Start a rental (EN_COURS)."""
    reservation = get_object_or_404(Reservation, pk=pk)
    if reservation.demarrer():
        messages.success(request, 'Location démarrée!')
    else:
        messages.error(request, 'Impossible de démarrer cette location.')
    return redirect('reservations:reservation_detail', pk=pk)


@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_employe())
def reservation_end(request, pk):
    """End a rental (TERMINEE)."""
    reservation = get_object_or_404(Reservation, pk=pk)
    if reservation.terminer():
        messages.success(request, 'Location terminée!')
    else:
        messages.error(request, 'Impossible de terminer cette location.')
    return redirect('reservations:reservation_detail', pk=pk)


@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_client())
def extend_reservation(request, pk):
    """Prepare extension payment for an active rental."""
    reservation = get_object_or_404(Reservation, pk=pk)

    if request.user.is_client() and reservation.client != request.user:
        messages.error(request, 'Accès non autorisé.')
        return redirect('reservations:reservation_detail', pk=pk)

    if reservation.statut_reservation != 'EN_COURS' or reservation.vehicule.statut == 'DISPONIBLE':
        messages.error(request, 'La prolongation est possible uniquement pendant une location en cours.')
        return redirect('reservations:reservation_detail', pk=pk)

    if request.method != 'POST':
        return redirect('reservations:reservation_detail', pk=pk)

    nouvelle_date = request.POST.get('date_fin')
    try:
        nouvelle_date_fin = date.fromisoformat(nouvelle_date)
    except (TypeError, ValueError):
        messages.error(request, 'Veuillez choisir une date de fin valide.')
        return redirect('reservations:reservation_detail', pk=pk)

    if nouvelle_date_fin <= reservation.date_fin:
        messages.error(request, "La nouvelle date de fin doit être après l'ancienne date de fin.")
        return redirect('reservations:reservation_detail', pk=pk)

    overlapping = Reservation.objects.filter(
        vehicule=reservation.vehicule,
        statut_reservation__in=['EN_ATTENTE', 'CONFIRMEE', 'EN_COURS'],
        date_debut__lt=nouvelle_date_fin,
        date_fin__gt=reservation.date_fin,
    ).exclude(pk=reservation.pk).exists()

    if overlapping:
        messages.error(request, "Ce véhicule est déjà réservé après votre date de fin actuelle.")
        return redirect('reservations:reservation_detail', pk=pk)

    jours_supplementaires = (nouvelle_date_fin - reservation.date_fin).days
    supplement_ht = (Decimal(jours_supplementaires) * reservation.vehicule.prix_journalier).quantize(Decimal("0.01"))
    supplement_tva = (supplement_ht * Decimal("0.20")).quantize(Decimal("0.01"))
    supplement = (supplement_ht + supplement_tva).quantize(Decimal("0.01"))

    request.session['extension_data'] = {
        'reservation_id': reservation.id,
        'ancienne_date_fin': reservation.date_fin.isoformat(),
        'nouvelle_date_fin': nouvelle_date_fin.isoformat(),
        'jours_supplementaires': jours_supplementaires,
        'supplement_ht': str(supplement_ht),
        'supplement_tva': str(supplement_tva),
        'supplement': str(supplement),
    }

    return redirect('reservations:extension_payment', pk=reservation.pk)


@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_client())
def extension_payment(request, pk):
    """Pay and apply a reservation extension."""
    reservation = get_object_or_404(Reservation, pk=pk)

    if request.user.is_client() and reservation.client != request.user:
        messages.error(request, 'Accès non autorisé.')
        return redirect('reservations:reservation_detail', pk=pk)

    if reservation.statut_reservation != 'EN_COURS' or reservation.vehicule.statut == 'DISPONIBLE':
        messages.error(request, "La prolongation n'est plus disponible pour cette réservation.")
        request.session.pop('extension_data', None)
        return redirect('reservations:reservation_detail', pk=pk)

    extension_data = request.session.get('extension_data')
    if not extension_data or extension_data.get('reservation_id') != reservation.id:
        messages.error(request, 'Demande de prolongement expirée. Veuillez recommencer.')
        return redirect('reservations:reservation_detail', pk=pk)

    nouvelle_date_fin = date.fromisoformat(extension_data['nouvelle_date_fin'])
    ancienne_date_fin = date.fromisoformat(extension_data['ancienne_date_fin'])
    supplement_ht = Decimal(extension_data.get('supplement_ht', '0.00'))
    supplement_tva = Decimal(extension_data.get('supplement_tva', '0.00'))
    supplement = Decimal(extension_data['supplement'])
    jours_supplementaires = extension_data['jours_supplementaires']

    if request.method == 'POST':
        overlapping = Reservation.objects.filter(
            vehicule=reservation.vehicule,
            statut_reservation__in=['EN_ATTENTE', 'CONFIRMEE', 'EN_COURS'],
            date_debut__lt=nouvelle_date_fin,
            date_fin__gt=reservation.date_fin,
        ).exclude(pk=reservation.pk).exists()

        if overlapping or reservation.date_fin != ancienne_date_fin:
            messages.error(request, "La disponibilité a changé. Veuillez refaire la demande de prolongement.")
            request.session.pop('extension_data', None)
            return redirect('reservations:reservation_detail', pk=pk)

        with transaction.atomic():
            paiement = Paiement.objects.create(
                reservation=reservation,
                type='TOTAL',
                amount=supplement,
                mode='CARTE_BANCAIRE',
                statut='COMPLETE',
                transaction_id=f'EXT-{reservation.id}-{timezone.now().timestamp():.0f}'
            )

            nouveau_montant = (reservation.montant_total + supplement).quantize(Decimal("0.01"))
            nouveau_nombre_jours = max((nouvelle_date_fin - reservation.date_debut).days, 1)

            Reservation.objects.filter(pk=reservation.pk).update(
                date_fin=nouvelle_date_fin,
                montant_total=nouveau_montant,
                nombre_jours=nouveau_nombre_jours,
            )

            Facture.objects.create(
                reservation=reservation,
                paiement=paiement,
                type='PROLONGEMENT',
                description=f'Facture de prolongement - Réservation #{reservation.id}',
                montant_ht=Decimal('0.00'),
                montant_ttc=supplement,
            )

            Notification.objects.create(
                utilisateur=reservation.client,
                type='GENERAL',
                titre='Prolongement confirmé',
                message=(
                    f'Votre réservation #{reservation.id} est prolongée '
                    f"jusqu'au {nouvelle_date_fin}. Supplément payé: {supplement} MAD."
                )
            )

            admins = Utilisateur.objects.filter(role='ADMIN')
            for admin in admins:
                Notification.objects.create(
                    utilisateur=admin,
                    type='GENERAL',
                    titre='Prolongement payé',
                    message=(
                        f'Réservation #{reservation.id} prolongée jusqu\'au '
                        f'{nouvelle_date_fin}. Supplément: {supplement} MAD.'
                    )
                )

        request.session.pop('extension_data', None)
        messages.success(request, f'Prolongement payé et enregistré. Supplément: {supplement} MAD.')
        return redirect('reservations:reservation_detail', pk=pk)

    context = {
        'reservation': reservation,
        'ancienne_date_fin': ancienne_date_fin,
        'nouvelle_date_fin': nouvelle_date_fin,
        'jours_supplementaires': jours_supplementaires,
        'supplement_ht': supplement_ht,
        'supplement_tva': supplement_tva,
        'supplement': supplement,
    }
    return render(request, 'reservations/extension_payment.html', context)


# ==================== LIVREUR ACTIONS ====================

@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_livreur())
def livraison_accept(request, pk):
    """Livreur accepts a delivery."""
    livraison = get_object_or_404(Livraison, pk=pk)
    if livraison.livreur == request.user or request.user.is_admin():
        livraison.statut = 'EN_COURS'
        livraison.save()
        messages.success(request, 'Livraison acceptÃ©e!')
    return redirect('reservations:livraison_list')



@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_livreur())
def livraison_picked_up(request, pk):
    """Mark vehicle as picked up."""
    livraison = get_object_or_404(Livraison, pk=pk)
    if livraison.livreur == request.user or request.user.is_admin():
        livraison.statut = 'EN_COURS'
        livraison.kilometrage_depart = request.POST.get('kilometrage')
        livraison.save()
        messages.success(request, 'Véhicule récupéré!')
    return redirect('reservations:livraison_list')


@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_livreur())
def livraison_delivered(request, pk):
    """Mark vehicle as delivered."""
    livraison = get_object_or_404(Livraison, pk=pk)
    if livraison.livreur == request.user or request.user.is_admin():
        livraison.statut = 'TERMINEE'
        livraison.save()
        if livraison.reservation.statut_reservation == 'CONFIRMEE':
            reservation = livraison.reservation
            reservation.demarrer()
        messages.success(request, 'Livraison terminée!')
    return redirect('reservations:livraison_list')

# ==================== SLOTS ====================

@login_required
@user_passes_test(lambda u: u.is_admin())
def slot_list(request):
    slots = Slot.objects.all().order_by('localisation')
    return render(request, 'reservations/slot_list.html', {'slots': slots})


@login_required
@user_passes_test(lambda u: u.is_admin())
def slot_create(request):
    if request.method == 'POST':
        form = SlotForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Slot ajouté!')
            return redirect('reservations:slot_list')
    else:
        form = SlotForm()
    return render(request, 'reservations/slot_form.html', {'form': form})


# ==================== LIVRAISONS ====================

@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_livreur())
def livraison_list(request):
    livraisons = Livraison.objects.select_related(
        'reservation', 'reservation__client', 'livreur'
    )
    if request.user.is_livreur():
        livraisons = livraisons.filter(livreur=request.user)
    livraisons = livraisons.order_by('-date_livraison')
    return render(request, 'reservations/livraison_list.html', {'livraisons': livraisons})


@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_livreur())
def livraison_create(request, reservation_id=None):
    reservation = None
    if reservation_id:
        reservation = get_object_or_404(Reservation, pk=reservation_id)

    if request.user.is_livreur():
        # Livreur sees only reservations assigned to them via existing livraisons
        reservations = Reservation.objects.filter(
            statut_reservation__in=['CONFIRMEE', 'EN_COURS'],
            livraisons__livreur=request.user
        ).select_related('client', 'vehicule').distinct()
        livreurs = Utilisateur.objects.filter(id=request.user.id)
    else:
        # Admin sees all
        reservations = Reservation.objects.filter(
            statut_reservation__in=['CONFIRMEE', 'EN_COURS']
        ).select_related('client', 'vehicule')
        livreurs = Utilisateur.objects.filter(role=Utilisateur.ROLE_LIVREUR)

    # STRICT FIX: read reservation & livreur from POST and create Livraison accordingly
    if request.method == 'POST':
        reservation_id_post = request.POST.get('reservation')
        livreur_id_post = request.POST.get('livreur')

        if not reservation_id_post or not livreur_id_post:
            messages.error(request, 'Données manquantes. Veuillez sélectionner la réservation et le livreur.')
            return redirect('reservations:livraison_list')

        try:
            reservation_obj = get_object_or_404(Reservation, pk=int(reservation_id_post))
            livreur_obj = get_object_or_404(Utilisateur, pk=int(livreur_id_post))
        except Exception:
            messages.error(request, 'Réservation ou livreur invalide.')
            return redirect('reservations:livraison_list')

        if reservation_obj.date_debut != timezone.localdate():
            messages.error(request, "Le livreur peut être assigné uniquement le jour du départ.")
            return redirect('reservations:reservation_detail', pk=reservation_obj.id)

        # Prevent duplicate livraison for the same reservation
        if Livraison.objects.filter(reservation=reservation_obj).exists():
            messages.error(request, 'Une livraison existe déjà pour cette réservation.')
            return redirect('reservations:reservation_detail', pk=reservation_obj.id)

        from datetime import time
        from django.db import transaction

        try:
            with transaction.atomic():
                liv = Livraison.objects.create(
                    reservation=reservation_obj,
                    livreur=livreur_obj,
                    lieu_livraison=reservation_obj.lieu_depart,
                    date_livraison=reservation_obj.date_debut,
                    heure_livraison=time(9, 0),
                    statut='EN_ATTENTE'
                )
                Notification.objects.create(
                    utilisateur=livreur_obj,
                    type='RESERVATION',
                    titre='Livraison Assignee',
                    message=(
                        f'Une nouvelle livraison vous a ete assignee! '
                        f'Reservation #{reservation_obj.id}. '
                        f'Client: {reservation_obj.client.get_full_name() or reservation_obj.client.username}, '
                        f'Lieu: {liv.lieu_livraison}.'
                    )
                )
        except Exception as exc:
            messages.error(request, f'Erreur lors de la création de la livraison: {exc}')
            return redirect('reservations:reservation_detail', pk=reservation_obj.id)

        messages.success(request, 'Livreur assigné avec succès')
        return redirect('reservations:reservation_detail', pk=reservation_obj.id)

    # GET: render form as before
    form = LivraisonForm()
    return render(request, 'reservations/livraison_form.html',
                  {'form': form, 'reservations': reservations, 'livreurs': livreurs, 'reservation': reservation})


@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_livreur())
def livraison_update(request, pk):
    livraison = get_object_or_404(Livraison, pk=pk)
    old_statut = livraison.statut
    if request.method == 'POST':
        if request.user.is_livreur() and request.POST.get('demande_annulation') == '1':
            motif_annulation = request.POST.get('motif_annulation', '').strip()

            if not motif_annulation:
                messages.error(request, "Veuillez saisir un motif d'annulation.")
                return redirect('accounts:dashboard_livreur')

            admins = Utilisateur.objects.filter(
                Q(role='ADMIN') | Q(is_staff=True) | Q(is_superuser=True)
            ).distinct()
            for admin in admins:
                Notification.objects.create(
                    utilisateur=admin,
                    type='RESERVATION',
                    titre="Demande d'annulation livraison",
                    message=(
                        f"{request.user.get_full_name() or request.user.username} demande "
                        f"l'annulation de la livraison #{livraison.id} "
                        f"(réservation #{livraison.reservation.id}). "
                        f"Motif: {motif_annulation}"
                    )
                )

            messages.success(request, "Votre demande d'annulation a été envoyée à l'administrateur.")
            return redirect('accounts:dashboard_livreur')

        if request.POST.get('statut') == 'ECHEC':
            motif_echec = request.POST.get('motif_echec', '').strip()

            if not motif_echec:
                messages.error(request, "Veuillez saisir un motif d'annulation.")
                if request.user.is_livreur():
                    return redirect('accounts:dashboard_livreur')
                return redirect('reservations:livraison_list')

            livraison.statut = 'ECHEC'
            livraison.motif_echec = motif_echec
            livraison.save(update_fields=['statut', 'motif_echec'])

            if old_statut != 'ECHEC':
                livraison.trigger_refund()

            messages.warning(request, f'Échec enregistré. Un remboursement de {livraison.reservation.montant_total} MAD sera traité.')
            if request.user.is_livreur():
                return redirect('accounts:dashboard_livreur')
            return redirect('reservations:livraison_list')

        form = LivraisonForm(request.POST, instance=livraison)
        if form.is_valid():
            updated_livraison = form.save()
            # If statut changed to ECHEC and motif provided, trigger auto-refund
            if updated_livraison.statut == 'ECHEC' and old_statut != 'ECHEC' and updated_livraison.motif_echec:
                updated_livraison.trigger_refund()
                messages.warning(request, f'Échec enregistré. Un remboursement de {updated_livraison.reservation.montant_total} MAD sera traité.')
            else:
                messages.success(request, 'Livraison mise à jour!')
            return redirect('reservations:livraison_list')
    else:
        form = LivraisonForm(instance=livraison)
    return render(request, 'reservations/livraison_form.html', {'form': form, 'livraison': livraison})


# ==================== PAIEMENTS ====================

@login_required
@user_passes_test(lambda u: u.is_admin())
def paiement_list(request):
    paiements = Paiement.objects.all().order_by('-date_paiement')
    return render(request, 'reservations/paiement_list.html', {'paiements': paiements})


@login_required
@user_passes_test(lambda u: u.is_admin())
def paiement_demander_remboursement(request, pk):
    """Admin requests a refund for a payment."""
    paiement = get_object_or_404(Paiement, pk=pk)

    if request.method == 'POST':
        if paiement.demander_remboursement():
            messages.success(request, f'Demande de remboursement créée pour {paiement.amount} MAD.')
        else:
            messages.error(request, 'Impossible de demander un remboursement pour ce paiement.')
        return redirect('reservations:paiement_list')

    return render(request, 'reservations/paiement_confirm_refund.html', {'paiement': paiement})


@login_required
@user_passes_test(lambda u: u.is_admin())
def paiement_effectuer_remboursement(request, pk):
    """Admin processes (executes) the refund via Stripe."""
    paiement = get_object_or_404(Paiement, pk=pk)

    if request.method == 'POST':
        if paiement.statut != 'EN_ATTENTE_REMBOURSEMENT':
            messages.error(request, 'Ce paiement n\'est pas en attente de remboursement.')
            return redirect('reservations:paiement_list')

        if paiement.effectuer_remboursement():
            # Cancel the associated reservation
            if paiement.reservation.statut_reservation in ['CONFIRMEE', 'EN_ATTENTE']:
                paiement.reservation.annuler()

            messages.success(request, f'Remboursement de {paiement.amount} MAD effectué avec succès.')
        else:
            messages.error(request, 'Erreur lors du remboursement Stripe. Vérifiez les logs.')

        return redirect('reservations:paiement_list')

    return render(request, 'reservations/paiement_confirm_refund.html', {'paiement': paiement})


@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_client())
def paiement_create(request, reservation_id):
    reservation = get_object_or_404(Reservation, pk=reservation_id)
    if request.method == 'POST':
        form = PaiementForm(request.POST)
        if form.is_valid():
            paiement = form.save(commit=False)
            paiement.reservation = reservation
            paiement.confirmer()
            # Update reservation caution if needed
            if paiement.type == 'CAUTION':
                reservation.caution_versee = True
                reservation.save()
            messages.success(request, 'Paiement enregistré!')
            return redirect('reservations:reservation_detail', pk=reservation.id)
    else:
        form = PaiementForm(initial={'reservation': reservation, 'amount': reservation.montant_total})
    return render(request, 'reservations/paiement_form.html', {'form': form, 'reservation': reservation})


# ==================== ETAT DES LIEUX ====================

@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_employe())
def etat_des_lieux_create(request, reservation_id):
    reservation = get_object_or_404(Reservation, pk=reservation_id)
    default_type = request.GET.get('type')
    if default_type not in ['SORTIE', 'ENTREE']:
        default_type = 'ENTREE' if reservation.statut_reservation == 'EN_COURS' else 'SORTIE'
    if request.method == 'POST':
        form = EtatDesLieuxForm(request.POST, request.FILES)
        if form.is_valid():
            etat = form.save(commit=False)
            etat.reservation = reservation
            etat.type = default_type
            etat.employe = request.user
            etat.save()
            vehicule = reservation.vehicule
            if etat.kilometrage and etat.kilometrage > vehicule.kilometrage:
                vehicule.kilometrage = etat.kilometrage

            if etat.type == 'SORTIE':
                if reservation.delivery_option == 'RETRAIT_AGENCE' and reservation.statut_reservation == 'CONFIRMEE':
                    reservation.demarrer()
                    vehicule.refresh_from_db()
                elif reservation.delivery_option == 'LIVRAISON_DOMICILE' and reservation.statut_reservation == 'CONFIRMEE':
                    vehicule.statut = 'EN_LIVRAISON'
                    vehicule.save(update_fields=['statut', 'kilometrage'])
                else:
                    vehicule.save(update_fields=['kilometrage'])
            elif etat.type == 'ENTREE' and reservation.statut_reservation == 'EN_COURS':
                frais_supplementaires = Decimal('0.00')
                details_frais = []
                etat_depart = reservation.etats_des_lieux.filter(type='SORTIE').exclude(pk=etat.pk).order_by('-date').first()
                if etat_depart:
                    kilometres_parcourus = max(etat.kilometrage - etat_depart.kilometrage, 0)
                    kilometres_autorises = max(reservation.nombre_jours, 1) * 200
                    kilometres_supplementaires = max(kilometres_parcourus - kilometres_autorises, 0)
                    if kilometres_supplementaires:
                        frais_km = (Decimal(kilometres_supplementaires) * Decimal('5.00')).quantize(Decimal('0.01'))
                        frais_supplementaires += frais_km
                        details_frais.append(f'{kilometres_supplementaires} km supplémentaires: {frais_km} MAD')

                    carburant_rank = {
                        'VIDE': 0,
                        'QUART': 1,
                        'MOITIE': 2,
                        'TROIS_QUARTS': 3,
                        'PLEIN': 4,
                    }
                    if carburant_rank.get(etat.niveau_carburant, 0) < carburant_rank.get(etat_depart.niveau_carburant, 0):
                        details_frais.append('Niveau carburant inférieur au départ')

                if etat.commentaire:
                    details_frais.append('Commentaire/anomalie signalé par employé')

                if frais_supplementaires > 0:
                    Paiement.objects.create(
                        reservation=reservation,
                        type='FRAIS_SUPPLEMENTAIRES',
                        amount=frais_supplementaires,
                        mode='ESPECES',
                        statut='EN_ATTENTE',
                        transaction_id=f'EXTRA-{reservation.id}-{timezone.now().timestamp():.0f}',
                    )

                admins = Utilisateur.objects.filter(role='ADMIN')
                details_message = '; '.join(details_frais) if details_frais else 'Aucun frais supplémentaire détecté.'
                for admin in admins:
                    Notification.objects.create(
                        utilisateur=admin,
                        type='RESERVATION',
                        titre='Retour véhicule contrôlé',
                        message=(
                            f'Réservation #{reservation.id} contrôlée au retour par '
                            f'{request.user.get_full_name() or request.user.username}. '
                            f'Frais supplémentaires: {frais_supplementaires} MAD. '
                            f'Détails: {details_message}'
                        )
                    )

                reservation.terminer()
                vehicule.refresh_from_db()
                if etat.kilometrage and etat.kilometrage > vehicule.kilometrage:
                    vehicule.kilometrage = etat.kilometrage
                    vehicule.save(update_fields=['kilometrage'])
            messages.success(request, 'État des lieux enregistré!')
            return redirect('reservations:reservation_detail', pk=reservation.id)
    else:
        form = EtatDesLieuxForm(initial={'reservation': reservation})
    return render(request, 'reservations/etat_des_lieux_form.html',
                  {'form': form, 'reservation': reservation, 'default_type': default_type})


@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_employe())
def etat_des_lieux_list(request):
    etats = EtatDesLieux.objects.all().order_by('-date')
    return render(request, 'reservations/etat_des_lieux_list.html', {'etats': etats})


# ==================== PDF EXPORT ====================

@login_required
def contract_pdf(request, reservation_id):
    """Export contract as PDF."""
    reservation = get_object_or_404(Reservation, pk=reservation_id)
    if reservation.client != request.user and not request.user.is_admin():
        messages.error(request, 'Accès non autorisé.')
        return redirect('accounts:dashboard_client')

    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from io import BytesIO

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, spaceAfter=30, alignment=1)
    story.append(Paragraph("CONTRAT DE LOCATION", title_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph(f"<b>Réservation N°:</b> {reservation.id}", styles['Normal']))
    story.append(Paragraph(f"<b>Date:</b> {reservation.date_reservation.strftime('%d/%m/%Y à %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>LOCATAIRE:</b>", styles['Heading3']))
    story.append(Paragraph(f"{reservation.client.get_full_name() or reservation.client.username}", styles['Normal']))
    story.append(Paragraph(f"Email: {reservation.client.email}", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>Véhicule:</b>", styles['Heading3']))
    story.append(Paragraph(f"{reservation.vehicule.marque} {reservation.vehicule.modele}", styles['Normal']))
    story.append(Paragraph(f"Immatriculation: {reservation.vehicule.immatriculation}", styles['Normal']))
    story.append(Spacer(1, 15))

    data = [
        ['Date début', str(reservation.date_debut)],
        ['Date fin', str(reservation.date_fin)],
        ['Lieu de départ', reservation.lieu_depart],
        ['Lieu de retour', reservation.lieu_retour],
        ['Montant total', f"{reservation.montant_total} MAD"],
        ['Caution', f"{reservation.vehicule.caution} MAD"],
    ]
    t = Table(data, colWidths=[5*cm, 10*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.2, 0.2, 0.2)),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    story.append(t)
    story.append(Spacer(1, 30))

    if reservation.contrat and reservation.contrat.signature_client:
        story.append(Paragraph("<b>Signature du locataire:</b>", styles['Heading3']))
        story.append(Paragraph(f"{reservation.contrat.signature_client}", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=contrat_{reservation.id}.pdf'
    return response


@login_required
def facture_pdf(request, reservation_id):
    """Export invoice as PDF."""
    reservation = get_object_or_404(Reservation, pk=reservation_id)
    if reservation.client != request.user and not request.user.is_admin():
        messages.error(request, 'Accès non autorisé.')
        return redirect('accounts:dashboard_client')

    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from io import BytesIO

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, spaceAfter=30, alignment=1)
    story.append(Paragraph("FACTURE", title_style))
    story.append(Spacer(1, 20))

    if reservation.facture:
        story.append(Paragraph(f"<b>N° Facture:</b> {reservation.facture.id}", styles['Normal']))
        story.append(Paragraph(f"<b>Date:</b> {reservation.facture.date_facture.strftime('%d/%m/%Y')}", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>Client:</b>", styles['Heading3']))
    story.append(Paragraph(f"{reservation.client.get_full_name() or reservation.client.username}", styles['Normal']))
    story.append(Paragraph(f"Email: {reservation.client.email}", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>Véhicule:</b>", styles['Heading3']))
    story.append(Paragraph(f"{reservation.vehicule.marque} {reservation.vehicule.modele}", styles['Normal']))
    story.append(Spacer(1, 15))

    if reservation.facture:
        montant_ht = reservation.facture.montant_ht
        tva = float(montant_ht) * 0.20
        montant_ttc = reservation.facture.montant_ttc
    else:
        montant_ht = reservation.montant_total
        tva = float(montant_ht) * 0.20
        montant_ttc = float(montant_ht) * 1.20

    data = [
        ['Description', 'Montant (MAD)'],
        [f"Location {reservation.vehicule.marque} {reservation.vehicule.modele} ({reservation.nombre_jours} jour(s))", f"{montant_ht:.2f}"],
        ['TVA (20%)', f"{tva:.2f}"],
        ['TOTAL TTC', f"{montant_ttc:.2f}"],
    ]
    t = Table(data, colWidths=[10*cm, 5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.2)),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    story.append(t)

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=facture_{reservation.id}.pdf'
    return response


# ==================== AVAILABILITY CHECK ====================

def check_availability(request):
    """API endpoint to check vehicle availability."""
    vehicle_id = request.GET.get('vehicle_id')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')

    if not vehicle_id or not date_debut or not date_fin:
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    vehicule = get_object_or_404(Vehicule, pk=vehicle_id)

    from datetime import datetime
    try:
        debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
        fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    if fin <= debut:
        return JsonResponse({'available': False, 'reason': 'La date de fin doit être après la date de début'})

    # Check vehicle status
    if vehicule.statut != 'DISPONIBLE':
        return JsonResponse({'available': False, 'reason': 'Véhicule non disponible'})

    # Check for overlapping reservations
    overlapping = Reservation.objects.filter(
        vehicule=vehicule,
        statut_reservation__in=['EN_ATTENTE', 'CONFIRMEE', 'EN_COURS'],
        date_debut__lt=fin,
        date_fin__gt=debut
    ).exists()

    if overlapping:
        return JsonResponse({'available': False, 'reason': 'Véhicule déjà réservé pour ces dates'})

    # Calculate price
    jours = max((fin - debut).days, 1)
    total = jours * vehicule.prix_journalier

    return JsonResponse({
        'available': True,
        'days': jours,
        'daily_price': float(vehicule.prix_journalier),
        'total_price': float(total),
        'caution': float(vehicule.caution)
    })


@login_required
@require_http_methods(["GET"])
def delivery_quote(request):
    """AJAX endpoint returning delivery distance and fee."""
    address = request.GET.get('address', '').strip()
    latitude = request.GET.get('latitude')
    longitude = request.GET.get('longitude')

    try:
        quote = calculate_delivery_quote(address=address, latitude=latitude, longitude=longitude)
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    return JsonResponse({
        'ok': True,
        'distance_km': float(quote['distance_km']),
        'fee': float(quote['fee']),
        'price_per_km': float(quote['price_per_km']),
    })


@login_required
@user_passes_test(lambda u: u.is_admin())
def admin_prolongations(request):
    """Admin: list prolongation requests."""
    demandes = DemandeProlongation.objects.all().order_by('-created_at')
    statut = request.GET.get('statut')
    if statut:
        demandes = demandes.filter(statut=statut)
    return render(request, 'reservations/admin_prolongations.html', {'demandes': demandes})


@login_required
@user_passes_test(lambda u: u.is_admin())
def accepter_prolongation(request, pk):
    demande = get_object_or_404(DemandeProlongation, pk=pk)
    if request.method != 'POST':
        messages.error(request, 'Méthode non autorisée.')
        return redirect('reservations:admin_prolongations')

    with transaction.atomic():
        demande.statut = 'ACCEPTEE'
        demande.save()
        reservation = demande.reservation
        reservation.date_fin = demande.nouvelle_date_fin
        reservation.calculer_total()
        reservation.save()
        # Create a facture record for the prolongation if desired
        Facture.objects.create(
            reservation=reservation,
            type='PROLONGEMENT',
            description=f'Prolongation acceptée - Réservation #{reservation.id}',
            montant_ht=Decimal('0.00'),
            montant_ttc=Decimal('0.00'),
        )

    messages.success(request, 'Demande de prolongation acceptée et appliquée.')
    return redirect('reservations:admin_prolongations')


@login_required
@user_passes_test(lambda u: u.is_admin())
def refuser_prolongation(request, pk):
    demande = get_object_or_404(DemandeProlongation, pk=pk)
    if request.method != 'POST':
        messages.error(request, 'Méthode non autorisée.')
        return redirect('reservations:admin_prolongations')

    motif = request.POST.get('motif_refus', '').strip()
    demande.statut = 'REFUSEE'
    demande.motif_refus = motif
    demande.save()
    messages.success(request, 'Demande de prolongation refusée.')
    return redirect('reservations:admin_prolongations')


@login_required
def demander_prolongation(request, pk):
    """Client: submit a prolongation request."""
    reservation = get_object_or_404(Reservation, pk=pk)
    if not request.user.is_client() or reservation.client != request.user:
        messages.error(request, 'Accès non autorisé.')
        return redirect('reservations:reservation_detail', pk=pk)

    if reservation.statut_reservation != 'EN_COURS':
        messages.error(request, 'La prolongation est possible uniquement pendant une location en cours.')
        return redirect('reservations:reservation_detail', pk=pk)

    if request.method != 'POST':
        messages.error(request, 'Méthode non autorisée.')
        return redirect('reservations:reservation_detail', pk=pk)

    nouvelle_date = request.POST.get('nouvelle_date_fin')
    try:
        nouvelle_date_fin = date.fromisoformat(nouvelle_date)
    except (TypeError, ValueError):
        messages.error(request, 'Veuillez choisir une date de fin valide.')
        return redirect('reservations:reservation_detail', pk=pk)

    if nouvelle_date_fin <= reservation.date_fin:
        messages.error(request, 'La nouvelle date de fin doit être après l\'ancienne date de fin.')
        return redirect('reservations:reservation_detail', pk=pk)

    # Check overlapping
    overlapping = Reservation.objects.filter(
        vehicule=reservation.vehicule,
        statut_reservation__in=['EN_ATTENTE', 'CONFIRMEE', 'EN_COURS'],
        date_debut__lt=nouvelle_date_fin,
        date_fin__gt=reservation.date_fin,
    ).exclude(pk=reservation.pk).exists()

    if overlapping:
        messages.error(request, 'Ce véhicule est déjà réservé après votre date de fin actuelle.')
        return redirect('reservations:reservation_detail', pk=pk)

    DemandeProlongation.objects.create(
        reservation=reservation,
        nouvelle_date_fin=nouvelle_date_fin,
        statut='EN_ATTENTE'
    )

    # Notify admins
    admins = Utilisateur.objects.filter(role='ADMIN')
    for admin in admins:
        Notification.objects.create(
            utilisateur=admin,
            type='PROLONGATION',
            titre='Nouvelle demande de prolongation',
            message=f'Demande de prolongation pour la réservation #{reservation.id}.'
        )

    messages.success(request, 'Demande de prolongation envoyée. L\'administration vous tiendra informé.')
    return redirect('reservations:reservation_detail', pk=pk)
