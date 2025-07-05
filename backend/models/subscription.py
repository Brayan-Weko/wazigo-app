from datetime import datetime, timedelta
from .database import db, DatabaseMixin, JSONColumn
from sqlalchemy.orm import relationship

class SubscriptionPlan(DatabaseMixin, db.Model):
    """Plans d'abonnement disponibles."""
    __tablename__ = 'subscription_plans'

    # Informations générales
    name = db.Column(db.String(50), nullable=False, unique=True)  # 'free', 'premium'
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price_monthly = db.Column(db.Float, default=0.0)  # Prix en USD
    price_yearly = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='USD')
    
    # Limites et fonctionnalités
    traffic_radius_km = db.Column(db.Integer, default=45)  # Rayon trafic en km
    countries_access = db.Column(db.Integer, default=1)  # Nombre de pays
    daily_searches = db.Column(db.Integer, default=50)  # Recherches par jour
    has_ads = db.Column(db.Boolean, default=True)
    has_voice_alerts = db.Column(db.Boolean, default=False)
    has_offline_mode = db.Column(db.Boolean, default=False)
    has_premium_routes = db.Column(db.Boolean, default=False)  # Panoramique, éco
    has_priority_support = db.Column(db.Boolean, default=False)
    
    # Métadonnées
    is_active = db.Column(db.Boolean, default=True)
    
    # Relations
    subscriptions = relationship('UserSubscription', back_populates='plan', lazy='dynamic')

    def __init__(self, name, display_name, **kwargs):
        self.name = name
        self.display_name = display_name
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self):
        return f'<SubscriptionPlan {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'price_monthly': self.price_monthly,
            'price_yearly': self.price_yearly,
            'currency': self.currency,
            'features': {
                'traffic_radius_km': self.traffic_radius_km,
                'countries_access': self.countries_access,
                'daily_searches': self.daily_searches,
                'has_ads': self.has_ads,
                'has_voice_alerts': self.has_voice_alerts,
                'has_offline_mode': self.has_offline_mode,
                'has_premium_routes': self.has_premium_routes,
                'has_priority_support': self.has_priority_support
            },
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def get_plan_by_name(cls, name):
        """Récupérer un plan par son nom."""
        return cls.query.filter_by(name=name, is_active=True).first()

    @classmethod
    def get_active_plans(cls):
        """Récupérer tous les plans actifs."""
        return cls.query.filter_by(is_active=True).all()

