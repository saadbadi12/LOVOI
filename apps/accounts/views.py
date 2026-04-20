from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Utilisateur, Notification
from .forms import ClientRegistrationForm
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
            user = form.save()
            login(request, user)
            messages.success(request, 'Compte créé avec succès!')
            return redirect('accounts:dashboard_client')
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
    total_vehicules = Vehicule.objects.count()
    disponibles = Vehicule.objects.filter(statut='DISPONIBLE').count()
    en_maintenance = Vehicule.objects.filter(statut='EN_MAINTENANCE').count()
    total_clients = Utilisateur.objects.filter(role=Utilisateur.ROLE_CLIENT).count()
    total_reservations = Reservation.objects.count()
    reservations_en_cours = Reservation.objects.filter(statut_reservation='EN_COURS').count()
    reservations_en_attente = Reservation.objects.filter(statut_reservation='EN_ATTENTE').count()

    recent_reservations = Reservation.objects.all().order_by('-date_reservation')[:10]

    context = {
        'total_vehicules': total_vehicules,
        'disponibles': disponibles,
        'en_maintenance': en_maintenance,
        'total_clients': total_clients,
        'total_reservations': total_reservations,
        'reservations_en_cours': reservations_en_cours,
        'reservations_en_attente': reservations_en_attente,
        'recent_reservations': recent_reservations,
    }
    return render(request, 'accounts/dashboard_admin.html', context)


@login_required
@user_passes_test(lambda u: u.is_employe())
def dashboard_employe(request):
    """Employee dashboard."""
    etats_des_lieux = EtatDesLieux.objects.filter(
        employe=request.user
    ).order_by('-date')[:10]
    context = {
        'etats_des_lieux': etats_des_lieux,
    }
    return render(request, 'accounts/dashboard_employe.html', context)


@login_required
@user_passes_test(lambda u: u.is_technicien())
def dashboard_technicien(request):
    """Technician dashboard."""
    from apps.vehicles.models import Maintenance
    mes_maintenances = Maintenance.objects.filter(
        vehicule__maintenances__isnull=False
    ).distinct().order_by('-date_prevue')[:10]
    context = {
        'maintenances': mes_maintenances,
    }
    return render(request, 'accounts/dashboard_technicien.html', context)


@login_required
@user_passes_test(lambda u: u.is_livreur())
def dashboard_livreur(request):
    """Livreur dashboard."""
    mes_livraisons = Livraison.objects.filter(
        livreur=request.user
    ).order_by('-date_livraison')[:10]
    context = {
        'livraisons': mes_livraisons,
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
def profile(request):
    """User profile."""
    return render(request, 'accounts/profile.html', {'user': request.user})


@login_required
def notifications(request):
    """User notifications."""
    notifications = Notification.objects.filter(utilisateur=request.user).order_by('-date_envoi')
    # Mark as read
    notifications.filter(lue=False).update(lue=True)
    return render(request, 'accounts/notifications.html', {'notifications': notifications})
