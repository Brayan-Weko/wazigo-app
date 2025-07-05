from flask import jsonify, request, current_app, render_template
from werkzeug.exceptions import HTTPException
import traceback
import logging
from datetime import datetime
from typing import Dict, Any, Tuple
import sys

class SmartRouteError(Exception):
    """Exception de base pour l'application Smart Route"""
    
    def __init__(self, message: str, code: str = None, status_code: int = 400, details: Dict = None):
        self.message = message
        self.code = code or 'SMART_ROUTE_ERROR'
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(SmartRouteError):
    """Erreur de validation"""
    
    def __init__(self, message: str, field: str = None, **kwargs):
        super().__init__(message, code='VALIDATION_ERROR', status_code=400, **kwargs)
        self.field = field

class AuthenticationError(SmartRouteError):
    """Erreur d'authentification"""
    
    def __init__(self, message: str = "Authentification requise", **kwargs):
        super().__init__(message, code='AUTHENTICATION_ERROR', status_code=401, **kwargs)

class AuthorizationError(SmartRouteError):
    """Erreur d'autorisation"""
    
    def __init__(self, message: str = "Accès non autorisé", **kwargs):
        super().__init__(message, code='AUTHORIZATION_ERROR', status_code=403, **kwargs)

class NotFoundError(SmartRouteError):
    """Erreur de ressource non trouvée"""
    
    def __init__(self, message: str = "Ressource non trouvée", **kwargs):
        super().__init__(message, code='NOT_FOUND_ERROR', status_code=404, **kwargs)

class RateLimitError(SmartRouteError):
    """Erreur de limite de taux"""
    
    def __init__(self, message: str = "Trop de requêtes", retry_after: int = None, **kwargs):
        super().__init__(message, code='RATE_LIMIT_ERROR', status_code=429, **kwargs)
        self.retry_after = retry_after

class ExternalServiceError(SmartRouteError):
    """Erreur de service externe"""
    
    def __init__(self, service: str, message: str = None, **kwargs):
        message = message or f"Erreur du service {service}"
        super().__init__(message, code='EXTERNAL_SERVICE_ERROR', status_code=503, **kwargs)
        self.service = service

class ErrorLogger:
    """Gestionnaire de logs d'erreurs"""
    
    def __init__(self):
        self.logger = logging.getLogger('smart_route.errors')
    
    def log_error(self, error: Exception, request_data: Dict = None, user_data: Dict = None):
        """Logger une erreur avec contexte"""
        
        error_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'request_data': request_data or {},
            'user_data': user_data or {}
        }
        
        # Ajouter les détails spécifiques aux erreurs Smart Route
        if isinstance(error, SmartRouteError):
            error_data.update({
                'error_code': error.code,
                'status_code': error.status_code,
                'details': error.details
            })
        
        # Logger selon la sévérité
        if isinstance(error, (AuthenticationError, AuthorizationError, ValidationError)):
            self.logger.warning(f"User Error: {error_data}")
        elif isinstance(error, ExternalServiceError):
            self.logger.error(f"External Service Error: {error_data}")
        else:
            self.logger.error(f"Application Error: {error_data}")

def get_request_context() -> Dict[str, Any]:
    """Récupérer le contexte de la requête pour les logs"""
    try:
        return {
            'method': request.method,
            'url': request.url,
            'endpoint': request.endpoint,
            'remote_addr': request.remote_addr,
            'user_agent': request.user_agent.string,
            'referrer': request.referrer,
            'args': dict(request.args),
            'form_data': dict(request.form) if request.form else None,
            'json_data': request.get_json(silent=True)
        }
    except RuntimeError:
        # Pas de contexte de requête disponible
        return {}

def get_user_context() -> Dict[str, Any]:
    """Récupérer le contexte utilisateur pour les logs"""
    try:
        from flask import session
        user_data = {}
        
        if 'user' in session:
            user_data = {
                'user_id': session['user'].get('id'),
                'user_email': session['user'].get('email'),
                'user_name': session['user'].get('name')
            }
        
        if 'session_id' in session:
            user_data['session_id'] = session['session_id']
        
        return user_data
    except (RuntimeError, KeyError):
        return {}

