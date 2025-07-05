"""
Point d'entrée principal de l'application Smart Route
"""

import os
import sys
import subprocess
from backend.app import create_app, db

# Ajouter le répertoire backend au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Créer l'application
app = create_app()

def build_assets():
    """Compile les assets frontend (Tailwind CSS)"""
    try:
        # Chemin vers npm (peut varier selon votre installation)
        npm_path = os.path.join(os.environ.get('APPDATA'), 'npm', 'npm.cmd')
        
        # Vérifie si node_modules existe
        if not os.path.exists('node_modules'):
            print("⏳ Installation des dépendances Node.js...")
            subprocess.run([npm_path, 'install'], check=True, shell=True)
        
        print("🔨 Compilation des assets Tailwind CSS...")
        subprocess.run([npm_path, 'run', 'build'], check=True, shell=True)
        print("✅ Assets compilés avec succès")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de la compilation des assets: {e}")

if __name__ == '__main__':
    # Configuration pour le développement
    with app.app_context():
        # Créer les tables si elles n'existent pas
        try:
            db.create_all()
            print("✅ Base de données initialisée avec succès")
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation de la base de données: {e}")

        # Compiler les assets en mode développement
        if app.debug:
            build_assets()
    
    # Lancer le serveur de développement
    print(f"🚀 Démarrage de {app.config['APP_NAME']} sur {app.config['APP_URL']}")
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=True,
        threaded=True
    )