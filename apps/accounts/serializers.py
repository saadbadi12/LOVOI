from rest_framework import serializers
from .models import Utilisateur, Notification


class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'telephone', 'adresse', 'role', 'date_inscription']
        read_only_fields = ['id', 'date_inscription']


class UtilisateurCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Utilisateur
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name',
                  'telephone', 'adresse', 'permis_numero', 'permis_date', 'role']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Utilisateur(**validated_data)
        user.set_password(password)
        user.save()
        return user


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'utilisateur', 'type', 'titre', 'message', 'date_envoi', 'lue']
        read_only_fields = ['id', 'date_envoi']
