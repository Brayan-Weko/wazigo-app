from .database import db, DatabaseMixin
from datetime import datetime, timedelta

class UserAnalytics(DatabaseMixin, db.Model):
    """Modèle pour les analytics des utilisateurs"""
    
    __tablename__ = 'user_analytics'
    __table_args__ = {'extend_existing': True}
    
    # Relation avec l'utilisateur
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Métriques globales
    total_routes_searched = db.Column(db.Integer, default=0, nullable=False)
    total_time_saved_minutes = db.Column(db.Integer, default=0, nullable=False)
    total_distance_km = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    
    # Préférences déduites
    most_used_origin = db.Column(db.Text, nullable=True)
    most_used_destination = db.Column(db.Text, nullable=True)
    average_optimization_score = db.Column(db.Numeric(5, 2), default=0, nullable=False)
    
    # Activité
    last_activity = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Périodes d'activité (pour détecter les patterns)
    peak_hours = db.Column(db.String(250), nullable=True)  # ex: "8-9,17-18"
    preferred_days = db.Column(db.String(250), nullable=True)  # ex: "1,2,3,4,5" (lun-ven)
    
    def __init__(self, user_id):
        self.user_id = user_id
    
    def __repr__(self):
        return f'<UserAnalytics User {self.user_id}>'
    
    @classmethod
    def get_or_create(cls, user_id):
        """Récupérer ou créer les analytics d'un utilisateur"""
        analytics = cls.query.filter_by(user_id=user_id).first()
        if not analytics:
            analytics = cls(user_id=user_id)
            analytics.save()
        return analytics
    
    def update_from_route_history(self):
        """Mettre à jour les analytics à partir de l'historique"""
        from .history import RouteHistory
        
        # Récupérer tous les trajets de l'utilisateur
        routes = RouteHistory.query.filter_by(user_id=self.user_id).all()
        
        if not routes:
            return
        
        # Calculs de base
        self.total_routes_searched = len(routes)
        self.total_time_saved_minutes = sum(r.time_saved_seconds for r in routes) // 60
        self.total_distance_km = sum(r.distance_meters for r in routes) / 1000
        self.average_optimization_score = sum(r.optimization_score for r in routes) / len(routes)
        
        # Origines et destinations les plus fréquentes
        origins = [r.origin_address for r in routes]
        destinations = [r.destination_address for r in routes]
        
        if origins:
            self.most_used_origin = max(set(origins), key=origins.count)
        if destinations:
            self.most_used_destination = max(set(destinations), key=destinations.count)
        
        # Analyse des heures de pointe
        self.peak_hours = self._calculate_peak_hours(routes)
        self.preferred_days = self._calculate_preferred_days(routes)
        
        self.last_activity = datetime.utcnow()
        self.save()
    
    def _calculate_peak_hours(self, routes):
        """Calculer les heures de pointe de l'utilisateur"""
        if not routes:
            return None
        
        # Compter les recherches par heure
        hour_counts = {}
        for route in routes:
            hour = route.created_at.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        # Trouver les heures avec le plus d'activité (> moyenne + écart-type)
        if not hour_counts:
            return None
        
        average = sum(hour_counts.values()) / len(hour_counts)
        peak_hours = [str(hour) for hour, count in hour_counts.items() if count > average * 1.5]
        
        return ','.join(sorted(peak_hours)) if peak_hours else None
    
    def _calculate_preferred_days(self, routes):
        """Calculer les jours préférés de l'utilisateur"""
        if not routes:
            return None
        
        # Compter les recherches par jour de la semaine (0=lundi, 6=dimanche)
        day_counts = {}
        for route in routes:
            day = route.created_at.weekday()
            day_counts[day] = day_counts.get(day, 0) + 1
        
        if not day_counts:
            return None
        
        # Trouver les jours avec le plus d'activité
        average = sum(day_counts.values()) / len(day_counts)
        preferred_days = [str(day) for day, count in day_counts.items() if count > average]
        
        return ','.join(sorted(preferred_days)) if preferred_days else None
    
    def get_weekly_stats(self):
        """Récupérer les statistiques de la semaine dernière"""
        from .history import RouteHistory
        
        week_ago = datetime.utcnow() - timedelta(days=7)
        routes = (RouteHistory.query
                 .filter_by(user_id=self.user_id)
                 .filter(RouteHistory.created_at >= week_ago)
                 .all())
        
        if not routes:
            return {
                'routes_count': 0,
                'time_saved_minutes': 0,
                'distance_km': 0,
                'average_score': 0
            }
        
        return {
            'routes_count': len(routes),
            'time_saved_minutes': sum(r.time_saved_seconds for r in routes) // 60,
            'distance_km': round(sum(r.distance_meters for r in routes) / 1000, 1),
            'average_score': round(sum(r.optimization_score for r in routes) / len(routes), 2)
        }
    
    def get_monthly_trends(self, months=6):
        """Récupérer les tendances mensuelles"""
        from .history import RouteHistory
        
        trends = []
        for i in range(months):
            start_date = datetime.utcnow().replace(day=1) - timedelta(days=30*i)
            end_date = start_date + timedelta(days=30)
            
            routes = (RouteHistory.query
                     .filter_by(user_id=self.user_id)
                     .filter(RouteHistory.created_at.between(start_date, end_date))
                     .all())
            
            trends.append({
                'month': start_date.strftime('%Y-%m'),
                'routes_count': len(routes),
                'time_saved_minutes': sum(r.time_saved_seconds for r in routes) // 60 if routes else 0,
                'distance_km': round(sum(r.distance_meters for r in routes) / 1000, 1) if routes else 0
            })
        
        return list(reversed(trends))
    
    def get_efficiency_score(self):
        """Calculer un score d'efficacité global"""
        if self.total_routes_searched == 0:
            return 0
        
        # Score basé sur l'optimisation moyenne et l'activité
        base_score = float(self.average_optimization_score) * 10  # Sur 100
        
        # Bonus pour l'utilisation régulière
        if self.total_routes_searched > 10:
            base_score += 10
        if self.total_routes_searched > 50:
            base_score += 10
        
        # Bonus pour le temps économisé
        if self.total_time_saved_minutes > 60:  # Plus d'1h économisée
            base_score += 5
        
        return min(100, max(0, round(base_score)))
    
    def to_dict(self):
        """Convertir en dictionnaire"""
        return {
            'user_id': self.user_id,
            'total_routes_searched': self.total_routes_searched,
            'total_time_saved_minutes': self.total_time_saved_minutes,
            'total_distance_km': float(self.total_distance_km),
            'weekly_stats': self.get_weekly_stats(),
            'most_used_origin': self.most_used_origin,
            'most_used_destination': self.most_used_destination,
            'average_optimization_score': float(self.average_optimization_score),
            'peak_hours': self.peak_hours.split(',') if self.peak_hours else [],
            'preferred_days': [int(d) for d in self.preferred_days.split(',')] if self.preferred_days else [],
            'efficiency_score': self.get_efficiency_score(),
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }