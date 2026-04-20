from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_client, name='register'),

    # Dashboards
    path('dashboard/client/', views.dashboard_client, name='dashboard_client'),
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/employe/', views.dashboard_employe, name='dashboard_employe'),
    path('dashboard/technicien/', views.dashboard_technicien, name='dashboard_technicien'),
    path('dashboard/livreur/', views.dashboard_livreur, name='dashboard_livreur'),

    # User Management
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('profile/', views.profile, name='profile'),
    path('notifications/', views.notifications, name='notifications'),
]
