from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from .models import Utilisateur, Notification
from .forms import ClientRegistrationForm, ProfileForm
from apps.vehicles.models import Vehicule, Categorie
from apps.reservations.models import Reservation, Livraison, EtatDesLieux


def home(request):
    """Home page with vehicle catalog preview."""
    categories = Categorie.objects.all()
    vehicules = Vehicule.objects.filter(statut='DISPONIBLE').order_by('-id')[:6]
    context = {
        'categories': categories,
        'vehicules': vehicules,
    }
    return render(request, 'accounts/home.html', context)


def register_client(request):
    """Client registration."""
    if request.method == 'POST':
        form = ClientRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            if Utilisateur.objects.filter(username=username).exists():
                messages.error(request, f'Le nom d\'utilisateur "{username}" est déjà pris. Veuillez en choisir un autre.')
                return render(request, 'accounts/register.html', {'form': form})
            try:
                user = form.save()
                # Ensure telephone from the registration form is persisted.
                # Some code paths previously returned users with empty telephone;
                # enforce saving the cleaned value after form.save() to guarantee
                # the database has the submitted phone number.
                telephone = form.cleaned_data.get('telephone', '')
                if telephone and (not user.telephone or user.telephone != telephone):
                    user.telephone = telephone
                    user.save(update_fields=['telephone'])
                login(request, user)
                messages.success(request, 'Compte créé avec succès! Bienvenue ' + user.first_name)
                return redirect('accounts:dashboard_client')
            except Exception as e:
                messages.error(request, 'Erreur lors de la création du compte. Veuillez réessayer.')
                return render(request, 'accounts/register.html', {'form': form})
    else:
        form = ClientRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """User login."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Bienvenue, {user.username}!')

            # Redirect based on role
            if user.is_admin():
                return redirect('accounts:dashboard_admin')
            elif user.is_employe():
                return redirect('accounts:dashboard_employe')
            elif user.is_technicien():
                return redirect('accounts:dashboard_technicien')
            elif user.is_livreur():
                return redirect('accounts:dashboard_livreur')
            else:
                return redirect('accounts:dashboard_client')
        else:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')
    return render(request, 'accounts/login.html')


def logout_view(request):
    """User logout."""
    logout(request)
    messages.success(request, 'Vous avez été déconnecté.')
    return redirect('accounts:home')


# ==================== DASHBOARDS ====================

@login_required
def dashboard_client(request):
    """Client dashboard."""
    client = request.user
    reservations = Reservation.objects.filter(client=client).order_by('-date_reservation')[:5]
    vehicules = Vehicule.objects.filter(statut='DISPONIBLE').order_by('-id')[:6]
    context = {
        'reservations': reservations,
        'vehicules': vehicules,
        'total_reservations': Reservation.objects.filter(client=client).count(),
    }
    return render(request, 'accounts/dashboard_client.html', context)


@login_required
@user_passes_test(lambda u: u.is_admin())
def dashboard_admin(request):
    """Admin dashboard with KPIs."""
    from django.db.models import Count, Sum, Avg
    from datetime import datetime, timedelta

    total_vehicules = Vehicule.objects.count()
    disponibles = Vehicule.objects.filter(statut='DISPONIBLE').count()
    en_maintenance = Vehicule.objects.filter(statut='EN_MAINTENANCE').count()
    total_clients = Utilisateur.objects.filter(role=Utilisateur.ROLE_CLIENT).count()
    total_reservations = Reservation.objects.count()
    reservations_en_cours = Reservation.objects.filter(statut_reservation='EN_COURS').count()
    reservations_en_attente = Reservation.objects.filter(statut_reservation='EN_ATTENTE').count()

    # Revenue stats
    from apps.reservations.models import Paiement
    total_revenue = Paiement.objects.filter(statut='COMPLETE').aggregate(Sum('amount'))['amount__sum'] or 0

    # Monthly reservations for chart (last 6 months)
    six_months_ago = datetime.now() - timedelta(days=180)
    monthly_reservations = []
    monthly_revenue = []
    for i in range(5, -1, -1):
        month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        count = Reservation.objects.filter(
            date_reservation__gte=month_start,
            date_reservation__lt=month_end
        ).count()
        revenue = Paiement.objects.filter(
            statut='COMPLETE',
            date_paiement__gte=month_start,
            date_paiement__lt=month_end
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        monthly_reservations.append({
            'month': month_start.strftime('%b'),
            'count': count
        })
        monthly_revenue.append(float(revenue))

    # Vehicle categories distribution
    categorie_stats = Vehicule.objects.values('categorie__type').annotate(count=Count('id'))

    # Reservation status distribution
    status_stats = Reservation.objects.values('statut_reservation').annotate(count=Count('id'))

    # Clients with multiple reservations (fideles) - using ORM
    from django.db.models import Count
    fideles_qs = Reservation.objects.values('client__id', 'client__username', 'client__first_name', 'client__last_name')\
        .annotate(count=Count('id'))\
        .filter(count__gt=1)\
        .order_by('-count')[:5]
    clients_fideles_list = []
    for f in fideles_qs:
        try:
            user = Utilisateur.objects.get(id=f['client__id'])
            clients_fideles_list.append({
                'id': f['client__id'],
                'username': f['client__username'],
                'name': user.get_full_name() or f['client__username'],
                'count': f['count']
            })
        except:
            pass

    # Vehicles rental count with details - using ORM
    vehicules_qs = Reservation.objects.values('vehicule__id', 'vehicule__marque', 'vehicule__modele')\
        .annotate(count=Count('id'))\
        .order_by('-count')[:5]
    vehicules_loues_list = []
    for v in vehicules_qs:
        vehicules_loues_list.append({
            'id': v['vehicule__id'],
            'name': f"{v['vehicule__marque']} {v['vehicule__modele']}",
            'count': v['count']
        })

    # Calculate occupation rate
    vehicules_reserved = Reservation.objects.filter(statut_reservation__in=['CONFIRMEE', 'EN_COURS']).values('vehicule').distinct().count()
    taux_occupation = int((vehicules_reserved / total_vehicules * 100)) if total_vehicules > 0 else 0

    # Maintenance costs
    from apps.vehicles.models import Maintenance
    maintenance_cost = Maintenance.objects.filter(statut='TERMINEE').aggregate(Sum('cout'))['cout__sum'] or 0

    # Monthly maintenance costs for chart
    maintenance_costs = []
    for i in range(5, -1, -1):
        month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        cost = Maintenance.objects.filter(
            date_realisee__gte=month_start,
            date_realisee__lt=month_end,
            statut='TERMINEE'
        ).aggregate(Sum('cout'))['cout__sum'] or 0
        maintenance_costs.append(float(cost))

    # Top clients with total amount spent
    top_clients_qs = Reservation.objects.values('client__id', 'client__username', 'client__first_name', 'client__last_name')\
        .annotate(count=Count('id'), total=Sum('montant_total'))\
        .order_by('-count')[:5]
    top_clients = []
    for c in top_clients_qs:
        try:
            user = Utilisateur.objects.get(id=c['client__id'])
            top_clients.append({
                'id': c['client__id'],
                'username': c['client__username'],
                'name': user.get_full_name() or c['client__username'],
                'count': c['count'],
                'total': float(c['total'] or 0)
            })
        except:
            pass

    # Add rate to vehicules_loues
    max_count = vehicules_loues_list[0]['count'] if vehicules_loues_list else 1
    for v in vehicules_loues_list:
        v['rate'] = int((v['count'] / max_count) * 100)

    # Recent data
    recent_reservations = Reservation.objects.all().order_by('-date_reservation')[:10]
    from apps.reservations.models import Livraison
    recent_livraisons = Livraison.objects.filter(latitude__isnull=False).select_related('reservation', 'livreur')[:10]
    unread = Notification.objects.filter(utilisateur=request.user, lue=False).count()

    context = {
        'total_vehicules': total_vehicules,
        'disponibles': disponibles,
        'en_maintenance': en_maintenance,
        'total_clients': total_clients,
        'total_reservations': total_reservations,
        'reservations_en_cours': reservations_en_cours,
        'reservations_en_attente': reservations_en_attente,
        'total_revenue': total_revenue,
        'monthly_reservations': monthly_reservations,
        'monthly_revenue': monthly_revenue,
        'categorie_stats': list(categorie_stats),
        'status_stats': list(status_stats),
        'clients_fideles_count': len(clients_fideles_list),
        'clients_fideles': clients_fideles_list,
        'vehicules_loues_count': len(vehicules_loues_list),
        'vehicules_loues': vehicules_loues_list,
        'taux_occupation': taux_occupation,
        'maintenance_cost': maintenance_cost,
        'maintenance_costs': maintenance_costs,
        'top_clients': top_clients,
        'recent_reservations': recent_reservations,
        'recent_livraisons': recent_livraisons,
        'unread_notifications': unread,
    }
    return render(request, 'accounts/dashboard_admin.html', context)


@login_required
@user_passes_test(lambda u: u.is_employe())
def dashboard_employe(request):
    """Employee dashboard."""
    from datetime import date, timedelta

    today = date.today()
    tomorrow = today + timedelta(days=1)
    etats_des_lieux = EtatDesLieux.objects.filter(
        employe=request.user
    ).order_by('-date')[:10]
    departs_aujourdhui = Reservation.objects.filter(
        date_debut=today,
        statut_reservation='CONFIRMEE',
    ).select_related('client', 'vehicule').order_by('date_debut')
    retours_aujourdhui = Reservation.objects.filter(
        date_fin=today,
        statut_reservation='EN_COURS',
    ).select_related('client', 'vehicule').order_by('date_fin')
    etat_depart_exists = EtatDesLieux.objects.filter(
        reservation=OuterRef('pk'),
        type='SORTIE',
    )
    etat_retour_exists = EtatDesLieux.objects.filter(
        reservation=OuterRef('pk'),
        type='ENTREE',
    )
    reservations_a_venir = Reservation.objects.filter(
        date_debut__gte=today,
    ).annotate(
        has_etat_depart=Exists(etat_depart_exists),
    ).select_related('client', 'vehicule').order_by('date_debut')
    reservations_en_cours = Reservation.objects.filter(
        statut_reservation='EN_COURS',
    ).select_related('client', 'vehicule').order_by('date_fin')
    retours_imminents = Reservation.objects.filter(
        statut_reservation='EN_COURS',
        date_fin__gte=today,
        date_fin__lte=tomorrow,
    ).annotate(
        has_etat_retour=Exists(etat_retour_exists),
    ).select_related('client', 'vehicule').order_by('date_fin')

    reservation_id = request.GET.get('reservation_id', '').strip()
    client = request.GET.get('client', '').strip()

    def apply_reservation_filters(queryset):
        if reservation_id:
            if reservation_id.isdigit():
                queryset = queryset.filter(id=int(reservation_id))
            else:
                queryset = queryset.none()

        if client:
            queryset = queryset.filter(
                Q(client__username__icontains=client)
                | Q(client__first_name__icontains=client)
                | Q(client__last_name__icontains=client)
                | Q(client__email__icontains=client)
            )

        return queryset

    reservations_a_venir = apply_reservation_filters(reservations_a_venir)
    reservations_en_cours = apply_reservation_filters(reservations_en_cours)
    retours_imminents = apply_reservation_filters(retours_imminents)

    context = {
        'etats_des_lieux': etats_des_lieux,
        'departs_aujourdhui': departs_aujourdhui,
        'retours_aujourdhui': retours_aujourdhui,
        'reservations_a_venir': reservations_a_venir,
        'reservations_en_cours': reservations_en_cours,
        'retours_imminents': retours_imminents,
        'reservation_filter_id': reservation_id,
        'client_filter': client,
        'today': today,
        'tomorrow': tomorrow,
        'reservations': list(departs_aujourdhui) + list(retours_aujourdhui),
        'terminees': etats_des_lieux.count(),
    }
    return render(request, 'accounts/dashboard_employe.html', context)


@login_required
@user_passes_test(lambda u: u.is_technicien())
def dashboard_technicien(request):
    """Technician dashboard."""
    from apps.vehicles.models import Maintenance
    mes_maintenances = Maintenance.objects.filter(
        technicien=request.user
    ).distinct().order_by('-date_prevue')
    total = mes_maintenances.count()
    en_cours = mes_maintenances.filter(statut='EN_MAINTENANCE').count()
    terminees = mes_maintenances.filter(statut='TERMINEE').count()
    recent = mes_maintenances[:10]
    context = {
        'maintenances': recent,
        'total_maintenances': total,
        'en_cours': en_cours,
        'terminees': terminees,
    }
    return render(request, 'accounts/dashboard_technicien.html', context)


@login_required
@user_passes_test(lambda u: u.is_livreur())
def dashboard_livreur(request):
    """Livreur dashboard."""
    mes_livraisons = Livraison.objects.filter(
        livreur=request.user,
        reservation__delivery_option='LIVRAISON_DOMICILE',
    ).order_by('-date_livraison')[:10]
    total = Livraison.objects.filter(livreur=request.user, reservation__delivery_option='LIVRAISON_DOMICILE').count()
    en_cours = Livraison.objects.filter(livreur=request.user, reservation__delivery_option='LIVRAISON_DOMICILE', statut='EN_COURS').count()
    completed = Livraison.objects.filter(livreur=request.user, reservation__delivery_option='LIVRAISON_DOMICILE', statut__in=['LIVREE', 'TERMINEE']).count()
    unread = Notification.objects.filter(utilisateur=request.user, lue=False).count()
    context = {
        'livraisons': mes_livraisons,
        'total_livraisons': total,
        'en_cours': en_cours,
        'completed': completed,
        'unread_notifications': unread,
    }
    return render(request, 'accounts/dashboard_livreur.html', context)


# ==================== USER MANAGEMENT ====================

@login_required
@user_passes_test(lambda u: u.is_admin())
def user_list(request):
    """List all users (admin only)."""
    users = Utilisateur.objects.all().order_by('-date_inscription')
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'accounts/user_list.html', {'page_obj': page_obj})


@login_required
@user_passes_test(lambda u: u.is_admin())
def user_create(request):
    """Create new user (admin only)."""
    from .forms import UtilisateurCreationForm
    if request.method == 'POST':
        form = UtilisateurCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Utilisateur créé avec succès!')
            return redirect('accounts:user_list')
    else:
        form = UtilisateurCreationForm()
    return render(request, 'accounts/user_form.html', {'form': form, 'action': 'Créer'})


@login_required
@user_passes_test(lambda u: u.is_admin())
def user_edit(request, pk):
    """Admin: edit user role and status."""
    user = get_object_or_404(Utilisateur, pk=pk)
    if request.method == 'POST':
        role = request.POST.get('role')
        actif = request.POST.get('actif') == 'on'
        valid_roles = [
            Utilisateur.ROLE_CLIENT,
            Utilisateur.ROLE_ADMIN,
            Utilisateur.ROLE_EMPLOYE,
            Utilisateur.ROLE_TECHNICIEN,
            Utilisateur.ROLE_LIVREUR,
        ]
        if role in valid_roles:
            user.role = role
            user.actif = actif
            user.save(update_fields=['role', 'actif'])
            messages.success(request, f'Rôle de {user.username} mis à jour.')
        else:
            messages.error(request, 'Rôle invalide.')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_edit.html', {'u': user})


@login_required
def profile(request):
    """User profile with edit functionality."""
    show_form = request.GET.get('edit') == '1'

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès!')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user) if show_form else None

    return render(request, 'accounts/profile.html', {'user': request.user, 'form': form})


@login_required
def notifications(request):
    """User notifications."""
    if request.user.is_employe():
        today = timezone.localdate()
        upcoming_reservations = Reservation.objects.filter(
            statut_reservation='CONFIRMEE',
            date_debut__gte=today,
        ).select_related('client', 'vehicule')

        for reservation in upcoming_reservations:
            mode = 'Livraison a domicile' if reservation.delivery_option == 'LIVRAISON_DOMICILE' else 'Agence'
            Notification.objects.get_or_create(
                utilisateur=request.user,
                type='RESERVATION',
                titre=f'Reservation #{reservation.id} a preparer',
                defaults={
                    'message': (
                        f'Reservation {mode} pour {reservation.vehicule} - '
                        f'client {reservation.client.get_full_name() or reservation.client.username}. '
                        f'Date depart: {reservation.date_debut}.'
                    )
                }
            )

        retours = Reservation.objects.filter(
            statut_reservation='EN_COURS',
            date_fin__gte=today,
        ).select_related('client', 'vehicule')

        for reservation in retours:
            Notification.objects.get_or_create(
                utilisateur=request.user,
                type='RESERVATION',
                titre=f'Retour reservation #{reservation.id} a verifier',
                defaults={
                    'message': (
                        f'Retour prevu le {reservation.date_fin} pour {reservation.vehicule} - '
                        f'client {reservation.client.get_full_name() or reservation.client.username}.'
                    )
                }
            )

    notifications = Notification.objects.filter(utilisateur=request.user).order_by('-date_envoi')
    # Mark as read
    notifications.filter(lue=False).update(lue=True)
    return render(request, 'accounts/notifications.html', {'notifications': notifications})
