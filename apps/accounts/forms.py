from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Utilisateur, Notification


class UtilisateurCreationForm(UserCreationForm):
    """Form for creating new users."""
    telephone = forms.CharField(required=False, max_length=20)
    adresse = forms.CharField(required=False, max_length=255)
    permis_numero = forms.CharField(required=False, max_length=50)
    permis_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    role = forms.ChoiceField(choices=Utilisateur.ROLE_CHOICES)

    class Meta:
        model = Utilisateur
        fields = ('username', 'email', 'first_name', 'last_name', 'telephone',
                  'adresse', 'permis_numero', 'permis_date', 'role')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.telephone = self.cleaned_data.get('telephone', '')
        user.adresse = self.cleaned_data.get('adresse', '')
        user.permis_numero = self.cleaned_data.get('permis_numero', '')
        user.permis_date = self.cleaned_data.get('permis_date')
        user.role = self.cleaned_data.get('role', Utilisateur.ROLE_CLIENT)
        if commit:
            user.save()
        return user


class UtilisateurChangeForm(UserChangeForm):
    """Form for editing existing users."""
    class Meta:
        model = Utilisateur
        fields = ('username', 'email', 'first_name', 'last_name', 'telephone',
                  'adresse', 'permis_numero', 'permis_date', 'role', 'is_active')


class ClientRegistrationForm(UserCreationForm):
    """Registration form for clients."""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    telephone = forms.CharField(required=True, max_length=20)
    permis_numero = forms.CharField(required=True, max_length=50)
    permis_date = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = Utilisateur
        fields = ('username', 'email', 'first_name', 'last_name', 'telephone',
                  'permis_numero', 'permis_date', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = Utilisateur.ROLE_CLIENT
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.telephone = self.cleaned_data['telephone']
        user.permis_numero = self.cleaned_data['permis_numero']
        user.permis_date = self.cleaned_data['permis_date']
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """Form for users to edit their own profile."""
    class Meta:
        model = Utilisateur
        fields = ('email', 'first_name', 'last_name', 'telephone',
                  'adresse', 'permis_numero', 'permis_date')


class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ('type', 'titre', 'message', 'utilisateur')
