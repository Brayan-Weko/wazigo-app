"""
Services de l'application Smart Route

Ce module contient tous les services métier de l'application :
- HereApiService : Intégration avec l'API HERE Maps
- RouteOptimizer : Algorithme d'optimisation des itinéraires
- TrafficAnalyzer : Analyse des conditions de trafic
- GoogleAuthService : Authentification Google OAuth 2.0
"""

from .here_api import HereApiService
from .route_optimizer import RouteOptimizer
from .traffic_analyzer import TrafficAnalyzer
from .google_auth import GoogleAuthService

# Export des services
__all__ = [
    'HereApiService',
    'RouteOptimizer', 
    'TrafficAnalyzer',
    'GoogleAuthService'
]

# Configuration des services par défaut
DEFAULT_SERVICES_CONFIG = {
    'here_api': {
        'cache_ttl': 300,  # 5 minutes
        'timeout': 30,
        'max_alternatives': 5
    },
    'route_optimizer': {
        'traffic_weight': 0.4,
        'distance_weight': 0.3,
        'time_weight': 0.3,
        'incident_penalty': 0.2
    },
    'traffic_analyzer': {
        'analysis_depth': 'detailed',
        'prediction_horizon_hours': 2,
        'critical_threshold': 7
    },
    'google_auth': {
        'scopes': ['openid', 'email', 'profile'],
        'auto_select': False
    }
}

def initialize_services(app):
    """Initialiser tous les services avec l'application Flask"""
    
    with app.app_context():
        try:
            # Test de connectivité HERE API
            here_service = HereApiService()
            here_status = here_service.check_service_status()
            
            # Test de connectivité Google Auth
            google_service = GoogleAuthService()
            google_status = google_service.check_service_availability()
            
            # Validation des configurations
            google_validation = google_service.validate_client_config()
            
            services_status = {
                'here_api': here_status,
                'google_auth': google_status,
                'google_config_valid': google_validation['valid'],
                'initialized': True
            }
            
            app.logger.info("✅ Services initialisés avec succès")
            return services_status
            
        except Exception as e:
            app.logger.error(f"❌ Erreur initialisation services: {str(e)}")
            return {
                'initialized': False,
                'error': str(e)
            }

def get_service_health_check():
    """Vérifier l'état de santé de tous les services"""
    
    health_status = {
        'timestamp': None,
        'overall_status': 'healthy',
        'services': {}
    }
    
    try:
        from datetime import datetime
        health_status['timestamp'] = datetime.utcnow().isoformat()
        
        # Vérifier HERE API
        try:
            here_service = HereApiService()
            here_check = here_service.check_service_status()
            health_status['services']['here_api'] = {
                'status': 'healthy' if all(s == 'operational' for s in here_check.values() if s != here_check.get('last_check')) else 'degraded',
                'details': here_check
            }
        except Exception as e:
            health_status['services']['here_api'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall_status'] = 'degraded'
        
        # Vérifier Google Auth
        try:
            google_service = GoogleAuthService()
            google_check = google_service.check_service_availability()
            health_status['services']['google_auth'] = {
                'status': 'healthy' if google_check['available'] else 'unhealthy',
                'details': google_check
            }
            
            if not google_check['available']:
                health_status['overall_status'] = 'degraded'
                
        except Exception as e:
            health_status['services']['google_auth'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall_status'] = 'degraded'
        
        # Vérifier les autres services
        health_status['services']['route_optimizer'] = {'status': 'healthy'}
        health_status['services']['traffic_analyzer'] = {'status': 'healthy'}
        
    except Exception as e:
        health_status['overall_status'] = 'unhealthy'
        health_status['error'] = str(e)
    
    return health_status