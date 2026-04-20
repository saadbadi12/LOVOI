from django.urls import path
from . import views

app_name = 'vehicles'

urlpatterns = [
    # Public
    path('', views.vehicle_list, name='vehicle_list'),
    path('<int:pk>/', views.vehicle_detail, name='vehicle_detail'),

    # Admin - Vehicles CRUD
    path('create/', views.vehicle_create, name='vehicle_create'),
    path('<int:pk>/edit/', views.vehicle_update, name='vehicle_update'),
    path('<int:pk>/delete/', views.vehicle_delete, name='vehicle_delete'),

    # Maintenance
    path('maintenance/', views.maintenance_list, name='maintenance_list'),
    path('maintenance/create/', views.maintenance_create, name='maintenance_create'),
    path('maintenance/<int:pk>/edit/', views.maintenance_update, name='maintenance_update'),

    # Documents
    path('documents/', views.document_list, name='document_list'),
    path('documents/create/', views.document_create, name='document_create'),
    path('documents/<int:pk>/edit/', views.document_update, name='document_update'),

    # Categories
    path('categories/', views.categorie_list, name='categorie_list'),
    path('categories/create/', views.categorie_create, name='categorie_create'),
]
