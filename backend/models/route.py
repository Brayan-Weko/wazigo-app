from .database import db, DatabaseMixin, JSONColumn
from datetime import datetime

class SavedRoute(DatabaseMixin, db.Model):
    """Modèle pour les itinéraires sauvegardés par les utilisateurs"""
    
    __tablename__ = 'saved_routes'
    
    # Relation avec l'utilisateur
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Informations de base
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_favorite = db.Column(db.Boolean, default=False, nullable=False)
    
    # Point de départ
    origin_address = db.Column(db.Text, nullable=False)
    origin_lat = db.Column(db.Numeric(10, 8), nullable=False)
    origin_lng = db.Column(db.Numeric(11, 8), nullable=False)
    
    # Point d'arrivée
    destination_address = db.Column(db.Text, nullable=False)
    destination_lat = db.Column(db.Numeric(10, 8), nullable=False)
    destination_lng = db.Column(db.Numeric(11, 8), nullable=False)
    
    # Métadonnées supplémentaires
    tags = db.Column(JSONColumn, nullable=True)  # ['travail', 'maison', 'loisir']
    schedule = db.Column(JSONColumn, nullable=True)  # Horaires récurrents
    
    # Statistiques d'utilisation
    usage_count = db.Column(db.Integer, default=0, nullable=False)
    last_used = db.Column(db.DateTime, nullable=True)
    
    def __init__(self, name, origin_address, origin_lat, origin_lng, 
                 destination_address, destination_lat, destination_lng, 
                 user_id=None, description=None):
        self.name = name
        self.origin_address = origin_address
        self.origin_lat = float(origin_lat)
        self.origin_lng = float(origin_lng)
        self.destination_address = destination_address
        self.destination_lat = float(destination_lat)
        self.destination_lng = float(destination_lng)
        self.user_id = user_id
        self.description = description
        self.tags = []
    
    def __repr__(self):
        return f'<SavedRoute {self.name}>'
    
    @classmethod
    def get_user_routes(cls, user_id, include_favorites_only=False):
        """Récupérer les itinéraires d'un utilisateur"""
        query = cls.query.filter_by(user_id=user_id)
        if include_favorites_only:
            query = query.filter_by(is_favorite=True)
        return query.order_by(cls.usage_count.desc(), cls.created_at.desc()).all()
    
    @classmethod
    def find_similar_route(cls, user_id, origin_lat, origin_lng, dest_lat, dest_lng, tolerance=0.001):
        """Trouver un itinéraire similaire (même origine et destination approximatives)"""
        return cls.query.filter(
            cls.user_id == user_id,
            cls.origin_lat.between(float(origin_lat) - tolerance, float(origin_lat) + tolerance),
            cls.origin_lng.between(float(origin_lng) - tolerance, float(origin_lng) + tolerance),
            cls.destination_lat.between(float(dest_lat) - tolerance, float(dest_lat) + tolerance),
            cls.destination_lng.between(float(dest_lng) - tolerance, float(dest_lng) + tolerance)
        ).first()
    
    def increment_usage(self):
        """Incrémenter le compteur d'utilisation"""
        self.usage_count += 1
        self.last_used = datetime.utcnow()
        self.save()
    
    def toggle_favorite(self):
        """Basculer le statut favori"""
        self.is_favorite = not self.is_favorite
        self.save()
        return self.is_favorite
    
    def add_tag(self, tag):
        """Ajouter un tag"""
        if not self.tags:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
            self.save()
    
    def remove_tag(self, tag):
        """Supprimer un tag"""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
            self.save()
    
    def get_coordinates(self):
        """Récupérer les coordonnées sous forme de dictionnaire"""
        return {
            'origin': {
                'lat': float(self.origin_lat),
                'lng': float(self.origin_lng),
                'address': self.origin_address
            },
            'destination': {
                'lat': float(self.destination_lat),
                'lng': float(self.destination_lng),
                'address': self.destination_address
            }
        }
    
    def to_dict(self):
        """Convertir en dictionnaire"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_favorite': self.is_favorite,
            'coordinates': self.get_coordinates(),
            'tags': self.tags or [],
            'usage_count': self.usage_count,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }