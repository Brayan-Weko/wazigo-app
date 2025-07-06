import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

class Config:
    """Configuration de base de l'application"""
    
    # Configuration Flask
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    # Configuration de la base de données MySQL
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'smart_route_db')
    
    # URI de connexion SQLAlchemy
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {
            'connect_timeout': 30,
            'read_timeout': 30,
            'write_timeout': 30
        }
    }
    
    # Configuration HERE Maps API
    HERE_API_KEY = os.environ.get('HERE_API_KEY')
    HERE_BASE_URL = 'https://router.hereapi.com/v8'
    HERE_GEOCODING_URL = 'https://geocode.search.hereapi.com/v1'
    HERE_TRAFFIC_URL = 'https://data.traffic.hereapi.com/v7/flow'
    
    # Configuration Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid_configuration"
    GOOGLE_AUTH_USE_HTTPS = False
    GOOGLE_OAUTH_REDIRECT_URI = 'http://localhost:5000/auth/callback'
    GOOGLE_OAUTH_ALLOWED_ORIGINS = [
        'http://localhost:5000',
        'http://127.0.0.1:5000'
    ]
    
    # Configuration session
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_FILE_DIR = './sessions'
    
    # Configuration Redis (cache)
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    
    # Configuration de l'application
    APP_NAME = os.environ.get('APP_NAME', 'Smart Route')
    APP_URL = os.environ.get('APP_URL', 'http://localhost:5000')
    
    # Paramètres de l'algorithme d'optimisation
    ROUTE_OPTIMIZATION = {
        'max_alternatives': 5,
        'traffic_weight': 0.4,
        'distance_weight': 0.3,
        'time_weight': 0.3,
        'incident_penalty': 0.2,
        'cache_duration': 300  # 5 minutes
    }
    
    # Paramètres de rate limiting
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_DEFAULT = "100 per hour"
    
    # Configuration logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = 'logs/smart_route.log'

class DevelopmentConfig(Config):
    """Configuration pour développement"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Configuration pour production"""
    DEBUG = False
    TESTING = False
    
    # Sécurité renforcée en production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class TestingConfig(Config):
    """Configuration pour les tests"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Dictionnaire de configuration
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}