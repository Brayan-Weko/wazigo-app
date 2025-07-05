from functools import wraps
from flask import session, request, jsonify, redirect, url_for, flash, current_app, g
from backend.models import User
import time
from typing import Dict, Optional, Callable, Any
import logging
from datetime import datetime, timedelta
import hashlib
import json

# Configuration du rate limiting (en production, utiliser Redis)
_rate_limit_store = {}
_rate_limit_cleanup_last = time.time()

def login_required(f: Callable) -> Callable:
    """Décorateur pour exiger une authentification obligatoire"""
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentification requise'}), 401
            else:
                flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
                session['next_page'] = request.url
                return redirect(url_for('auth.login'))
        
        # Vérifier que l'utilisateur existe toujours en base
        user_id = session['user']['id']
        user = User.get_by_id(user_id)
        
        if not user or not user.is_active:
            session.pop('user', None)
            if request.is_json:
                return jsonify({'error': 'Session invalide'}), 401
            else:
                flash('Votre session a expiré. Veuillez vous reconnecter.', 'error')
                return redirect(url_for('auth.login'))
        
        # Mettre à jour la dernière activité
        user.update_last_activity()
        
        # Injecter l'utilisateur dans le contexte
        g.current_user = user
        
        return f(*args, **kwargs)
    
    return decorated_function

def optional_login_required(f: Callable) -> Callable:
    """Décorateur pour une authentification optionnelle (enrichit le contexte si connecté)"""
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.current_user = None
        
        if 'user' in session:
            user_id = session['user']['id']
            user = User.get_by_id(user_id)
            
            if user and user.is_active:
                user.update_last_activity()
                g.current_user = user
            else:
                # Nettoyer la session si l'utilisateur n'existe plus
                session.pop('user', None)
        
        return f(*args, **kwargs)
    
    return decorated_function

def api_login_required(f: Callable) -> Callable:
    """Décorateur pour les API nécessitant une authentification"""
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({
                'error': 'Authentification requise',
                'code': 'AUTH_REQUIRED'
            }), 401
        
        user_id = session['user']['id']
        user = User.get_by_id(user_id)
        
        if not user or not user.is_active:
            session.pop('user', None)
            return jsonify({
                'error': 'Session invalide',
                'code': 'INVALID_SESSION'
            }), 401
        
        # Mettre à jour l'activité et injecter dans le contexte
        user.update_last_activity()
        g.current_user = user
        
        return f(*args, **kwargs)
    
    return decorated_function

def rate_limit(limit_string: str, per_ip: bool = True, per_user: bool = False, 
               key_func: Optional[Callable] = None):
    """
    Décorateur de rate limiting
    
    Args:
        limit_string: Format "X per Y" (ex: "100 per hour", "10 per minute")
        per_ip: Appliquer la limite par IP
        per_user: Appliquer la limite par utilisateur connecté
        key_func: Fonction personnalisée pour générer la clé de cache
    """
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Parser la limite
            try:
                limit_parts = limit_string.split(' per ')
                max_requests = int(limit_parts[0])
                period = limit_parts[1]
                
                # Convertir la période en secondes
                period_seconds = _parse_period(period)
            except (ValueError, IndexError):
                current_app.logger.error(f"Format de rate limit invalide: {limit_string}")
                return f(*args, **kwargs)
            
            # Générer la clé de rate limiting
            if key_func:
                key = key_func()
            else:
                key_parts = []
                
                if per_ip:
                    ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
                    key_parts.append(f"ip:{ip}")
                
                if per_user and 'user' in session:
                    key_parts.append(f"user:{session['user']['id']}")
                
                if not key_parts:
                    key_parts.append("global")
                
                key = f"{f.__name__}:" + ":".join(key_parts)
            
            # Vérifier et mettre à jour le rate limit
            if _check_rate_limit(key, max_requests, period_seconds):
                return f(*args, **kwargs)
            else:
                if request.is_json:
                    return jsonify({
                        'error': 'Trop de requêtes',
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'retry_after': period_seconds
                    }), 429
                else:
                    flash('Trop de requêtes. Veuillez patienter.', 'error')
                    return redirect(request.referrer or url_for('main.index'))
        
        return decorated_function
    
    return decorator

def admin_required(f: Callable) -> Callable:
    """Décorateur pour exiger des privilèges administrateur"""
    
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        user = g.current_user
        
        # Vérifier les privilèges admin (à adapter selon votre logique)
        if not _is_admin_user(user):
            if request.is_json:
                return jsonify({
                    'error': 'Privilèges administrateur requis',
                    'code': 'ADMIN_REQUIRED'
                }), 403
            else:
                flash('Accès non autorisé.', 'error')
                return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    
    return decorated_function

def validate_json(required_fields: list = None, optional_fields: list = None):
    """Décorateur pour valider les données JSON d'une requête"""
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'error': 'Content-Type application/json requis',
                    'code': 'INVALID_CONTENT_TYPE'
                }), 400
            
            data = request.get_json()
            if not data:
                return jsonify({
                    'error': 'Corps JSON requis',
                    'code': 'MISSING_JSON_BODY'
                }), 400
            
            # Vérifier les champs requis
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return jsonify({
                        'error': f'Champs requis manquants: {", ".join(missing_fields)}',
                        'code': 'MISSING_REQUIRED_FIELDS',
                        'missing_fields': missing_fields
                    }), 400
            
            # Vérifier les champs non autorisés
            if optional_fields is not None:
                allowed_fields = (required_fields or []) + optional_fields
                extra_fields = [field for field in data.keys() if field not in allowed_fields]
                if extra_fields:
                    return jsonify({
                        'error': f'Champs non autorisés: {", ".join(extra_fields)}',
                        'code': 'INVALID_FIELDS',
                        'extra_fields': extra_fields
                    }), 400
            
            # Injecter les données validées dans le contexte
            g.validated_data = data
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator

