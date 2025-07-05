from datetime import datetime
from .analytics import UserAnalytics
from .history import RouteHistory
from .database import db, DatabaseMixin, JSONColumn

class User(DatabaseMixin, db.Model):
    """Modèle pour les utilisateurs de l'application"""
    
    __tablename__ = 'users'
    
    # Colonnes principales
    google_id = db.Column(db.String(250), unique=True, nullable=True, index=True)
    email = db.Column(db.String(250), unique=True, nullable=False, index=True)
    name = db.Column(db.String(250), nullable=False)
    avatar_url = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Préférences utilisateur (stockées en JSON)
    preferences = db.Column(JSONColumn, nullable=True)
    
    # Dernière activité
    last_login = db.Column(db.DateTime, nullable=True)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    saved_routes = db.relationship('SavedRoute', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    route_history = db.relationship('RouteHistory', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    analytics = db.relationship('UserAnalytics', backref='user', uselist=False, cascade='all, delete-orphan')
    feedback = db.relationship('Feedback', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    subscription = db.relationship('UserSubscription', back_populates='user', uselist=False, cascade='all, delete-orphan')
    
    def __init__(self, email, name, google_id=None, avatar_url=None):
        self.email = email
        self.name = name
        self.google_id = google_id
        self.avatar_url = avatar_url
        self.preferences = self.get_default_preferences()
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    @staticmethod
    def get_default_preferences():
        """Préférences par défaut pour un nouvel utilisateur"""
        return {
            'route_preferences': {
                'avoid_tolls': False,
                'avoid_highways': False,
                'avoid_ferries': False,
                'prefer_fastest': True
            },
            'notifications': {
                'traffic_alerts': True,
                'route_suggestions': True,
                'email_updates': False
            },
            'display': {
                'units': 'metric',  # metric ou imperial
                'language': 'fr',
                'theme': 'auto'  # light, dark, auto
            },
            'privacy': {
                'save_history': True,
                'share_analytics': False
            }
        }
    
    @classmethod
    def find_by_email(cls, email):
        """Trouver un utilisateur par email"""
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def find_by_google_id(cls, google_id):
        """Trouver un utilisateur par Google ID"""
        return cls.query.filter_by(google_id=google_id).first()
    
    @classmethod
    def create_from_google(cls, google_user_info):
        """Créer un utilisateur à partir des infos Google"""
        user = cls(
            email=google_user_info.get('email'),
            name=google_user_info.get('name'),
            google_id=google_user_info.get('sub'),
            avatar_url=google_user_info.get('picture')
        )
        return user
    
    def update_last_activity(self):
        """Mettre à jour la dernière activité"""
        self.last_activity = datetime.utcnow()
        self.save()
    
    def update_preferences(self, new_preferences):
        """Mettre à jour les préférences utilisateur"""
        if self.preferences:
            # Fusionner avec les préférences existantes
            for key, value in new_preferences.items():
                if isinstance(value, dict) and key in self.preferences:
                    self.preferences[key].update(value)
                else:
                    self.preferences[key] = value
        else:
            self.preferences = new_preferences
        self.save()
    
    def get_favorite_routes(self):
        """Récupérer les itinéraires favoris"""
        return self.saved_routes.filter_by(is_favorite=True).all()
    
    def get_recent_routes(self, limit=10):
        """Récupérer les itinéraires récents"""
        return (self.route_history
                .order_by(RouteHistory.created_at.desc())
                .limit(limit)
                .all())
    
    def get_analytics_summary(self):
        """Récupérer un résumé des analytics utilisateur"""
        if not self.analytics:
            # Créer les analytics si elles n'existent pas
            analytics = UserAnalytics(user_id=self.id)
            analytics.save()
            return analytics
        return self.analytics
    
    @property
    def subscription_type(self):
        """Type d'abonnement actuel."""
        if self.subscription and self.subscription.is_active:
            return self.subscription.plan.name
        return 'free'

    @property
    def is_premium(self):
        """Vérifier si l'utilisateur est premium."""
        return self.subscription_type == 'premium'

    @property
    def subscription_status(self):
        """Statut détaillé de l'abonnement."""
        if not self.subscription:
            return {
                'type': 'free',
                'active': True,
                'expires_at': None,
                'days_remaining': None
            }
        
        return {
            'type': self.subscription.plan.name,
            'active': self.subscription.is_active,
            'expires_at': self.subscription.expires_at,
            'days_remaining': self.subscription.days_remaining
        }

    def can_access_feature(self, feature):
        """Vérifier l'accès à une fonctionnalité."""
        if not self.subscription or not self.subscription.is_active:
            return False
        return getattr(self.subscription.plan, f'has_{feature}', False)

    def get_subscription_limits(self):
        """Récupérer les limites de l'abonnement."""
        if self.subscription and self.subscription.is_active:
            plan = self.subscription.plan
            return {
                'traffic_radius_km': plan.traffic_radius_km,
                'countries_access': plan.countries_access,
                'daily_searches': plan.daily_searches,
                'daily_searches_used': self.subscription.daily_searches_used,
                'has_ads': plan.has_ads
            }
        
        # Limites par défaut pour utilisateur gratuit
        return {
            'traffic_radius_km': 45,
            'countries_access': 1,
            'daily_searches': 50,
            'daily_searches_used': 0,
            'has_ads': True
        }

    def can_search(self):
        """Vérifier si l'utilisateur peut effectuer une recherche."""
        if self.subscription and self.subscription.is_active:
            return self.subscription.can_search()
        return True  # Utilisateurs gratuits peuvent rechercher (avec limites)

    def to_dict(self, include_sensitive=False, include_subscription=False):
        """Convertir en dictionnaire avec options de sécurité et abonnement."""
        data = {
            'id': self.id,
            'name': self.name,
            'avatar_url': self.avatar_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'subscription_type': self.subscription_type,
            'is_premium': self.is_premium
        }
        
        if include_sensitive:
            data.update({
                'email': self.email,
                'google_id': self.google_id,
                'preferences': self.preferences,
                'is_active': self.is_active
            })
        
        if include_subscription:
            data.update({
                'subscription': self.subscription.to_dict() if self.subscription else None,
                'subscription_status': self.subscription_status,
                'subscription_limits': self.get_subscription_limits()
            })
        
        return data