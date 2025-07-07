# 📄 **README.md complet**


# 🚗 WaziGo - Optimiseur d'Itinéraires Intelligent

WaziGo est une application web avancée de recherche et d'optimisation d'itinéraires qui utilise l'intelligence artificielle et les données de trafic en temps réel pour proposer les meilleurs trajets possibles.

## 📋 Description

WaziGo révolutionne la planification de trajets en combinant :
- **Données de trafic en temps réel** via Google Maps API
- **Algorithmes d'optimisation** intelligents 
- **Interface utilisateur moderne** et responsive
- **Analytics avancées** pour améliorer vos habitudes de déplacement
- **Gestion des favoris** et historique des trajets

L'application analyse plusieurs itinéraires alternatifs, évalue les conditions de circulation, identifie les points de congestion et recommande la meilleure route selon vos préférences.

## ✨ Fonctionnalités Principales

### 🎯 Recherche d'Itinéraires
- **Multi-critères** : Plus rapide, plus court, équilibré
- **Évitement intelligent** : Péages, autoroutes, ferries
- **Alternatives multiples** : Jusqu'à 5 itinéraires différents
- **Trafic temps réel** : Intégration des conditions actuelles

### 🧠 Optimisation Intelligente
- **Score d'optimisation** (0-10) pour chaque route
- **Analyse des incidents** : Accidents, travaux, fermetures
- **Prédictions de trafic** : Estimation des conditions futures
- **Points critiques** : Identification des zones de congestion

### 🗺️ Interface Cartographique
- **Sélection interactive** sur carte Leaflet/OpenStreetMap
- **Géocodage automatique** des adresses
- **Autocomplétion** des lieux
- **Coordonnées GPS** précises

### 👤 Gestion Utilisateur
- **Comptes utilisateur** avec authentification sécurisée
- **Favoris** : Sauvegarde des itinéraires préférés
- **Historique** : Traçabilité de tous vos trajets
- **Analytics personnelles** : Statistiques d'utilisation

### 📊 Tableaux de Bord
- **Temps économisé** total et par période
- **Distance parcourue** et impact environnemental
- **Patterns de déplacement** : Heures et jours préférés
- **Score d'efficacité** global

### 🌍 Multi-Pays
- **Support international** avec sélection de pays
- **Géolocalisation automatique** de l'utilisateur
- **Contraintes géographiques** respectées

## 🛠️ Technologies Utilisées

### Backend
- **Flask** (Python) - Framework web
- **SQLAlchemy** - ORM base de données
- **Google Maps API** - Données cartographiques et trafic
- **SQLite** - Base de données
- **Redis** (optionnel) - Cache et sessions

### Frontend
- **HTML5/CSS3** - Structure et style
- **JavaScript ES6+** - Logique côté client
- **TailwindCSS** - Framework CSS moderne
- **Leaflet** - Cartes interactives
- **Chart.js** - Graphiques et visualisations

### Services Externes
- **Google Maps API** - Routage et géocodage
- **OpenStreetMap** - Tuiles cartographiques
- **Nominatim** - Géocodage de secours

## 📦 Installation

### Prérequis
- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)
- Node 22 ou supérieur
- Clé API Google Maps (gratuite)
- Git

### 1. Cloner le Repository

```bash
git clone https://github.com/Brayan-Weko/wazigo-app
cd WaziGo
```

### 2. Créer un Environnement Virtuel

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Installer les Dépendances

```bash
pip install -r backend/requirements.txt
```

```bash
npm install
```

### 4. Configuration des Variables d'Environnement

Créez un fichier `.env` à la racine du projet :

```env
# Configuration Flask
FLASK_ENV=development
FLASK_SECRET_KEY=super-secret-key-change-in-production
PORT=5000

# Base de données MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=smart_route_db

# HERE Maps API
HERE_API_KEY=WSmHMi5J0XCGO2A7A84BuSvMsnEwzlEq9Heq9EPnnIE

# Google OAuth 2.0
GOOGLE_CLIENT_ID=641584917672-96th5oiev32586ghsfk8g6j1lvgdt0l2.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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

# Redis (Cache)
REDIS_URL=redis://localhost:6379

# Application
APP_NAME=WaziGo
APP_URL=http://localhost:5000

# Logs
LOG_LEVEL=INFO
```

## ▶️ Exécution

### Mode Développement

```bash
python run.py
```

L'application sera accessible à l'adresse : `http://localhost:5000`


## 🏗️ Structure du Projet