class UserSubscription(DatabaseMixin, db.Model):
    """Abonnement d'un utilisateur."""
    __tablename__ = 'user_subscriptions'

    # Relations
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=False)
    
    # Statut de l'abonnement
    status = db.Column(db.String(20), default='active')  # active, cancelled, expired, pending
    billing_period = db.Column(db.String(10), default='monthly')  # monthly, yearly
    
    # Dates
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    
    # Paiement (simulation)
    payment_method = db.Column(db.String(50))  # 'card', 'paypal', 'mobile'
    last_payment_date = db.Column(db.DateTime)
    next_payment_date = db.Column(db.DateTime)
    
    # Utilisation quotidienne
    daily_searches_used = db.Column(db.Integer, default=0)
    daily_searches_reset_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Métadonnées supplémentaires
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = relationship('User', back_populates='subscription')
    plan = relationship('SubscriptionPlan', back_populates='subscriptions')

    def __init__(self, user_id, plan_id, **kwargs):
        self.user_id = user_id
        self.plan_id = plan_id
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self):
        return f'<UserSubscription {self.user_id}:{self.plan.name if self.plan else "Unknown"}>'

    @property
    def is_active(self):
        """Vérifier si l'abonnement est actif."""
        return (self.status == 'active' and 
                (self.expires_at is None or self.expires_at > datetime.utcnow()))

    @property
    def days_remaining(self):
        """Nombre de jours restants."""
        if not self.expires_at:
            return None
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)

    @property
    def is_premium(self):
        """Vérifier si c'est un abonnement premium."""
        return self.plan and self.plan.name == 'premium' and self.is_active

    def can_search(self):
        """Vérifier si l'utilisateur peut effectuer une recherche."""
        # Réinitialiser le compteur quotidien si nécessaire
        self.reset_daily_usage_if_needed()
        
        if not self.plan:
            return False
            
        if self.plan.daily_searches == -1:  # Illimité
            return True
        
        return self.daily_searches_used < self.plan.daily_searches

    def increment_daily_searches(self):
        """Incrémenter le compteur de recherches quotidiennes."""
        self.reset_daily_usage_if_needed()
        self.daily_searches_used += 1
        self.save()

    def reset_daily_usage_if_needed(self):
        """Réinitialiser l'usage quotidien si nécessaire."""
        today = datetime.utcnow().date()
        if self.daily_searches_reset_date.date() < today:
            self.daily_searches_used = 0
            self.daily_searches_reset_date = datetime.utcnow()
            self.save()

    def cancel_subscription(self):
        """Annuler l'abonnement."""
        self.status = 'cancelled'
        self.cancelled_at = datetime.utcnow()
        self.save()

    def reactivate_subscription(self):
        """Réactiver l'abonnement."""
        if self.status == 'cancelled' and self.expires_at and self.expires_at > datetime.utcnow():
            self.status = 'active'
            self.cancelled_at = None
            self.save()

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plan': self.plan.to_dict() if self.plan else None,
            'status': self.status,
            'billing_period': self.billing_period,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'is_active': self.is_active,
            'is_premium': self.is_premium,
            'days_remaining': self.days_remaining,
            'daily_searches_used': self.daily_searches_used,
            'daily_searches_limit': self.plan.daily_searches if self.plan else 0,
            'payment_method': self.payment_method,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Advertisement(DatabaseMixin, db.Model):
    """Publicités pour utilisateurs gratuits."""
    __tablename__ = 'advertisements'

    # Contenu publicitaire
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    click_url = db.Column(db.String(500))
    cta_text = db.Column(db.String(50), default='En savoir plus')  # Call to action
    
    # Ciblage
    target_countries = db.Column(JSONColumn)  # Liste des codes pays
    target_user_types = db.Column(db.String(50), default='free')  # free, guest, all
    
    # Planification
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    
    # Métriques
    impressions = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    
    # Configuration
    priority = db.Column(db.Integer, default=1)  # 1=low, 5=high
    is_active = db.Column(db.Boolean, default=True)
    ad_type = db.Column(db.String(20), default='banner')  # banner, sidebar, popup
    
    # Métadonnées
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, title, **kwargs):
        self.title = title
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self):
        return f'<Advertisement {self.title[:30]}...>'

    def increment_impression(self):
        """Incrémenter le nombre d'impressions."""
        self.impressions += 1
        self.save()

    def increment_click(self):
        """Incrémenter le nombre de clics."""
        self.clicks += 1
        self.save()

    @property
    def ctr(self):
        """Taux de clic (Click Through Rate)."""
        if self.impressions == 0:
            return 0
        return round((self.clicks / self.impressions) * 100, 2)

    @property
    def is_scheduled_active(self):
        """Vérifier si la publicité est active selon la planification."""
        now = datetime.utcnow()
        start_ok = self.start_date <= now
        end_ok = self.end_date is None or self.end_date > now
        return self.is_active and start_ok and end_ok

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'image_url': self.image_url,
            'click_url': self.click_url,
            'cta_text': self.cta_text,
            'ad_type': self.ad_type,
            'impressions': self.impressions,
            'clicks': self.clicks,
            'ctr': self.ctr,
            'target_countries': self.target_countries,
            'target_user_types': self.target_user_types,
            'is_active': self.is_active,
            'is_scheduled_active': self.is_scheduled_active,
            'priority': self.priority,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def get_active_ads(cls, user_type='free', country=None, ad_type=None, limit=10):
        """Récupérer les publicités actives selon les critères."""
        query = cls.query.filter(
            cls.is_active == True,
            cls.start_date <= datetime.utcnow()
        )
        
        # Filtrer par date de fin
        query = query.filter(
            (cls.end_date.is_(None)) | (cls.end_date > datetime.utcnow())
        )
        
        # Filtrer par type d'utilisateur
        if user_type:
            query = query.filter(
                (cls.target_user_types == user_type) | 
                (cls.target_user_types == 'all')
            )
        
        # Filtrer par type de publicité
        if ad_type:
            query = query.filter(cls.ad_type == ad_type)
        
        # Trier par priorité et randomiser un peu
        query = query.order_by(cls.priority.desc(), cls.created_at.desc())
        
        if limit:
            query = query.limit(limit)
            
        return query.all()

