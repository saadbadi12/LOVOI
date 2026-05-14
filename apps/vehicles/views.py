from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Q
from django.http import HttpResponse
from datetime import date
from decimal import Decimal, InvalidOperation
from .models import Vehicule, Categorie, Maintenance, Document
from .forms import VehiculeForm, MaintenanceForm, DocumentForm, CategorieForm
from apps.reservations.models import Reservation


def vehicle_list(request):
    """Public vehicle catalog with filters."""
    is_admin_view = (
        request.user.is_authenticated
        and (request.user.is_staff or request.user.is_admin())
    )

    vehicules = Vehicule.objects.all()

    # Filters
    search = request.GET.get('search', '')
    categorie_id = request.GET.get('categorie')
    carburant = request.GET.get('carburant')
    transmission = request.GET.get('transmission')
    prix_max = request.GET.get('prix_max')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')

    if search:
        search_filter = (
            Q(marque__icontains=search) |
            Q(modele__icontains=search) |
            Q(immatriculation__icontains=search) |
            Q(categorie__type__icontains=search) |
            Q(carburant__icontains=search) |
            Q(transmission__icontains=search)
        )

        try:
            search_price = Decimal(search.replace(',', '.'))
            search_filter |= Q(prix_journalier=search_price)
        except (InvalidOperation, AttributeError):
            pass

        vehicules = vehicules.filter(search_filter)

    if categorie_id:
        vehicules = vehicules.filter(categorie_id=categorie_id)

    if carburant:
        vehicules = vehicules.filter(carburant=carburant)

    if transmission:
        vehicules = vehicules.filter(transmission=transmission)

    if prix_max:
        try:
            prix_max_decimal = Decimal(prix_max.replace(',', '.'))
            vehicules = vehicules.filter(prix_journalier__lte=prix_max_decimal)
        except (InvalidOperation, AttributeError):
            prix_max = ''

    if is_admin_view and date_debut and date_fin:
        try:
            debut = date.fromisoformat(date_debut)
            fin = date.fromisoformat(date_fin)
        except ValueError:
            debut = None
            fin = None

        if debut and fin and fin > debut:
            reserved_vehicle_ids = Reservation.objects.filter(
                statut_reservation__in=['EN_ATTENTE', 'CONFIRMEE', 'EN_COURS'],
                date_debut__lt=fin,
                date_fin__gt=debut,
            ).values_list('vehicule_id', flat=True)
            vehicules = vehicules.exclude(id__in=reserved_vehicle_ids)

    vehicules = vehicules.order_by('-date_ajout')
    categories = Categorie.objects.all()

    paginator = Paginator(vehicules, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    query_params = request.GET.copy()
    query_params.pop('page', None)

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'query_string': query_params.urlencode(),
        'filters': {
            'search': search,
            'categorie': categorie_id,
            'carburant': carburant,
            'transmission': transmission,
            'prix_max': prix_max,
            'date_debut': date_debut,
            'date_fin': date_fin,
        }
    }
    return render(request, 'vehicles/vehicle_list.html', context)


def vehicle_detail(request, pk):
    """Vehicle detail page."""
    vehicule = get_object_or_404(Vehicule, pk=pk)
    avis = vehicule.avis.select_related('client').all()
    avis_stats = avis.aggregate(note_moyenne=Avg('note'))
    note_moyenne = avis_stats['note_moyenne']
    context = {
        'vehicule': vehicule,
        'avis_list': avis,
        'avis_count': avis.count(),
        'note_moyenne': round(note_moyenne, 1) if note_moyenne else None,
    }
    return render(request, 'vehicles/vehicle_detail.html', context)


# ==================== ADMIN / STAFF VIEWS ====================

@login_required
@user_passes_test(lambda u: u.is_admin())
def vehicle_create(request):
    """Add new vehicle."""
    if request.method == 'POST':
        form = VehiculeForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Véhicule ajouté avec succès!')
            return redirect('vehicles:vehicle_list')
    else:
        form = VehiculeForm()
    return render(request, 'vehicles/vehicle_form.html', {'form': form, 'action': 'Ajouter'})


@login_required
@user_passes_test(lambda u: u.is_admin())
def vehicle_update(request, pk):
    """Update vehicle."""
    vehicule = get_object_or_404(Vehicule, pk=pk)
    if request.method == 'POST':
        form = VehiculeForm(request.POST, request.FILES, instance=vehicule)
        if form.is_valid():
            form.save()
            messages.success(request, 'Véhicule mis à jour!')
            return redirect('vehicles:vehicle_list')
    else:
        form = VehiculeForm(instance=vehicule)
    return render(request, 'vehicles/vehicle_form.html', {'form': form, 'vehicule': vehicule, 'action': 'Modifier'})