```
wazigo-app/
│
├── 📁 backend/
│   ├── 📄 app.py                    # Application Flask principale
│   ├── 📄 config.py                 # Configuration (DB, API keys, etc.)
│   ├── 📄 requirements.txt          # Dépendances Python
│   │
│   ├── 📁 models/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 user.py              # Modèle utilisateur
│   │   ├── 📄 route.py             # Modèle itinéraire
│   │   ├── 📄 history.py           # Modèle historique
│   │   └── 📄 database.py          # Connexion DB
│   │
│   ├── 📁 routes/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 auth.py              # Routes authentification
│   │   ├── 📄 main.py              # Routes principales
│   │   ├── 📄 api.py               # API routes
│   │   └── 📄 maps.py              # Routes cartographie
│   │
│   ├── 📁 services/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 here_api.py          # Service HERE Maps
│   │   ├── 📄 route_optimizer.py  # Algorithme d'optimisation
│   │   ├── 📄 traffic_analyzer.py # Analyse trafic
│   │   └── 📄 google_auth.py       # Service OAuth Google
│   │
│   └── 📁 utils/
│       ├── 📄 __init__.py
│       ├── 📄 helpers.py           # Fonctions utilitaires
│       └── 📄 decorators.py        # Décorateurs personnalisés
│
├── 📁 frontend/
│   ├── 📁 static/
│   │   ├── 📁 css/
│   │   │   └── 📄 style.css        # Styles personnalisés
│   │   ├── 📁 js/
│   │   │   ├── 📄 main.js          # JavaScript principal
│   │   │   ├── 📄 maps.js          # Gestion cartes
│   │   │   ├── 📄 auth.js          # Authentification
│   │   │   └── 📄 utils.js         # Utilitaires JS
│   │   └── 📁 images/
│   │       └── 📄 logo.png
│   │
│   └── 📁 templates/
│       ├── 📁 components/
│       │   ├── 📄 header.html      # Header partagé
│       │   ├── 📄 footer.html      # Footer partagé
│       │   ├── 📄 sidebar.html     # Sidebar navigation
│       │   └── 📄 auth_modal.html  # Modal de connexion
│       │
│       ├── 📄 base.html            # Template de base
│       ├── 📄 index.html           # Page d'accueil
│       ├── 📄 search.html          # Recherche d'itinéraire
│       ├── 📄 results.html         # Résultats et carte
│       ├── 📄 navigation.html      # Navigation active
│       ├── 📄 history.html         # Historique des trajets
│       ├── 📄 analytics.html       # Analytics et stats
│       ├── 📄 settings.html        # Paramètres utilisateur
│       ├── 📄 about.html           # À propos
│       └── 📄 profile.html         # Profil utilisateur
│
├── 📁 database/
│   ├── 📄 schema.sql               # Structure de la DB
│   ├── 📄 migrations/              # Scripts de migration
│   └── 📄 seed_data.sql           # Données d'exemple
│
├── 📁 docs/
│   ├── 📄 API.md                   # Documentation API
│   └── 📄 DEPLOYMENT.md           # Guide de déploiement
│
├── logs/               # Fichiers de logs
├── documentation/      # 📄 PDF de présentation
├── demo-video/              # 🎥 Vidéos de démonstration
├── 📄 .env                         # Variables d'environnement
├── 📄 .gitignore
├── 📄 README.md
└── 📄 run.py                       # Point d'entrée application
```

## 📚 Documentation Complémentaire

### 📄 Présentation Complète
Le **PDF de présentation détaillé** du projet se trouve dans le dossier :
```
documentation/
└── WaziGo_Presentation.pdf     # Présentation complète du projet
```

### 🎥 Vidéos de Démonstration
Les **vidéos de démonstration** et tutoriels sont disponibles dans :
```
demo-video/
└── WaziGo_Presentation.mp4            # Présentation générale
```

## 🐛 Dépannage

### Problèmes Courants

**1. Erreur de clé API HERE Maps**
```bash
# Vérifier la clé
curl "https://geocode.search.hereapi.com/v1/geocode?q=Paris&apikey=VOTRE_CLE"
```

**2. Problème de base de données**
```bash
# Réinitialiser la DB
python run.py
```

**3. Problèmes de permissions**
```bash
# Linux/macOS
chmod +x app.py
chmod -R 755 static/
```

**4. Port déjà utilisé**
```bash
# Changer le port
export FLASK_RUN_PORT=8000
python app.py
```

### Logs de Débogage

Les logs sont disponibles dans :
```
logs/
├── app.log              # Logs généraux
├── error.log            # Erreurs uniquement
├── here_api.log         # Logs API Google Maps
└── traffic.log          # Logs d'analyse trafic
```

## 🤝 Contribution

1. Fork le projet
2. Créez une branche pour votre fonctionnalité
3. Commitez vos changements
4. Poussez vers la branche
5. Ouvrez une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 📞 Support

- **Email** : wekobrayan163@gmail.com
- **Documentation** : `documentation/`
- **Issues** : GitHub Issues
- **Discussions** : GitHub Discussions

## 🏆 Auteurs

- **Brayan Weko** - Développeur Principal
- **Équipe TechSpectra** - Contributeurs

---

## 🚀 Démarrage Rapide

```bash
# 1. Clone et installation
git clone https://github.com/your-username/WaziGo.git
cd WaziGo
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Configuration
pip install -r backend/requirements.txt

# 4. Initialisation & Lancement
python run.py
# Ouvrir http://localhost:5000
```

**🎉 WaziGo est maintenant prêt à optimiser vos trajets !**
```

Ce README complet couvre tous les aspects essentiels de votre projet WaziGo, avec des instructions claires pour l'installation, l'initialisation et l'exécution, ainsi que les références aux dossiers de documentation et de démonstration vidéo ! 🚀