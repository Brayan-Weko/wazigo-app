from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import logging
from datetime import datetime
import uuid

# Configuration
from .utils import configure_utils
from .config import config
from .extensions import db, sess
from .models.subscription import initialize_subscription_system

def create_app(config_name=None):
    """Factory pour créer l'application Flask"""
    
    app = Flask(__name__, 
                template_folder='../frontend/templates',
                static_folder='../frontend/static')
    
    # Configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Middleware pour proxy (en production)
    if config_name == 'production':
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Initialiser les extensions
    db.init_app(app)
    sess.init_app(app)
    
    # Configuration des logs
    setup_logging(app)
    
    # Créer les dossiers nécessaires
    os.makedirs('logs', exist_ok=True)
    os.makedirs('sessions', exist_ok=True)
    
    # Configurer les utilitaires
    configure_utils(app)
    
    # Enregistrer les blueprints
    register_blueprints(app)
    
    # Gestionnaires d'erreurs
    register_error_handlers(app)
    
    # Context processors
    register_context_processors(app)
    
    # Before/After request handlers
    register_request_handlers(app)
    
    return app

def setup_logging(app):
    """Configuration du système de logs"""
    if not app.debug and not app.testing:
        # Configuration des logs pour production
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s'
        )
        
        file_handler = logging.FileHandler(app.config['LOG_FILE'])
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application Smart Route démarrée')

def register_blueprints(app):
    """Enregistrement des blueprints"""
    
    # Import des routes
    from backend.routes.main import main_bp
    from backend.routes.auth import auth_bp
    from backend.routes.api import api_bp
    from backend.routes.maps import maps_bp
    #from backend.routes.subscription import subscription_bp
    
    # Enregistrement
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(maps_bp, url_prefix='/maps')
    #app.register_blueprint(subscription_bp, url_prefix='/api/subscription')

def register_error_handlers(app):
    """Gestionnaires d'erreurs personnalisés"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

def register_context_processors(app):
    """Processeurs de contexte globaux"""
    
    @app.context_processor
    def inject_config():
        """Injecter des variables de configuration dans les templates"""
        return {
            'app_name': app.config['APP_NAME'],
            'current_year': datetime.now().year,
            'google_client_id': app.config['GOOGLE_CLIENT_ID']
        }
    
    @app.context_processor
    def inject_user():
        """Injecter les informations utilisateur"""
        user_info = session.get('user')
        return {
            'current_user': user_info,
            'is_authenticated': bool(user_info)
        }

def register_request_handlers(app):
    """Handlers pour les requêtes"""
    
    @app.before_request
    def before_request():
        """Exécuté avant chaque requête"""
        # Générer un ID de session pour les utilisateurs anonymes
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        # Log des requêtes en développement
        if app.debug:
            app.logger.info(f"{request.method} {request.path} - IP: {request.remote_addr}")
    
    @app.after_request
    def after_request(response):
        """Exécuté après chaque requête"""
        # Headers de sécurité
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response

# Commandes CLI personnalisées
def register_cli_commands(app):
    """Enregistrer les commandes CLI"""
    
    @app.cli.command()
    def init_db():
        """Initialiser la base de données"""
        db.create_all()
        print("Base de données initialisée !")
    
    @app.cli.command()
    def drop_db():
        """Supprimer toutes les tables"""
        db.drop_all()
        print("Base de données supprimée !")
    
    @app.cli.command()
    def seed_db():
        """Remplir la base avec des données d'exemple"""
        from models.user import User
        
        # Ajouter un utilisateur de test
        test_user = User(
            email='test@smartroute.com',
            name='Utilisateur Test',
            google_id='test_google_id'
        )
        
        db.session.add(test_user)
        db.session.commit()
        print("Données d'exemple ajoutées !")

if __name__ == '__main__':
    app = create_app()
    
    # Enregistrer les commandes CLI
    register_cli_commands(app)
    
    # Créer les tables si elles n'existent pas
    with app.app_context():
        db.create_all()
        success = initialize_subscription_system()
        if success:
            print("🎉 Système d'abonnement prêt !")
        else:
            print("❌ Échec de l'initialisation")
    
    # Lancer l'application
    app.run(host='0.0.0.0', port=5000, debug=True)