def cache_response(timeout: int = 300, vary_on: list = None, condition: Callable = None):
    """Décorateur pour mettre en cache les réponses"""
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Vérifier la condition de cache
            if condition and not condition():
                return f(*args, **kwargs)
            
            # Générer la clé de cache
            cache_key_parts = [f.__name__]
            
            if vary_on:
                for param in vary_on:
                    if param in request.args:
                        cache_key_parts.append(f"{param}:{request.args[param]}")
                    elif param == 'user' and 'user' in session:
                        cache_key_parts.append(f"user:{session['user']['id']}")
            
            cache_key = "response:" + ":".join(cache_key_parts)
            cache_key_hash = hashlib.md5(cache_key.encode()).hexdigest()
            
            # Vérifier le cache (simulation - en production utiliser Redis)
            cached_response = _get_cached_response(cache_key_hash)
            if cached_response:
                return cached_response
            
            # Exécuter la fonction et mettre en cache
            response = f(*args, **kwargs)
            _set_cached_response(cache_key_hash, response, timeout)
            
            return response
        
        return decorated_function
    
    return decorator

def log_activity(activity_type: str, include_ip: bool = True, include_user: bool = True):
    """Décorateur pour loguer l'activité utilisateur"""
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            # Préparer les données de log
            log_data = {
                'activity_type': activity_type,
                'function': f.__name__,
                'timestamp': datetime.utcnow().isoformat(),
                'method': request.method,
                'endpoint': request.endpoint,
                'url': request.url
            }
            
            if include_ip:
                log_data['ip_address'] = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
                log_data['user_agent'] = request.user_agent.string
            
            if include_user and 'user' in session:
                log_data['user_id'] = session['user']['id']
                log_data['user_email'] = session['user']['email']
            
            try:
                # Exécuter la fonction
                result = f(*args, **kwargs)
                
                # Ajouter les détails de succès
                log_data['success'] = True
                log_data['execution_time_ms'] = round((time.time() - start_time) * 1000, 2)
                
                # Logger l'activité
                current_app.logger.info(f"Activity: {json.dumps(log_data)}")
                
                return result
                
            except Exception as e:
                # Logger l'erreur
                log_data['success'] = False
                log_data['error'] = str(e)
                log_data['execution_time_ms'] = round((time.time() - start_time) * 1000, 2)
                
                current_app.logger.error(f"Activity Error: {json.dumps(log_data)}")
                raise
        
        return decorated_function
    
    return decorator

def measure_performance(threshold_ms: int = 1000, log_slow: bool = True):
    """Décorateur pour mesurer les performances des fonctions"""
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Logger si lent
                if log_slow and execution_time_ms > threshold_ms:
                    current_app.logger.warning(
                        f"Slow function: {f.__name__} took {execution_time_ms:.2f}ms "
                        f"(threshold: {threshold_ms}ms)"
                    )
                
                # Ajouter les métriques à la réponse si DEBUG
                if current_app.debug and hasattr(result, 'headers'):
                    result.headers['X-Execution-Time'] = f"{execution_time_ms:.2f}ms"
                
                return result
                
            except Exception as e:
                execution_time_ms = (time.time() - start_time) * 1000
                current_app.logger.error(
                    f"Function {f.__name__} failed after {execution_time_ms:.2f}ms: {str(e)}"
                )
                raise
        
        return decorated_function
    
    return decorator

# Fonctions utilitaires privées

def _parse_period(period: str) -> int:
    """Convertir une période en secondes"""
    period_map = {
        'second': 1,
        'minute': 60,
        'hour': 3600,
        'day': 86400
    }
    
    for unit, seconds in period_map.items():
        if unit in period:
            return seconds
    
    return 3600  # Default: 1 heure

def _check_rate_limit(key: str, max_requests: int, period_seconds: int) -> bool:
    """Vérifier et mettre à jour le rate limit"""
    global _rate_limit_store, _rate_limit_cleanup_last
    
    current_time = time.time()
    
    # Nettoyage périodique du store (toutes les 5 minutes)
    if current_time - _rate_limit_cleanup_last > 300:
        _cleanup_rate_limit_store()
        _rate_limit_cleanup_last = current_time
    
    # Récupérer les données existantes
    if key not in _rate_limit_store:
        _rate_limit_store[key] = []
    
    requests = _rate_limit_store[key]
    
    # Supprimer les requêtes expirées
    cutoff_time = current_time - period_seconds
    requests[:] = [req_time for req_time in requests if req_time > cutoff_time]
    
    # Vérifier la limite
    if len(requests) >= max_requests:
        return False
    
    # Ajouter la requête actuelle
    requests.append(current_time)
    return True

def _cleanup_rate_limit_store():
    """Nettoyer le store de rate limiting"""
    global _rate_limit_store
    
    current_time = time.time()
    cutoff_time = current_time - 86400  # Garder 24h de données
    
    keys_to_remove = []
    for key, requests in _rate_limit_store.items():
        # Supprimer les clés avec seulement des requêtes expirées
        if not any(req_time > cutoff_time for req_time in requests):
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del _rate_limit_store[key]

def _is_admin_user(user) -> bool:
    """Vérifier si un utilisateur est administrateur"""
    # Logique d'admin à adapter selon vos besoins
    admin_emails = current_app.config.get('ADMIN_EMAILS', [])
    return user.email in admin_emails

def _get_cached_response(cache_key: str):
    """Récupérer une réponse du cache (simulation)"""
    # En production, utiliser Redis ou Memcached
    return None

def _set_cached_response(cache_key: str, response, timeout: int):
    """Mettre une réponse en cache (simulation)"""
    # En production, utiliser Redis ou Memcached
    pass