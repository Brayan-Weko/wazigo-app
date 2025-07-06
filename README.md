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
├── 📁 tests/
│   ├── 📄 test_routes.py
│   ├── 📄 test_services.py
│   └── 📄 test_models.py
│
├── 📁 docs/
│   ├── 📄 API.md                   # Documentation API
│   └── 📄 DEPLOYMENT.md           # Guide de déploiement
│
├── 📄 .env                         # Variables d'environnement
├── 📄 .gitignore
├── 📄 README.md
└── 📄 run.py                       # Point d'entrée application