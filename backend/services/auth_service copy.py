from functools import wraps
from flask import session, jsonify, request, current_app
from backend.models import User
import logging

logger = logging.getLogger(__name__)

def require_auth(f):
    """
    Décorateur pour vérifier l'authentification utilisateur.
    Vérifie si l'utilisateur est connecté via la session.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Vérifier si l'utilisateur est dans la session
        if 'user' not in session:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'AUTHENTICATION_REQUIRED',
                    'message': 'Authentification requise pour accéder à cette ressource'
                }
            }), 401
        
        # Vérifier que les données utilisateur sont valides
        user_data = session.get('user')
        if not user_data or not user_data.get('id'):
            # Session corrompue, la nettoyer
            session.pop('user', None)
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_SESSION',
                    'message': 'Session invalide, veuillez vous reconnecter'
                }
            }), 401
        
        # Vérifier que l'utilisateur existe toujours en base
        try:
            user = User.query.get(user_data['id'])
            if not user or not user.is_active:
                # Utilisateur supprimé ou désactivé
                session.pop('user', None)
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'USER_INACTIVE',
                        'message': 'Compte utilisateur inactif'
                    }
                }), 401
            
            # Mettre à jour la dernière activité
            user.update_last_activity()
            
        except Exception as e:
            logger.error(f"Erreur vérification utilisateur: {str(e)}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'DATABASE_ERROR',
                    'message': 'Erreur de vérification d\'authentification'
                }
            }), 500
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_premium(f):
    """
    Décorateur pour vérifier l'abonnement Premium.
    Vérifie que l'utilisateur est connecté ET a un abonnement Premium actif.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # D'abord vérifier l'authentification
        if 'user' not in session:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'AUTHENTICATION_REQUIRED',
                    'message': 'Authentification requise'
                }
            }), 401
        
        user_data = session.get('user')
        try:
            user = User.query.get(user_data['id'])
            if not user:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'USER_NOT_FOUND',
                        'message': 'Utilisateur non trouvé'
                    }
                }), 404
            
            # Vérifier l'abonnement Premium
            if not hasattr(user, 'subscription') or not user.subscription:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'PREMIUM_REQUIRED',
                        'message': 'Abonnement Premium requis pour cette fonctionnalité',
                        'upgrade_url': '/upgrade'
                    }
                }), 403
            
            if not user.subscription.is_active or user.subscription.plan.name != 'premium':
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'PREMIUM_REQUIRED',
                        'message': 'Abonnement Premium actif requis',
                        'current_plan': user.subscription.plan.name if user.subscription else 'free',
                        'upgrade_url': '/upgrade'
                    }
                }), 403
            
        except Exception as e:
            logger.error(f"Erreur vérification Premium: {str(e)}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'SUBSCRIPTION_CHECK_ERROR',
                    'message': 'Erreur de vérification d\'abonnement'
                }
            }), 500
        
        return f(*args, **kwargs)
    
    return decorated_function

