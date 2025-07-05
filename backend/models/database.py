#from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from backend.extensions import db

#db = SQLAlchemy()

class DatabaseMixin:
    """Mixin pour les fonctionnalités communes des modèles"""
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def save(self):
        """Sauvegarder l'objet en base"""
        try:
            db.session.add(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    def delete(self):
        """Supprimer l'objet de la base"""
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    def to_dict(self):
        """Convertir l'objet en dictionnaire"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
    
    @classmethod
    def get_by_id(cls, id):
        """Récupérer un objet par son ID"""
        return cls.query.get(id)
    
    @classmethod
    def get_all(cls):
        """Récupérer tous les objets"""
        return cls.query.all()

class JSONColumn(db.TypeDecorator):
    """Type de colonne personnalisé pour JSON"""
    
    impl = db.Text
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value, ensure_ascii=False)
        return value
    
    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return json.loads(value)
            except (ValueError, TypeError):
                return value
        return value