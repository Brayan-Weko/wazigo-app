# 📦 Guide d'Installation - Smart Route

Ce guide vous accompagne pour installer et configurer Smart Route en local ou en production.

## 🎯 Prérequis

### Système
- **OS**: Linux (Ubuntu 20.04+), macOS, ou Windows avec WSL2
- **RAM**: Minimum 4GB, recommandé 8GB+
- **Stockage**: Minimum 10GB d'espace libre

### Logiciels requis
- **Python 3.11+** avec pip
- **Node.js 18+** avec npm (pour le développement front-end)
- **MySQL 5+** avec npm (pour le développement front-end)
- **PostgreSQL 13+** (ou Docker)
- **Redis 6+** (ou Docker)
- **Git**

### Comptes externes requis
- **HERE Maps API** - [Créer un compte](https://developer.here.com/)
- **Google OAuth** - [Console développeurs](https://console.developers.google.com/)

---

## 🚀 Installation Rapide avec Docker

### 1. Cloner le repository
```bash
git clone https://github.com/votre-org/smart-route.git
cd smart-route
```

### 2. Configuration
#### Copier le fichier d'environnement
cp .env.example .env

#### Éditer les variables d'environnement
nano .env