def create_error_response(error: Exception, include_traceback: bool = False) -> Tuple[Dict, int]:
    """Créer une réponse d'erreur standardisée"""
    
    if isinstance(error, SmartRouteError):
        response_data = {
            'error': {
                'message': error.message,
                'code': error.code,
                'details': error.details
            },
            'success': False,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if isinstance(error, RateLimitError) and error.retry_after:
            response_data['retry_after'] = error.retry_after
        
        return response_data, error.status_code
    
    elif isinstance(error, HTTPException):
        response_data = {
            'error': {
                'message': error.description,
                'code': f'HTTP_{error.code}',
                'details': {}
            },
            'success': False,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return response_data, error.code
    
    else:
        # Erreur inattendue
        message = "Une erreur inattendue s'est produite"
        if current_app.debug:
            message = str(error)
        
        response_data = {
            'error': {
                'message': message,
                'code': 'INTERNAL_ERROR',
                'details': {}
            },
            'success': False,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if include_traceback and current_app.debug:
            response_data['error']['traceback'] = traceback.format_exc()
        
        return response_data, 500

def register_error_handlers(app):
    """Enregistrer tous les gestionnaires d'erreurs"""
    
    error_logger = ErrorLogger()
    
    @app.errorhandler(SmartRouteError)
    def handle_smart_route_error(error: SmartRouteError):
        """Gestionnaire pour les erreurs Smart Route"""
        
        # Logger l'erreur
        error_logger.log_error(error, get_request_context(), get_user_context())
        
        # Réponse JSON ou HTML selon le type de requête
        if request.is_json or request.endpoint and request.endpoint.startswith('api.'):
            response_data, status_code = create_error_response(error)
            return jsonify(response_data), status_code
        else:
            # Affichage HTML avec template d'erreur
            if error.status_code == 404:
                return render_template('errors/404.html', error=error), 404
            elif error.status_code == 403:
                return render_template('errors/403.html', error=error), 403
            else:
                return render_template('errors/generic.html', error=error), error.status_code
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        """Gestionnaire spécifique pour les erreurs de validation"""
        
        if request.is_json:
            response_data = {
                'error': {
                    'message': error.message,
                    'code': error.code,
                    'field': error.field,
                    'details': error.details
                },
                'success': False,
                'timestamp': datetime.utcnow().isoformat()
            }
            return jsonify(response_data), 400
        else:
            from flask import flash, redirect, url_for
            flash(error.message, 'error')
            return redirect(request.referrer or url_for('main.index'))
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Gestionnaire pour les erreurs 404"""
        
        if request.is_json:
            return jsonify({
                'error': {
                    'message': 'Endpoint non trouvé',
                    'code': 'NOT_FOUND',
                    'details': {'endpoint': request.endpoint, 'method': request.method}
                },
                'success': False
            }), 404
        else:
            return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """Gestionnaire pour les erreurs internes"""
        
        # Logger l'erreur
        error_logger.log_error(error, get_request_context(), get_user_context())
        
        # Rollback de la base de données si nécessaire
        try:
            from models import db
            db.session.rollback()
        except:
            pass
        
        if request.is_json:
            response_data, status_code = create_error_response(error, include_traceback=app.debug)
            return jsonify(response_data), status_code
        else:
            return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def handle_forbidden(error):
        """Gestionnaire pour les erreurs 403"""
        
        if request.is_json:
            return jsonify({
                'error': {
                    'message': 'Accès interdit',
                    'code': 'FORBIDDEN',
                    'details': {}
                },
                'success': False
            }), 403
        else:
            return render_template('errors/403.html'), 403
    
    @app.errorhandler(429)
    def handle_rate_limit(error):
        """Gestionnaire pour les erreurs de rate limit"""
        
        retry_after = getattr(error, 'retry_after', 60)
        
        response_data = {
            'error': {
                'message': 'Trop de requêtes. Veuillez patienter.',
                'code': 'RATE_LIMIT_EXCEEDED',
                'details': {'retry_after': retry_after}
            },
            'success': False,
            'retry_after': retry_after
        }
        
        if request.is_json:
            return jsonify(response_data), 429
        else:
            from flask import flash, redirect, url_for
            flash('Trop de requêtes. Veuillez patienter quelques instants.', 'warning')
            return redirect(url_for('main.index'))
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Gestionnaire pour toutes les autres erreurs"""
        
        # Logger l'erreur
        error_logger.log_error(error, get_request_context(), get_user_context())
        
        # Rollback de la base de données
        try:
            from models import db
            db.session.rollback()
        except:
            pass
        
        # En mode debug, laisser l'erreur remonter
        if app.debug:
            raise error
        
        # Sinon, retourner une erreur générique
        if request.is_json:
            return jsonify({
                'error': {
                    'message': 'Une erreur inattendue s\'est produite',
                    'code': 'INTERNAL_ERROR',
                    'details': {}
                },
                'success': False
            }), 500
        else:
            return render_template('errors/500.html'), 500

class ExceptionContext:
    """Context manager pour capturer et traiter les exceptions"""
    
    def __init__(self, logger: ErrorLogger = None, reraise: bool = True):
        self.logger = logger or ErrorLogger()
        self.reraise = reraise
        self.error = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error = exc_val
            self.logger.log_error(exc_val, get_request_context(), get_user_context())
            
            if not self.reraise:
                return True  # Supprime l'exception
        
        return False

def safe_execute(func, *args, **kwargs):
    """Exécuter une fonction de manière sécurisée avec gestion d'erreurs"""
    
    try:
        return func(*args, **kwargs), None
    except Exception as e:
        error_logger = ErrorLogger()
        error_logger.log_error(e, get_request_context(), get_user_context())
        return None, e

def with_error_handling(error_return_value=None, log_errors=True):
    """Décorateur pour la gestion d'erreurs"""
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    error_logger = ErrorLogger()
                    error_logger.log_error(e, get_request_context(), get_user_context())
                
                if error_return_value is not None:
                    return error_return_value
                else:
                    raise
        
        return wrapper
    return decorator