# Fonctions d'initialisation
def init_subscription_plans():
    """Créer les plans d'abonnement par défaut."""
    
    # Plan gratuit
    free_plan = SubscriptionPlan.get_plan_by_name('free')
    if not free_plan:
        free_plan = SubscriptionPlan(
            name='free',
            display_name='Gratuit',
            description='Accès de base à Smart Route avec fonctionnalités limitées',
            price_monthly=0.0,
            traffic_radius_km=45,
            countries_access=1,
            daily_searches=50,
            has_ads=True,
            has_voice_alerts=False,
            has_offline_mode=False,
            has_premium_routes=False,
            has_priority_support=False
        )
        free_plan.save()
        print("✅ Plan gratuit créé")

    # Plan premium
    premium_plan = SubscriptionPlan.get_plan_by_name('premium')
    if not premium_plan:
        premium_plan = SubscriptionPlan(
            name='premium',
            display_name='Premium',
            description='Accès complet sans publicité avec toutes les fonctionnalités avancées',
            price_monthly=2.0,
            price_yearly=20.0,
            traffic_radius_km=-1,  # Illimité
            countries_access=-1,   # Illimité
            daily_searches=-1,     # Illimité
            has_ads=False,
            has_voice_alerts=True,
            has_offline_mode=True,
            has_premium_routes=True,
            has_priority_support=True
        )
        premium_plan.save()
        print("✅ Plan premium créé")

def init_default_ads():
    """Créer des publicités de démonstration."""
    
    sample_ads = [
        {
            'title': '🏨 Hôtel Central - Réservez maintenant !',
            'description': 'Profitez de 20% de réduction sur votre prochain séjour dans notre hôtel 4 étoiles au cœur de la ville.',
            'image_url': 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400&h=200&fit=crop',
            'click_url': '#demo-hotel',
            'cta_text': 'Réserver maintenant',
            'ad_type': 'banner',
            'priority': 3
        },
        {
            'title': '🚗 Location AutoPlus - Prix imbattables',
            'description': 'Voitures neuves et entretenues disponibles 24h/24. Livraison gratuite dans un rayon de 10km.',
            'image_url': 'https://images.unsplash.com/photo-1449965408869-eaa3f722e40d?w=400&h=200&fit=crop',
            'click_url': '#demo-rental',
            'cta_text': 'Voir les offres',
            'ad_type': 'sidebar',
            'priority': 4
        },
        {
            'title': '🍕 Restaurant Le Bon Goût',
            'description': 'Cuisine locale authentique préparée avec amour. Livraison gratuite sous 30 minutes.',
            'image_url': 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=400&h=200&fit=crop',
            'click_url': '#demo-restaurant',
            'cta_text': 'Commander',
            'ad_type': 'banner',
            'priority': 2
        },
        {
            'title': '⛽ Station Essence Eco+',
            'description': 'Carburant écologique de qualité premium. Programme de points fidélité avantageux.',
            'image_url': 'https://images.unsplash.com/photo-1545262107-70ec4f821c9d?w=400&h=200&fit=crop',
            'click_url': '#demo-gas',
            'cta_text': 'Localiser',
            'ad_type': 'sidebar',
            'priority': 3
        },
        {
            'title': '🛠️ Garage AutoExpert',
            'description': 'Réparation et entretien automobile par des experts certifiés. Devis gratuit en ligne.',
            'image_url': 'https://images.unsplash.com/photo-1486754735734-325b5831c3ad?w=400&h=200&fit=crop',
            'click_url': '#demo-garage',
            'cta_text': 'Devis gratuit',
            'ad_type': 'banner',
            'priority': 2
        },
        {
            'title': '🏪 SuperMarché Fresh',
            'description': 'Produits frais et locaux sélectionnés. Drive et livraison à domicile disponibles 7j/7.',
            'image_url': 'https://images.unsplash.com/photo-1534723452862-4c874018d66d?w=400&h=200&fit=crop',
            'click_url': '#demo-supermarket',
            'cta_text': 'Faire ses courses',
            'ad_type': 'sidebar',
            'priority': 1
        }
    ]

    ads_created = 0
    for ad_data in sample_ads:
        existing_ad = Advertisement.query.filter_by(title=ad_data['title']).first()
        if not existing_ad:
            ad = Advertisement(**ad_data)
            ad.save()
            ads_created += 1

    if ads_created > 0:
        print(f"✅ {ads_created} publicités de démonstration créées")

def initialize_subscription_system():
    """Initialiser complètement le système d'abonnement."""
    try:
        print("🚀 Initialisation du système d'abonnement...")
        init_subscription_plans()
        init_default_ads()
        print("✅ Système d'abonnement initialisé avec succès")
        return True
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation: {str(e)}")
        return False