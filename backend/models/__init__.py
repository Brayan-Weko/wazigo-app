"""
Modèles de base de données pour l'application Smart Route
"""

from .database import db, DatabaseMixin, JSONColumn
from .user import User
from .route import SavedRoute
from .history import RouteHistory
from .analytics import UserAnalytics
from .additional import GuestSession, Feedback

# Export des modèles
__all__ = [
    'db',
    'DatabaseMixin', 
    'JSONColumn',
    'User',
    'SavedRoute',
    'RouteHistory',
    'UserAnalytics',
    'GuestSession',
    'Feedback'
]

# Fonction utilitaire pour créer toutes les tables
def create_all_tables(app):
    """Créer toutes les tables de la base de données"""
    with app.app_context():
        db.create_all()
        print("✅ Toutes les tables ont été créées avec succès")

# Fonction utilitaire pour supprimer toutes les tables
def drop_all_tables(app):
    """Supprimer toutes les tables de la base de données"""
    with app.app_context():
        db.drop_all()
        print("⚠️ Toutes les tables ont été supprimées")