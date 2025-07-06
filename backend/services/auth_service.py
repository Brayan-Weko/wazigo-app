from functools import wraps
from flask import session, jsonify, current_app
from backend.models import User
import logging

logger = logging.getLogger(__name__)

def require_auth(f):
    """Décorateur pour vérifier l'authentification utilisateur."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'AUTHENTICATION_REQUIRED',
                    'message': 'Authentification requise'
                }
            }), 401
        
        user_data = session.get('user')
        if not user_data or not user_data.get('id'):
            session.pop('user', None)
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_SESSION',
                    'message': 'Session invalide'
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

def optional_auth(f):
    """Décorateur pour authentification optionnelle."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Récupérer l'utilisateur actuellement connecté."""
    if 'user' not in session:
        return None
    
    user_data = session.get('user')
    if not user_data or not user_data.get('id'):
        return None
    
    try:
        user = User.get_by_id(user_data['id'])
        return user if user and user.is_active else None
    except Exception as e:
        logger.error(f"Erreur récupération utilisateur: {str(e)}")
        return None

def is_premium_user():
    """Vérifier si l'utilisateur actuel est premium."""
    user = get_current_user()
    return user and user.is_premium if user else False