from flask import current_app
from .database import db, DatabaseMixin, JSONColumn
from datetime import datetime, timedelta
from sqlalchemy import func, and_

class RouteHistory(DatabaseMixin, db.Model):
    """Modèle pour l'historique des trajets effectués"""
    
    __tablename__ = 'route_history'
    __table_args__ = {'extend_existing': True}
    
    # Relations
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(250), nullable=False, index=True)
    
    # Points de départ et d'arrivée
    origin_address = db.Column(db.Text, nullable=False)
    origin_lat = db.Column(db.Numeric(10, 8), nullable=False)
    origin_lng = db.Column(db.Numeric(11, 8), nullable=False)
    destination_address = db.Column(db.Text, nullable=False)
    destination_lat = db.Column(db.Numeric(10, 8), nullable=False)
    destination_lng = db.Column(db.Numeric(11, 8), nullable=False)
    
    # Données de l'itinéraire sélectionné
    selected_route_data = db.Column(JSONColumn, nullable=False)
    alternative_routes = db.Column(JSONColumn, nullable=True)
    
    # Conditions du trafic au moment de la recherche
    traffic_conditions = db.Column(JSONColumn, nullable=True)
    weather_conditions = db.Column(JSONColumn, nullable=True)
    
    # Métriques de performance
    travel_time_seconds = db.Column(db.Integer, nullable=False)
    distance_meters = db.Column(db.Integer, nullable=False)
    optimization_score = db.Column(db.Numeric(5, 2), nullable=False)
    
    # Temps économisé par rapport à l'itinéraire le plus lent
    time_saved_seconds = db.Column(db.Integer, default=0)
    
    # Métadonnées de la recherche
    search_timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    route_started = db.Column(db.Boolean, default=False)
    route_completed = db.Column(db.Boolean, default=False)
    completion_timestamp = db.Column(db.DateTime, nullable=True)
    
    def __init__(self, session_id, origin_address, origin_lat, origin_lng,
                 destination_address, destination_lat, destination_lng,
                 selected_route_data, travel_time_seconds, distance_meters,
                 optimization_score, user_id=None):
        self.session_id = session_id
        self.origin_address = origin_address
        self.origin_lat = float(origin_lat)
        self.origin_lng = float(origin_lng)
        self.destination_address = destination_address
        self.destination_lat = float(destination_lat)
        self.destination_lng = float(destination_lng)
        self.selected_route_data = selected_route_data
        self.travel_time_seconds = travel_time_seconds
        self.distance_meters = distance_meters
        self.optimization_score = float(optimization_score)
        self.user_id = user_id
    
    def __repr__(self):
        return f'<RouteHistory {self.id} - {self.optimization_score}>'
    
    @classmethod
    def get_user_history(cls, user_id, limit=50):
        """Récupérer l'historique d'un utilisateur"""
        return (cls.query.filter_by(user_id=user_id)
                .order_by(cls.created_at.desc())
                .limit(limit)
                .all())
    
    @classmethod
    def get_session_history(cls, session_id, limit=20):
        """Récupérer l'historique d'une session"""
        return (cls.query.filter_by(session_id=session_id)
                .order_by(cls.created_at.desc())
                .limit(limit)
                .all())
    
    @classmethod
    def get_popular_routes(cls, days=30, limit=10):
        """Récupérer les itinéraires les plus populaires"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        return (db.session.query(
                    cls.origin_address,
                    cls.destination_address,
                    func.count(cls.id).label('count'),
                    func.avg(cls.optimization_score).label('avg_score')
                )
                .filter(cls.created_at >= cutoff_date)
                .group_by(cls.origin_address, cls.destination_address)
                .order_by(func.count(cls.id).desc())
                .limit(limit)
                .all())
    
    @classmethod
    def get_analytics_data(cls, user_id=None, days=30):
        """Récupérer les données d'analytics"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = cls.query.filter(cls.created_at >= cutoff_date)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        routes = query.all()
        
        if not routes:
            return {
                'total_routes': 0,
                'total_time_saved': 0,
                'total_distance': 0,
                'average_score': 0,
                'most_common_origin': None,
                'most_common_destination': None
            }
        
        # Calculs d'analytics
        total_time_saved = sum(r.time_saved_seconds for r in routes)
        total_distance = sum(r.distance_meters for r in routes)
        avg_score = sum(r.optimization_score for r in routes) / len(routes)
        
        # Origines et destinations les plus fréquentes
        origins = [r.origin_address for r in routes]
        destinations = [r.destination_address for r in routes]
        
        most_common_origin = max(set(origins), key=origins.count) if origins else None
        most_common_destination = max(set(destinations), key=destinations.count) if destinations else None
        
        return {
            'total_routes': len(routes),
            'total_time_saved': total_time_saved,
            'total_distance': total_distance,
            'average_score': float(avg_score),
            'most_common_origin': most_common_origin,
            'most_common_destination': most_common_destination
        }
    
    def mark_as_started(self):
        """Marquer l'itinéraire comme commencé"""
        self.route_started = True
        self.save()
    
    def mark_as_completed(self):
        """Marquer l'itinéraire comme terminé"""
        self.route_completed = True
        self.completion_timestamp = datetime.utcnow()
        self.save()
    
    def calculate_time_saved(self, alternative_routes):
        """Calculer le temps économisé par rapport aux alternatives"""
        if not alternative_routes:
            self.time_saved_seconds = 0
            return
        
        try:
            # S'assurer que alternative_routes est une liste de dictionnaires
            if not all(isinstance(r, dict) for r in alternative_routes):
                raise ValueError("alternative_routes doit contenir des dictionnaires")
                
            # Trouver le temps de trajet le plus long parmi les alternatives
            max_time = max(int(route.get('duration', 0)) for route in alternative_routes)
            current_time = int(self.travel_time_seconds)
            self.time_saved_seconds = max(0, max_time - current_time)
            self.save()
        except Exception as e:
            self.time_saved_seconds = 0
            current_app.logger.error(f'Erreur calcul temps économisé: {str(e)}')
    
    def get_route_summary(self):
        """Récupérer un résumé de l'itinéraire"""
        return {
            'id': self.id,
            'origin': self.origin_address,
            'destination': self.destination_address,
            'travel_time': {
                'seconds': self.travel_time_seconds,
                'formatted': self.format_duration(self.travel_time_seconds)
            },
            'distance': {
                'meters': self.distance_meters,
                'formatted': self.format_distance(self.distance_meters)
            },
            'optimization_score': float(self.optimization_score),
            'time_saved': {
                'seconds': self.time_saved_seconds,
                'formatted': self.format_duration(self.time_saved_seconds)
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'route_started': self.route_started,
            'route_completed': self.route_completed
        }
    
    @staticmethod
    def format_duration(seconds):
        """Formater une durée en secondes"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}min"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}min"
    
    @staticmethod
    def format_distance(meters):
        """Formater une distance en mètres"""
        if meters < 1000:
            return f"{meters}m"
        else:
            km = meters / 1000
            return f"{km:.1f}km"
    
    def to_dict(self, include_detailed_route=False):
        """Convertir en dictionnaire"""
        data = self.get_route_summary()
        
        if include_detailed_route:
            data.update({
                'selected_route_data': self.selected_route_data,
                'alternative_routes': self.alternative_routes,
                'traffic_conditions': self.traffic_conditions,
                'weather_conditions': self.weather_conditions
            })
        
        return data