from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import (Reservation, Slot, Contrat, Livraison, Paiement,
                     Facture, Avis,EtatDesLieux)
from .forms import (ReservationForm, SlotForm, LivraisonForm, PaiementForm,
                    AvisForm,EtatDesLieuxForm)
from apps.vehicles.models import Vehicule
from apps.accounts.models import Utilisateur


# ==================== CLIENT VIEWS ====================

@login_required
def reservation_create(request, vehicle_id):
    """Show reservation form and redirect to payment confirmation."""
    vehicule = get_object_or_404(Vehicule, pk=vehicle_id)

    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            # Store form data in session and redirect to contract signing
            request.session['reservation_data'] = {
                'vehicule_id': vehicle_id,
                'date_debut': str(form.cleaned_data['date_debut']),
                'date_fin': str(form.cleaned_data['date_fin']),
                'lieu_depart': form.cleaned_data['lieu_depart'],
                'lieu_retour': form.cleaned_data['lieu_retour'],
                'latitude_depart': str(form.cleaned_data.get('latitude_depart', '')),
                'longitude_depart': str(form.cleaned_data.get('longitude_depart', '')),
                'latitude_retour': str(form.cleaned_data.get('latitude_retour', '')),
                'longitude_retour': str(form.cleaned_data.get('longitude_retour', '')),
            }
            return redirect('reservations:contract_sign', vehicle_id=vehicle_id)
    else:
        form = ReservationForm(initial={'vehicule': vehicule})
    return render(request, 'reservations/reservation_form.html',
                  {'form': form, 'vehicule': vehicule})


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
    nombre_jours = (date_fin - date_debut).days

    from decimal import Decimal
    montant_total = Decimal(nombre_jours) * vehicule.prix_journalier

    context = {
        'vehicule': vehicule,
        'date_debut': data['date_debut'],
        'date_fin': data['date_fin'],
        'lieu_depart': data['lieu_depart'],
        'lieu_retour': data['lieu_retour'],
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
    nombre_jours = (date_fin - date_debut).days

    from decimal import Decimal
    montant_total = Decimal(nombre_jours) * vehicule.prix_journalier

    context = {
        'vehicule': vehicule,
        'date_debut': data['date_debut'],
        'date_fin': data['date_fin'],
        'lieu_depart': data['lieu_depart'],
        'lieu_retour': data['lieu_retour'],
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
        payment_method = request.POST.get('payment_method', 'CARTE_BANCAIRE')

        from datetime import date
        from apps.reservations.models import Reservation, Paiement, Contrat, Facture

        from decimal import Decimal as D
        from django.conf import settings

        reservation = Reservation.objects.create(
            client=request.user,
            vehicule=vehicule,
            date_debut=date.fromisoformat(data['date_debut']),
            date_fin=date.fromisoformat(data['date_fin']),
            lieu_depart=data['lieu_depart'],
            lieu_retour=data['lieu_retour'],
            latitude_depart=data.get('latitude_depart') and D(data['latitude_depart']) or None,
            longitude_depart=data.get('longitude_depart') and D(data['longitude_depart']) or None,
            latitude_retour=data.get('latitude_retour') and D(data['latitude_retour']) or None,
            longitude_retour=data.get('longitude_retour') and D(data['longitude_retour']) or None,
            statut_reservation='CONFIRMEE',
        )
        reservation.calculer_total()
        reservation.save()

        # Create payment record
        Paiement.objects.create(
            reservation=reservation,
            type='ACOMPTE',
            amount=reservation.montant_total,
            mode=payment_method,
            statut='COMPLETE' if payment_method == 'CARTE_BANCAIRE' else 'EN_ATTENTE'
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
            montant_ht=reservation.montant_total,
            montant_ttc=reservation.montant_total * D('1.20')
        )

        # Create automatic Livraison for the reservation
        from datetime import datetime as dt
        from datetime import time as t
        from apps.accounts.models import Utilisateur

        # Auto-assign to first available livreur
        available_livreur = Utilisateur.objects.filter(role='LIVREUR', actif=True).first()

        Livraison.objects.create(
            reservation=reservation,
            livreur=available_livreur,
            type='LIVRAISON',
            date_livraison=reservation.date_debut,
            heure_livraison=t(9, 0),  # Default 9:00 AM
            lieu_livraison=reservation.lieu_depart,
            latitude=reservation.latitude_depart,
            longitude=reservation.longitude_depart,
            statut='EN_ATTENTE' if not available_livreur else 'EN_ATTENTE',
        )

        # Notify admin
        from apps.accounts.models import Utilisateur, Notification
        admins = Utilisateur.objects.filter(role='ADMIN')
        for admin in admins:
            Notification.objects.create(
                utilisateur=admin,
                type='RESERVATION',
                titre='Nouvelle Réservation Confirmée',
                message=f'Réservation #{reservation.id} - {request.user} a réservé {vehicule.marque} {vehicule.modele}. Montant: {reservation.montant_total} MAD.'
            )

        # Notify the assigned livreur
        if available_livreur:
            Notification.objects.create(
                utilisateur=available_livreur,
                type='RESERVATION',
                titre='Livraison Assignée',
                message=f'Une nouvelle livraison vous a été assignée! Réservation #{reservation.id}. Client: {request.user}, Lieu: {data["lieu_depart"]}.'
            )

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


# ==================== LIVREUR ACTIONS ====================

@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_livreur())
def livraison_accept(request, pk):
    """Livreur accepts a delivery."""
    livraison = get_object_or_404(Livraison, pk=pk)
    if livraison.livreur == request.user or request.user.is_admin():
        livraison.statut = 'EN_COURS'
        livraison.save()
        messages.success(request, 'Livraison acceptée!')
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
        messages.success(request, 'Livraison terminée!')
    return redirect('reservations:livraison_list')


@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_livreur())
def livraison_returned(request, pk):
    """Mark vehicle as returned."""
    livraison = get_object_or_404(Livraison, pk=pk)
    if livraison.livreur == request.user or request.user.is_admin():
        livraison.statut = 'TERMINEE'
        livraison.kilometrage_retour = request.POST.get('kilometrage')
        livraison.save()
        messages.success(request, 'Véhicule retourné!')
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
