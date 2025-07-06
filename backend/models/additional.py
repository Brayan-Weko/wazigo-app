from .database import db, DatabaseMixin, JSONColumn
from datetime import datetime, timedelta

class GuestSession(DatabaseMixin, db.Model):
    """Modèle pour les sessions d'utilisateurs invités"""
    
    __tablename__ = 'guest_sessions'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.String(250), primary_key=True)  # UUID
    ip_address = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.Text, nullable=True)
    preferences = db.Column(JSONColumn, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    def __init__(self, session_id, ip_address, user_agent=None):
        self.id = session_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.expires_at = datetime.utcnow() + timedelta(days=30)  # Expire après 30 jours
        self.preferences = {}
    
    @classmethod
    def cleanup_expired(cls):
        """Supprimer les sessions expirées"""
        expired = cls.query.filter(cls.expires_at < datetime.utcnow()).all()
        for session in expired:
            db.session.delete(session)
        db.session.commit()
        return len(expired)

class Feedback(DatabaseMixin, db.Model):
    """Modèle pour les retours utilisateurs"""
    
    __tablename__ = 'feedback'
    __table_args__ = {'extend_existing': True}
    
    # Relations
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(250), nullable=True)
    route_id = db.Column(db.Integer, db.ForeignKey('route_history.id'), nullable=True)
    
    # Contenu du feedback
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text, nullable=True)
    feedback_type = db.Column(db.Enum('route_quality', 'app_performance', 'feature_request', 'bug_report'), 
                             nullable=False)
    
    # Métadonnées
    is_resolved = db.Column(db.Boolean, default=False)
    admin_response = db.Column(db.Text, nullable=True)
    
    def __init__(self, rating, feedback_type, user_id=None, session_id=None, 
                 route_id=None, comment=None):
        self.rating = rating
        self.feedback_type = feedback_type
        self.user_id = user_id
        self.session_id = session_id
        self.route_id = route_id
        self.comment = comment
    
    @classmethod
    def get_average_rating(cls, days=30):
        """Récupérer la note moyenne des derniers jours"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = (db.session.query(db.func.avg(cls.rating))
                 .filter(cls.created_at >= cutoff)
                 .scalar())
        return round(float(result), 2) if result else 0
    
    def to_dict(self):
        return {
            'id': self.id,
            'rating': self.rating,
            'comment': self.comment,
            'feedback_type': self.feedback_type,
            'is_resolved': self.is_resolved,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }