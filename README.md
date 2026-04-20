# LOVOI_2 - Agence de Location de Voitures (Version Complète)

Application web complète de gestion d'une agence de location de voitures avec Django 4.2+.

## Stack Technique

- **Backend:** Django 4.2+ / Python 3.10+
- **Base de données:** MySQL 8.0
- **Frontend:** HTML5, CSS3, JavaScript + Bootstrap 5
- **API:** Django REST Framework
- **Auth:** Django Authentication intégrée avec RBAC

## Installation

```bash
# Cloner / Créer l'environnement
cd LOVOI_2
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Créer la base de données MySQL
mysql -u root -p
CREATE DATABASE lovoi2_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;

# Configurer settings.py avec vos identifiants MySQL

# Appliquer les migrations
python manage.py makemigrations
python manage.py migrate

# Créer un superutilisateur (admin)
python manage.py createsuperuser

# (Optionnel) Charger des données de test
python manage.py loaddata fixtures/initial_data.json

# Lancer le serveur
python manage.py runserver
```

## Structure du Projet

```
LOVOI_2/
├── apps/
│   ├── accounts/       # Gestion des utilisateurs (Client, Admin, Employé, Technicien, Livreur)
│   ├── vehicles/       # Gestion du parc automobile (Véhicule, Catégorie, Maintenance, Document)
│   ├── reservations/  # Réservations, Contrats, Livraisons, Paiements, Avis, États des Lieux
│   └── payments/      # Module de paiement (Stripe/PayPal integration)
├── core/              # Configuration Django (settings, urls, wsgi, asgi)
├── templates/         # Templates HTML (base + apps)
├── static/css/        # Fichiers statiques CSS
├── media/             # Fichiers uploadés (photos véhicules, documents, signatures)
└── requirements.txt
```

## Entités (18)

| # | Entité | Description |
|---|--------|-------------|
| 1 | Utilisateur | Modèle parent (hérite de AbstractUser) |
| 2 | Client | Proxy de Utilisateur (rôle CLIENT) |
| 3 | Admin | Proxy de Utilisateur (rôle ADMIN) |
| 4 | Employe | Proxy de Utilisateur (rôle EMPLOYE) |
| 5 | Technicien | Proxy de Utilisateur (rôle TECHNICIEN) |
| 6 | Livreur | Proxy de Utilisateur (rôle LIVREUR) |
| 7 | Notification | Notifications pour les utilisateurs |
| 8 | Categorie | Catégories de véhicules (SUV, Économique, etc.) |
| 9 | Vehicule | Véhicule avec tous ses attributs |
| 10 | VehiculePhoto | Photos additionnelles |
| 11 | Maintenance | Historique des maintenances |
| 12 | Document | Documents légaux (assurance, carte grise, visite technique) |
| 13 | Slot | Places de parking/stockage |
| 14 | Reservation | Réservation entre client et véhicule |
| 15 | Contrat | Contrat de location PDF |
| 16 | Livraison | Livraison/récupération par livreur |
| 17 | Paiement | Paiements (acompte, total, caution, remboursement) |
| 18 | Facture | Facture avec TVA |
| 19 | Avis | Notes et commentaires des clients |
| 20 | État des Lieux | Inspection entrée/sortie |

## Rôles & Permissions (RBAC)

| Rôle | Droits |
|------|--------|
| **CLIENT** | Voir catalogue, réserver, payer, noter, consulter historique |
| **ADMIN** | Gérer utilisateurs, véhicules, réservations, documents, statistiques |
| **EMPLOYE** | Effectuer états des lieux, mise à jour kilométrage |
| **TECHNICIEN** | Gérer les maintenances |
| **LIVREUR** | Gérer les livraisons |

## Fonctionnalités Implémentées

### Utilisateurs
- [x] Inscription / Connexion / Déconnexion
- [x] Profil utilisateur avec édition
- [x] Système RBAC avec 5 rôles
- [x] Notifications
- [x] Tableau de bord personnalisé par rôle

### Parc Automobile
- [x] Catalogue avec filtres (catégorie, carburant, transmission, prix)
- [x] CRUD complet véhicules
- [x] Gestion des catégories
- [x] Photos multiples par véhicule
- [x] Documents avec alertes d'expiration
- [x] Historique des maintenances

### Réservations
- [x] Création de réservation avec vérification disponibilité
- [x] Calcul automatique du prix total
- [x] Workflow complet: EN_ATTENTE → CONFIRMEE → EN_COURS → TERMINEE
- [x] Annulation et prolongation
- [x] Génération de contrat
- [x] États des lieux (entrée/sortie)
- [x] Gestion des slots

### Paiements
- [x] Multiple modes (carte bancaire, espèces, virement, PayPal)
- [x] Acompte, paiement total, caution
- [x] Facturation avec TVA
- [x] Gestion des remboursements

### Livraisons
- [x] Planification par livreur
- [x] Suivi du statut (planifiée, en cours, terminée, échec)
- [x] Kilométrage départ/retour

### Avis
- [x] Système de notation 1-5 étoiles
- [x] Commentaires clients
- [x] Un seul avis par client par véhicule

### API REST
- [x] Endpoints pour utilisateurs, véhicules, réservations
- [x] Authentification par token (optionnel)
- [x] Pagination et filtres

## Commandes de Gestion

```bash
# Vérifier les documents expirants (à planifier avec cron)
python manage.py check_document_expiration --days=30

# Créer un utilisateur depuis la ligne de commande
python manage.py shell
>>> from apps.accounts.models import Utilisateur
>>> Utilisateur.objects.create_superuser('admin', 'admin@lovoi.com', 'password', role='ADMIN')
```

## URLs Principales

| URL | Description |
|-----|-------------|
| `/` | Page d'accueil |
| `/login/` | Connexion |
| `/register/` | Inscription client |
| `/dashboard/client/` | Espace client |
| `/dashboard/admin/` | Espace admin |
| `/vehicles/` | Catalogue véhicules |
| `/vehicles/create/` | Ajouter véhicule (admin) |
| `/reservations/create/<id>/` | Créer réservation |
| `/reservations/my/` | Mes réservations |
| `/reservations/list/` | Toutes les réservations (admin) |
| `/api/` | API REST |

## Tâches à Compléter (Production)

1. **Configuration email** - Configurer SMTP dans settings.py
2. **Stripe/PayPal** - Intégrer les clés API真实的支付
3. **PDF génération** - Utiliser weasyprint ou reportlab pour contrats/factures
4. **CI/CD** - GitHub Actions pour déploiement
5. **Tests** - pytest + Selenium pour tests E2E
6. **Logs** - Configurer logging dans settings.py

## Licence

Projet scolaire EMSI 2024
