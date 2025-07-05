"""
Utilitaires pour l'application Smart Route

Ce module contient tous les utilitaires, décorateurs, validateurs 
et gestionnaires d'erreurs de l'application.
"""

from datetime import datetime
from .decorators import (
    login_required,
    optional_login_required,
    api_login_required,
    rate_limit,
    admin_required,
    validate_json,
    cache_response,
    log_activity,
    measure_performance
)

from .helpers import (
    generate_session_id,
    generate_secure_token,
    generate_api_key,
    hash_string,
    verify_hash,
    sanitize_filename,
    slugify,
    format_file_size,
    format_duration,
    format_distance,
    format_speed,
    parse_coordinates,
    validate_email,
    validate_phone,
    clean_phone_number,
    mask_sensitive_data,
    mask_email,
    get_client_ip,
    get_user_agent_info,
    paginate_query,
    safe_json_loads,
    safe_int,
    safe_float,
    chunks,
    flatten_dict,
    deep_merge_dicts,
    calculate_distance,
    calculate_bearing,
    is_point_in_bbox,
    generate_bbox,
    debounce_key,
    get_time_ago,
    is_weekend,
    is_business_hours,
    next_business_day,
    truncate_text,
    extract_numbers,
    normalize_whitespace
)

from .validators import (
    ValidationError as ValidatorError,
    Validator,
    StringValidator,
    EmailValidator,
    NumberValidator,
    BooleanValidator,
    DateValidator,
    CoordinatesValidator,
    ListValidator,
    DictValidator,
    URLValidator,
    IPAddressValidator,
    FormValidator,
    validate_route_search,
    validate_user_registration,
    validate_saved_route,
    validate_feedback,
    validate_user_preferences,
    ROUTE_SEARCH_SCHEMA,
    USER_REGISTRATION_SCHEMA,
    SAVED_ROUTE_SCHEMA,
    FEEDBACK_SCHEMA,
    USER_PREFERENCES_SCHEMA
)

from .error_handlers import (
    SmartRouteError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ExternalServiceError,
    ErrorLogger,
    register_error_handlers,
    create_error_response,
    ExceptionContext,
    safe_execute,
    with_error_handling
)

# Export principal
__all__ = [
    # Décorateurs
    'login_required',
    'optional_login_required', 
    'api_login_required',
    'rate_limit',
    'admin_required',
    'validate_json',
    'cache_response',
    'log_activity',
    'measure_performance',
    
    # Helpers
    'generate_session_id',
    'generate_secure_token',
    'generate_api_key',
    'hash_string',
    'verify_hash',
    'sanitize_filename',
    'slugify',
    'format_file_size',
    'format_duration',
    'format_distance',
    'format_speed',
    'parse_coordinates',
    'validate_email',
    'validate_phone',
    'clean_phone_number',
    'mask_sensitive_data',
    'mask_email',
    'get_client_ip',
    'get_user_agent_info',
    'paginate_query',
    'safe_json_loads',
    'safe_int',
    'safe_float',
    'chunks',
    'flatten_dict',
    'deep_merge_dicts',
    'calculate_distance',
    'calculate_bearing',
    'is_point_in_bbox',
    'generate_bbox',
    'debounce_key',
    'get_time_ago',
    'is_weekend',
    'is_business_hours',
    'next_business_day',
    'truncate_text',
    'extract_numbers',
    'normalize_whitespace',
    
    # Validateurs
    'ValidatorError',
    'Validator',
    'StringValidator',
    'EmailValidator',
    'NumberValidator',
    'BooleanValidator',
    'DateValidator',
    'CoordinatesValidator',
    'ListValidator',
    'DictValidator',
    'URLValidator',
    'IPAddressValidator',
    'FormValidator',
    'validate_route_search',
    'validate_user_registration',
    'validate_saved_route',
    'validate_feedback',
    'validate_user_preferences',
    'ROUTE_SEARCH_SCHEMA',
    'USER_REGISTRATION_SCHEMA',
    'SAVED_ROUTE_SCHEMA',
    'FEEDBACK_SCHEMA',
    'USER_PREFERENCES_SCHEMA',
    
    # Gestionnaires d'erreurs
    'SmartRouteError',
    'ValidationError',
    'AuthenticationError',
    'AuthorizationError',
    'NotFoundError',
    'RateLimitError',
    'ExternalServiceError',
    'ErrorLogger',
    'register_error_handlers',
    'create_error_response',
    'ExceptionContext',
    'safe_execute',
    'with_error_handling'
]

# Configuration par défaut des utilitaires
DEFAULT_UTILS_CONFIG = {
    'rate_limiting': {
        'enabled': True,
        'default_limit': '100 per hour',
        'storage': 'memory'  # En production: 'redis'
    },
    'validation': {
        'strict_mode': False,
        'auto_trim_strings': True,
        'max_string_length': 10000
    },
    'error_handling': {
        'log_all_errors': True,
        'include_traceback_in_debug': True,
        'mask_sensitive_data': True
    },
    'caching': {
        'enabled': True,
        'default_timeout': 300,
        'vary_on_user': True
    }
}

def configure_utils(app):
    """Configurer les utilitaires avec l'application Flask"""
    
    # Configuration depuis l'app ou valeurs par défaut
    utils_config = app.config.get('UTILS_CONFIG', DEFAULT_UTILS_CONFIG)
    
    # Enregistrer les gestionnaires d'erreurs
    register_error_handlers(app)
    
    # Configuration du logging pour les erreurs
    if utils_config.get('error_handling', {}).get('log_all_errors', True):
        print("✅ Gestionnaires d'erreurs configurés")
    
    # Ajouter les filtres Jinja2 utiles
    @app.template_filter('format_duration')
    def jinja_format_duration(seconds):
        return format_duration(int(seconds) if seconds else 0)
    
    @app.template_filter('format_distance')
    def jinja_format_distance(meters):
        return format_distance(float(meters) if meters else 0)
    
    @app.template_filter('time_ago')
    def jinja_time_ago(dt):
        return get_time_ago(dt) if dt else 'Jamais'
    
    @app.template_filter('mask_email')
    def jinja_mask_email(email):
        return mask_email(email) if email else ''
    
    @app.template_filter('truncate_smart')
    def jinja_truncate_smart(text, length=100):
        return truncate_text(text, length) if text else ''
    
    print("✅ Utilitaires configurés avec succès")
    
    return utils_config

def get_utils_status():
    """Récupérer le statut des utilitaires"""
    
    return {
        'decorators': 'operational',
        'validators': 'operational',
        'helpers': 'operational',
        'error_handlers': 'operational',
        'last_check': datetime.utcnow().isoformat()
    }