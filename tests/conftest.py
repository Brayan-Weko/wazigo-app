# conftest.py - Configuration globale des tests pytest

import pytest
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Import de l'application
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app import create_app
from backend.models import db, User, SavedRoute, RouteHistory
from backend.config import TestConfig

@pytest.fixture(scope='session')
def app():
    """Créer une instance de l'application pour les tests."""
    app = create_app(TestConfig)
    
    with app.app_context():
        yield app

@pytest.fixture(scope='function')
def client(app):
    """Client de test Flask."""
    return app.test_client()

@pytest.fixture(scope='function')
def db_session(app):
    """Session de base de données pour les tests."""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.rollback()
        db.drop_all()

@pytest.fixture
def sample_user(db_session):
    """Utilisateur de test."""
    user = User(
        email='test@example.com',
        name='Test User',
        google_id='test_google_id',
        avatar_url='https://example.com/avatar.jpg'
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def authenticated_client(client, sample_user):
    """Client authentifié."""
    with client.session_transaction() as sess:
        sess['user'] = {
            'id': sample_user.id,
            'email': sample_user.email,
            'name': sample_user.name
        }
    return client

@pytest.fixture
def sample_route(db_session, sample_user):
    """Route sauvegardée de test."""
    route = SavedRoute(
        user_id=sample_user.id,
        name='Maison → Bureau',
        origin_address='123 Rue de la Paix, Paris',
        origin_lat=48.8566,
        origin_lng=2.3522,
        destination_address='456 Avenue des Champs, Paris',
        destination_lat=48.8738,
        destination_lng=2.2950,
        tags=['travail', 'quotidien']
    )
    db_session.add(route)
    db_session.commit()
    return route

@pytest.fixture
def sample_history(db_session, sample_user):
    """Historique de route de test."""
    history = RouteHistory(
        user_id=sample_user.id,
        origin_address='Paris, France',
        origin_lat=48.8566,
        origin_lng=2.3522,
        destination_address='Lyon, France',
        destination_lat=45.7640,
        destination_lng=4.8357,
        travel_time_seconds=14400,  # 4 heures
        distance_meters=463000,     # 463 km
        optimization_score=8.5,
        time_saved_seconds=1800,    # 30 minutes
        route_data={'test': 'data'}
    )
    db_session.add(history)
    db_session.commit()
    return history

@pytest.fixture
def mock_here_api():
    """Mock de l'API HERE Maps."""
    with patch('backend.services.here_service.HereService') as mock:
        mock_instance = Mock()
        
        # Mock route calculation
        mock_instance.calculate_route.return_value = {
            'success': True,
            'routes': [{
                'summary': {
                    'duration': 3600,
                    'length': 50000,
                    'origin': {'lat': 48.8566, 'lng': 2.3522, 'address': 'Paris'},
                    'destination': {'lat': 48.8738, 'lng': 2.2950, 'address': 'La Défense'}
                },
                'coordinates': [
                    {'lat': 48.8566, 'lng': 2.3522},
                    {'lat': 48.8738, 'lng': 2.2950}
                ],
                'optimization_score': 8.0,
                'traffic_analysis': {
                    'level': 'moderate',
                    'description': 'Trafic modéré',
                    'ratio': 1.2
                }
            }]
        }
        
        # Mock geocoding
        mock_instance.geocode.return_value = {
            'success': True,
            'results': [{
                'title': 'Paris, France',
                'label': 'Paris, Île-de-France, France',
                'position': {'lat': 48.8566, 'lng': 2.3522}
            }]
        }
        
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_redis():
    """Mock de Redis."""
    with patch('redis.Redis') as mock:
        mock_instance = Mock()
        mock_instance.get.return_value = None
        mock_instance.set.return_value = True
        mock_instance.delete.return_value = True
        mock.return_value = mock_instance
        yield mock_instance

# Helpers pour les tests
class TestHelpers:
    @staticmethod
    def create_route_data(**kwargs):
        """Créer des données de route pour les tests."""
        default_data = {
            'origin': 'Paris, France',
            'destination': 'Lyon, France',
            'departure_time': None,
            'route_type': 'fastest',
            'avoid_tolls': False,
            'avoid_highways': False,
            'avoid_ferries': False
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def assert_route_response(response, expected_status=200):
        """Vérifier une réponse de route."""
        assert response.status_code == expected_status
        if expected_status == 200:
            data = response.get_json()
            assert data['success'] is True
            assert 'routes' in data
            assert len(data['routes']) > 0

@pytest.fixture
def helpers():
    """Helpers pour les tests."""
    return TestHelpers()

# Configuration des marqueurs pytest
def pytest_configure(config):
    """Configuration des marqueurs personnalisés."""
    config.addinivalue_line(
        "markers", "unit: marque les tests unitaires"
    )
    config.addinivalue_line(
        "markers", "integration: marque les tests d'intégration"
    )
    config.addinivalue_line(
        "markers", "e2e: marque les tests end-to-end"
    )
    config.addinivalue_line(
        "markers", "slow: marque les tests lents"
    )
    config.addinivalue_line(
        "markers", "api: marque les tests d'API"
    )

# Configuration du logging pour les tests
import logging
logging.getLogger().setLevel(logging.WARNING)