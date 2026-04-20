from django.urls import path
from . import views

app_name = 'reservations'

urlpatterns = [
    # Client
    path('create/<int:vehicle_id>/', views.reservation_create, name='reservation_create'),
    path('<int:pk>/', views.reservation_detail, name='reservation_detail'),
    path('my/', views.my_reservations, name='my_reservations'),
    path('avis/<int:vehicle_id>/', views.avis_create, name='avis_create'),

    # Admin management
    path('list/', views.reservation_list, name='reservation_list'),
    path('<int:pk>/confirm/', views.reservation_confirm, name='reservation_confirm'),
    path('<int:pk>/cancel/', views.reservation_cancel, name='reservation_cancel'),
    path('<int:pk>/start/', views.reservation_start, name='reservation_start'),
    path('<int:pk>/end/', views.reservation_end, name='reservation_end'),
    path('<int:pk>/extend/', views.extend_reservation, name='extend_reservation'),

    # Slots
    path('slots/', views.slot_list, name='slot_list'),
    path('slots/create/', views.slot_create, name='slot_create'),

    # Livraisons
    path('livraisons/', views.livraison_list, name='livraison_list'),
    path('livraisons/create/', views.livraison_create, name='livraison_create'),
    path('livraisons/<int:pk>/edit/', views.livraison_update, name='livraison_update'),

    # Paiements
    path('paiements/', views.paiement_list, name='paiement_list'),
    path('paiements/<int:reservation_id>/', views.paiement_create, name='paiement_create'),

    # État des lieux
    path('etat-des-lieux/', views.etat_des_lieux_list, name='etat_des_lieux_list'),
    path('etat-des-lieux/<int:reservation_id>/', views.etat_des_lieux_create, name='etat_des_lieux_create'),

    # API
    path('check-availability/', views.check_availability, name='check_availability'),
]