@login_required
@user_passes_test(lambda u: u.is_admin())
def vehicle_delete(request, pk):
    """Delete vehicle."""
    vehicule = get_object_or_404(Vehicule, pk=pk)
    if request.method == 'POST':
        vehicule.delete()
        messages.success(request, 'Véhicule supprimé!')
        return redirect('vehicles:vehicle_list')
    return render(request, 'vehicles/vehicle_confirm_delete.html', {'vehicule': vehicule})


# ==================== MAINTENANCE ====================

@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_technicien())
def maintenance_list(request):
    """List all maintenance records."""
    maintenances = Maintenance.objects.all().order_by('-date_prevue')
    # Technicien only sees their own maintenances (admin sees all)
    if request.user.is_technicien() and not request.user.is_admin():
        maintenances = maintenances.filter(technicien=request.user)
    if request.GET.get('vehicule'):
        maintenances = maintenances.filter(vehicule_id=request.GET.get('vehicule'))
    if request.GET.get('statut'):
        maintenances = maintenances.filter(statut=request.GET.get('statut'))
    return render(request, 'vehicles/maintenance_list.html', {'maintenances': maintenances})


@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_technicien())
def maintenance_create(request):
    """Create maintenance record."""
    if request.method == 'POST':
        form = MaintenanceForm(request.POST)
        if form.is_valid():
            maintenance = form.save(commit=False)
            # Auto-assign technician if user is a technician and no technician selected
            if request.user.is_technicien() and not maintenance.technicien:
                maintenance.technicien = request.user
            maintenance.save()
            messages.success(request, 'Maintenance enregistrée!')
            return redirect('vehicles:maintenance_list')
    else:
        form = MaintenanceForm()
        if request.GET.get('vehicule'):
            form.fields['vehicule'].initial = request.GET.get('vehicule')
    vehicles = Vehicule.objects.all()
    return render(request, 'vehicles/maintenance_form.html', {'form': form, 'vehicles': vehicles})


@login_required
@user_passes_test(lambda u: u.is_admin() or u.is_technicien())
def maintenance_update(request, pk):
    """Update maintenance record."""
    maintenance = get_object_or_404(Maintenance, pk=pk)
    # Technicien can only update their own
    if request.user.is_technicien() and maintenance.technicien != request.user:
        messages.error(request, 'Vous ne pouvez modifier que vos propres maintenances.')
        return redirect('accounts:dashboard_technicien')
    if request.method == 'POST':
        form = MaintenanceForm(request.POST, instance=maintenance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Maintenance mise à jour!')
            return redirect('accounts:dashboard_technicien')
    else:
        form = MaintenanceForm(instance=maintenance)
    return render(request, 'vehicles/maintenance_form.html', {'form': form, 'maintenance': maintenance, 'vehicles': Vehicule.objects.all()})


# ==================== DOCUMENTS ====================

@login_required
@user_passes_test(lambda u: u.is_admin())
def document_list(request):
    """List all vehicle documents."""
    documents = Document.objects.all().order_by('date_expiration')
    # Filter expired/expiring soon
    filter_type = request.GET.get('filter')
    if filter_type == 'expired':
        from django.utils import timezone
        documents = documents.filter(date_expiration__lt=timezone.now().date())
    elif filter_type == 'expiring':
        from django.utils import timezone
        from datetime import timedelta
        documents = documents.filter(
            date_expiration__gte=timezone.now().date(),
            date_expiration__lte=timezone.now().date() + timedelta(days=30)
        )
    return render(request, 'vehicles/document_list.html', {'documents': documents})


@login_required
@user_passes_test(lambda u: u.is_admin())
def document_create(request):
    """Add document to vehicle."""
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Document ajouté!')
            return redirect('vehicles:document_list')
    else:
        form = DocumentForm()
    return render(request, 'vehicles/document_form.html', {'form': form, 'vehicles': Vehicule.objects.all()})


@login_required
@user_passes_test(lambda u: u.is_admin())
def document_update(request, pk):
    """Update document."""
    document = get_object_or_404(Document, pk=pk)
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            form.save()
            messages.success(request, 'Document mis à jour!')
            return redirect('vehicles:document_list')
    else:
        form = DocumentForm(instance=document)
    return render(request, 'vehicles/document_form.html', {'form': form, 'document': document, 'vehicles': Vehicule.objects.all()})


# ==================== CATEGORIES ====================

@login_required
@user_passes_test(lambda u: u.is_admin())
def categorie_list(request):
    categories = Categorie.objects.all()
    return render(request, 'vehicles/categorie_list.html', {'categories': categories})


@login_required
@user_passes_test(lambda u: u.is_admin())
def categorie_create(request):
    if request.method == 'POST':
        form = CategorieForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Catégorie ajoutée!')
            return redirect('vehicles:categorie_list')
    else:
        form = CategorieForm()
    return render(request, 'vehicles/categorie_form.html', {'form': form})
