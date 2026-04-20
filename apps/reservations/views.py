from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta
from .models import (Reservation, Slot, Contrat, Livraison, Paiement,
                     Facture, Avis,EtatDesLieux)
from .forms import (ReservationForm, SlotForm, LivraisonForm, PaiementForm,
                    AvisForm,EtatDesLieuxForm)
from apps.vehicles.models import Vehicule
from apps.accounts.models import Utilisateur


# ==================== CLIENT VIEWS ====================

@login_required
def reservation_create(request, vehicle_id):
    """Create a new reservation for a vehicle."""
    vehicule = get_object_or_404(Vehicule, pk=vehicle_id)

    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.client = request.user
            reservation.calculer_total()
            reservation.save()
            messages.success(request, 'Réservation créée! En attente de confirmation.')
            return redirect('reservations:reservation_detail', pk=reservation.id)
    else:
        form = ReservationForm(initial={'vehicule': vehicule})
    return render(request, 'reservations/reservation_form.html',
                  {'form': form, 'vehicule': vehicule})


@login_required
def reservation_detail(request, pk):
    """Reservation detail."""
    reservation = get_object_or_404(Reservation, pk=pk)
    # Only client who made it, or admin can view
    if reservation.client != request.user and not request.user.is_admin():
        messages.error(request, 'Accès non autorisé.')
        return redirect('accounts:dashboard_client')
    return render(request, 'reservations/reservation_detail.html',
                  {'reservation': reservation})


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
        messages.error(request, "Vous devez avoir loué ce véhicule pour leave un avis.")
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
@user_passes_test(lambda u: u.is_admin())
def extend_reservation(request, pk):
    """Extend a reservation."""
    reservation = get_object_or_404(Reservation, pk=pk)
    if request.method == 'POST':
        nouvelle_date = request.POST.get('date_fin')
        if nouvelle_date and reservation.prolonger(nouvelle_date):
            messages.success(request, 'Location prolongée!')
        else:
            messages.error(request, 'Impossible de prolonger.')
    return redirect('reservations:reservation_detail', pk=pk)


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
    livraisons = Livraison.objects.all().order_by('-date_livraison')
    return render(request, 'reservations/livraison_list.html', {'livraisons': livraisons})


@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_livreur())
def livraison_create(request):
    reservations = Reservation.objects.filter(
        statut_reservation__in=['CONFIRMEE', 'EN_COURS']
    ).select_related('client', 'vehicule')
    livreurs = Utilisateur.objects.filter(role=Utilisateur.ROLE_LIVREUR)
    if request.method == 'POST':
        form = LivraisonForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Livraison planifiée!')
            return redirect('reservations:livraison_list')
    else:
        form = LivraisonForm()
    return render(request, 'reservations/livraison_form.html',
                  {'form': form, 'reservations': reservations, 'livreurs': livreurs})


@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_livreur())
def livraison_update(request, pk):
    livraison = get_object_or_404(Livraison, pk=pk)
    if request.method == 'POST':
        form = LivraisonForm(request.POST, instance=livraison)
        if form.is_valid():
            form.save()
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
    from apps.accounts.models import Utilisateur
    employes = Utilisateur.objects.filter(role=Utilisateur.ROLE_EMPLOYE)
    if request.method == 'POST':
        form = EtatDesLieuxForm(request.POST, request.FILES)
        if form.is_valid():
            etat = form.save(commit=False)
            etat.save()
            messages.success(request, 'État des lieux enregistré!')
            return redirect('reservations:reservation_detail', pk=reservation.id)
    else:
        form = EtatDesLieuxForm(initial={'reservation': reservation, 'employe': request.user})
    return render(request, 'reservations/etat_des_lieux_form.html',
                  {'form': form, 'reservation': reservation, 'employes': employes})


@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_employe())
def etat_des_lieux_list(request):
    etats = EtatDesLieux.objects.all().order_by('-date')
    return render(request, 'reservations/etat_des_lieux_list.html', {'etats': etats})


# ==================== AVAILABILITY CHECK ====================

def check_availability(request):
    """API endpoint to check vehicle availability."""
    vehicle_id = request.GET.get('vehicle_id')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')

    if not vehicle_id or not date_debut or not date_fin:
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    vehicule = get_object_or_404(Vehicule, pk=vehicle_id)

    # Check vehicle status
    if vehicule.statut != 'DISPONIBLE':
        return JsonResponse({'available': False, 'reason': 'Véhicule non disponible'})

    # Check for overlapping reservations
    overlapping = Reservation.objects.filter(
        vehicule=vehicule,
        statut_reservation__in=['EN_ATTENTE', 'CONFIRMEE', 'EN_COURS'],
        date_debut__lte=date_fin,
        date_fin__gte=date_debut
    ).exists()

    if overlapping:
        return JsonResponse({'available': False, 'reason': 'Véhicule déjà réservé pour ces dates'})

    # Calculate price
    from datetime import datetime
    debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
    fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
    jours = max((fin - debut).days, 1)
    total = jours * vehicule.prix_journalier

    return JsonResponse({
        'available': True,
        'days': jours,
        'daily_price': float(vehicule.prix_journalier),
        'total_price': float(total),
        'caution': float(vehicule.caution)
    })
