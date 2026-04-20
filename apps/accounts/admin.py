from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Utilisateur, Notification
from .forms import UtilisateurCreationForm, UtilisateurChangeForm


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    add_form = UtilisateurCreationForm
    form = UtilisateurChangeForm
    model = Utilisateur

    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'date_inscription')
    list_filter = ('role', 'is_active', 'is_staff', 'date_inscription')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_inscription',)

    fieldsets = UserAdmin.fieldsets + (
        ('Informations LOVOI', {
            'fields': ('telephone', 'adresse', 'permis_numero', 'permis_date', 'photo', 'role', 'poste', 'specialite')
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations LOVOI', {
            'fields': ('telephone', 'adresse', 'permis_numero', 'permis_date', 'role', 'poste', 'specialite')
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'type', 'titre', 'date_envoi', 'lue')
    list_filter = ('type', 'lue')
    search_fields = ('utilisateur__username', 'titre', 'message')
    readonly_fields = ('date_envoi',)
