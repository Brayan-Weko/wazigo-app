"""
Point d'entrée principal de l'application Smart Route
"""

import os
import sys
import subprocess
import threading
from backend.app import create_app, db
from PIL import Image

# Ajouter le répertoire backend au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Créer l'application
app = create_app()

def convert_to_ico(input_path, output_size=(256, 256)):
    """
    Convertit une image en .ico et retourne le chemin du fichier .ico
    Gère automatiquement les images transparentes et différentes tailles
    """
    try:
        # Vérifier si le fichier source existe
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Le fichier source {input_path} n'existe pas")
        
        # Créer le chemin de sortie
        base_dir = os.path.dirname(input_path)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(base_dir, f"{base_name}.ico")
        
        # Ouvrir l'image et la convertir
        with Image.open(input_path) as img:
            # Conserver la transparence si elle existe
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert("RGBA")
                ico_sizes = [(size, size) for size in (16, 24, 32, 48, 64, 128, 256)]
                img.save(output_path, format='ICO', sizes=ico_sizes, quality=100)
            else:
                img = img.convert("RGB")
                img.save(output_path, format='ICO', sizes=[output_size])
        
        print(f"✅ Icône convertie: {output_path}")
        return output_path
    
    except Exception as e:
        print(f"❌ Erreur lors de la conversion en .ico: {e}")
        return input_path

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

def run_flask_app():
    """Lance le serveur Flask"""
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
        threaded=True,
        use_reloader=False  # Important pour éviter les problèmes avec PyWebView
    )

def run_desktop_app(icon_path):
    """Lance l'application en mode Desktop avec pywebview"""
    try:
        import webview
        print("🖥️ Lancement de l'application en mode Desktop...")

        # Lancer Flask dans un thread séparé
        flask_thread = threading.Thread(target=run_flask_app)
        flask_thread.daemon = True
        flask_thread.start()

        # Attendre que le serveur Flask soit prêt
        import time
        time.sleep(1)
        
        # Créer la fenêtre
        window = webview.create_window(
            title=app.config['APP_NAME'],
            url='http://localhost:5000',
            width=1200,
            height=800,
            resizable=True,
            text_select=True,
            confirm_close=False,
            icon=icon_path
        )
        
        # Démarrer l'application
        webview.start(debug=app.debug)
    except ImportError:
        print("pywebview n'est pas installé. Lancement en mode navigateur uniquement.")
        run_flask_app()
    except Exception as e:
        print(f"❌ Erreur lors du lancement en mode Desktop: {e}")
        run_flask_app()

def run_mobile_app():
    """Configuration pour le mobile"""
    print("📱 Configuration pour mobile détectée")
    # Vous pouvez ajouter ici des configurations spécifiques au mobile
    run_flask_app()


if __name__ == '__main__':
    # Configuration pour le développement
    
    # Définir le répertoire de base pour vos images statiques
    image_dir = os.path.join(os.path.dirname(__file__), 'frontend', 'static', 'images')

    # Définir les noms de fichiers possibles pour l'icône avec différentes extensions
    possible_icons = ['favicon.jpg', 'favicon.png', 'favicon.jpeg']

    icon_jpg_path = None
    for icon_name in possible_icons:
        full_path = os.path.join(image_dir, icon_name)
        if os.path.exists(full_path):
            icon_jpg_path = full_path
            break

    # Chemin vers l'icône original
    if icon_jpg_path:
        print(f"Utilisation de l'icône depuis : {icon_jpg_path}")
    else:
        print("Icône non trouvée avec les extensions .jpg, .png ou .jpeg.")
    
    # Convertir en .ico automatiquement
    icon_path = convert_to_ico(icon_jpg_path)

    # Détection du mode d'exécution
    if '--desktop' in sys.argv:
        run_desktop_app(icon_path)
    elif '--mobile' in sys.argv:
        run_mobile_app()
    else:
        # Mode par défaut (navigateur web)
        run_flask_app()