def optional_auth(f):
    """
    Décorateur pour authentification optionnelle.
    La fonction s'exécute que l'utilisateur soit connecté ou non,
    mais ajoute les informations utilisateur si disponibles.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Ajouter les informations utilisateur à la requête si disponibles
        request.current_user = None
        
        if 'user' in session:
            user_data = session.get('user')
            if user_data and user_data.get('id'):
                try:
                    user = User.query.get(user_data['id'])
                    if user and user.is_active:
                        request.current_user = user
                        user.update_last_activity()
                except Exception as e:
                    logger.warning(f"Erreur récupération utilisateur optionnel: {str(e)}")
        
        return f(*args, **kwargs)
    
    return decorated_function

def get_current_user():
    """
    Récupérer l'utilisateur actuellement connecté.
    Retourne None si aucun utilisateur connecté.
    """
    if 'user' not in session:
        return None
    
    user_data = session.get('user')
    if not user_data or not user_data.get('id'):
        return None
    
    try:
        user = User.query.get(user_data['id'])
        if user and user.is_active:
            return user
    except Exception as e:
        logger.error(f"Erreur récupération utilisateur actuel: {str(e)}")
    
    return None

def is_authenticated():
    """
    Vérifier si un utilisateur est authentifié.
    """
    return get_current_user() is not None

def is_premium_user():
    """
    Vérifier si l'utilisateur actuel a un abonnement Premium.
    """
    user = get_current_user()
    if not user:
        return False
    
    try:
        if not hasattr(user, 'subscription') or not user.subscription:
            return False
        
        return (user.subscription.is_active and 
                user.subscription.plan.name == 'premium')
    except Exception:
        return False

def get_user_subscription_type():
    """
    Récupérer le type d'abonnement de l'utilisateur actuel.
    """
    user = get_current_user()
    if not user:
        return 'guest'
    
    try:
        if hasattr(user, 'subscription') and user.subscription and user.subscription.is_active:
            return user.subscription.plan.name
        return 'free'
    except Exception:
        return 'free'

def check_rate_limit(action, user_id=None):
    """
    Vérifier les limites de taux pour une action donnée.
    """
    # Cette fonction peut être étendue avec Redis pour un vrai rate limiting
    # Pour l'instant, on utilise les limites d'abonnement
    
    if not user_id:
        user_data = session.get('user')
        if user_data:
            user_id = user_data.get('id')
    
    if not user_id:
        # Utilisateur invité - limites strictes
        return {
            'allowed': True,  # On laisse passer mais avec restrictions
            'limit': 10,
            'remaining': 10,
            'reset_time': None
        }
    
    try:
        user = User.query.get(user_id)
        if not user:
            return {'allowed': False, 'error': 'Utilisateur non trouvé'}
        
        # Vérifier selon l'abonnement
        if hasattr(user, 'subscription') and user.subscription and user.subscription.is_active:
            subscription = user.subscription
            
            if action == 'search':
                if subscription.plan.daily_searches == -1:  # Illimité
                    return {
                        'allowed': True,
                        'limit': -1,
                        'remaining': -1,
                        'reset_time': None
                    }
                
                allowed = subscription.can_search()
                return {
                    'allowed': allowed,
                    'limit': subscription.plan.daily_searches,
                    'remaining': max(0, subscription.plan.daily_searches - subscription.daily_searches_used),
                    'reset_time': subscription.daily_searches_reset_date
                }
        
        # Utilisateur gratuit
        return {
            'allowed': True,
            'limit': 50,
            'remaining': 50,  # Simplifié pour la démo
            'reset_time': None
        }
        
    except Exception as e:
        logger.error(f"Erreur vérification rate limit: {str(e)}")
        return {'allowed': False, 'error': 'Erreur de vérification'}

class AuthService:
    """Service principal d'authentification."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def login_user(self, user_data):
        """
        Connecter un utilisateur (créer la session).
        """
        try:
            # Stocker les informations essentielles en session
            session['user'] = {
                'id': user_data.get('id'),
                'email': user_data.get('email'),
                'name': user_data.get('name'),
                'avatar_url': user_data.get('avatar_url'),
                'google_id': user_data.get('google_id')
            }
            
            # Configuration de sécurité de session
            session.permanent = True
            
            self.logger.info(f"Utilisateur connecté: {user_data.get('email')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur connexion utilisateur: {str(e)}")
            return False
    
    def logout_user(self):
        """
        Déconnecter un utilisateur (supprimer la session).
        """
        try:
            user_email = session.get('user', {}).get('email', 'Unknown')
            session.pop('user', None)
            
            # Nettoyer d'autres données de session si nécessaire
            session.pop('oauth_state', None)
            
            self.logger.info(f"Utilisateur déconnecté: {user_email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur déconnexion: {str(e)}")
            return False
    
    def create_or_update_user(self, google_user_info):
        """
        Créer ou mettre à jour un utilisateur depuis les infos Google.
        """
        try:
            from backend.models import db, User
            
            # Chercher l'utilisateur existant
            user = User.query.filter_by(
                google_id=google_user_info.get('id')
            ).first()
            
            if not user:
                # Vérifier si un utilisateur existe avec le même email
                user = User.query.filter_by(
                    email=google_user_info.get('email')
                ).first()
                
                if user:
                    # Associer le Google ID à l'utilisateur existant
                    user.google_id = google_user_info.get('id')
                else:
                    # Créer un nouvel utilisateur
                    user = User(
                        email=google_user_info.get('email'),
                        name=google_user_info.get('name'),
                        google_id=google_user_info.get('id'),
                        avatar_url=google_user_info.get('picture')
                    )
                    db.session.add(user)
            else:
                # Mettre à jour les informations existantes
                user.name = google_user_info.get('name', user.name)
                user.avatar_url = google_user_info.get('picture', user.avatar_url)
                user.update_last_activity()
            
            db.session.commit()
            return user
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Erreur création/mise à jour utilisateur: {str(e)}")
            return None
    
    def get_user_context(self):
        """
        Récupérer le contexte utilisateur pour les templates.
        """
        user = get_current_user()
        if not user:
            return {
                'is_authenticated': False,
                'is_anonymous': True,
                'subscription_type': 'guest'
            }
        
        return {
            'is_authenticated': True,
            'is_anonymous': False,
            'user': user,
            'subscription_type': get_user_subscription_type(),
            'is_premium': is_premium_user()
        }

# Instance globale du service
auth_service = AuthService()