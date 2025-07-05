# test_models.py - Tests unitaires des modèles

import pytest
from datetime import datetime, timedelta
from backend.models import User, SavedRoute, RouteHistory, RouteAnalytics

@pytest.mark.unit
class TestUser:
    """Tests du modèle User."""
    
    def test_user_creation(self, db_session):
        """Test de création d'un utilisateur."""
        user = User(
            email='test@example.com',
            name='Test User',
            google_id='google123'
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.email == 'test@example.com'
        assert user.name == 'Test User'
        assert user.google_id == 'google123'
        assert user.created_at is not None
        assert user.last_activity is not None
        assert user.is_active is True
    
    def test_user_repr(self, sample_user):
        """Test de la représentation string de l'utilisateur."""
        assert repr(sample_user) == f'<User {sample_user.email}>'
    
    def test_update_last_activity(self, sample_user, db_session):
        """Test de mise à jour de la dernière activité."""
        original_time = sample_user.last_activity
        sample_user.update_last_activity()
        db_session.commit()
        
        assert sample_user.last_activity > original_time
    
    def test_get_by_email(self, sample_user, db_session):
        """Test de récupération par email."""
        user = User.get_by_email(sample_user.email)
        assert user is not None
        assert user.id == sample_user.id
        
        # Test avec email inexistant
        user = User.get_by_email('nonexistent@example.com')
        assert user is None
    
    def test_get_by_google_id(self, sample_user, db_session):
        """Test de récupération par Google ID."""
        user = User.get_by_google_id(sample_user.google_id)
        assert user is not None
        assert user.id == sample_user.id
        
        # Test avec Google ID inexistant
        user = User.get_by_google_id('nonexistent_id')
        assert user is None
    
    def test_user_preferences_default(self, sample_user):
        """Test des préférences par défaut."""
        prefs = sample_user.get_preferences()
        
        assert 'route_preferences' in prefs
        assert 'notifications' in prefs
        assert 'display' in prefs
        
        # Vérifier les valeurs par défaut
        assert prefs['display']['units'] == 'metric'
        assert prefs['display']['language'] == 'fr'
        assert prefs['notifications']['traffic_alerts'] is True

@pytest.mark.unit
class TestSavedRoute:
    """Tests du modèle SavedRoute."""
    
    def test_saved_route_creation(self, db_session, sample_user):
        """Test de création d'une route sauvegardée."""
        route = SavedRoute(
            user_id=sample_user.id,
            name='Test Route',
            origin_address='Origin Address',
            origin_lat=48.8566,
            origin_lng=2.3522,
            destination_address='Destination Address',
            destination_lat=48.8738,
            destination_lng=2.2950
        )
        db_session.add(route)
        db_session.commit()
        
        assert route.id is not None
        assert route.user_id == sample_user.id
        assert route.name == 'Test Route'
        assert route.usage_count == 0
        assert route.is_favorite is False
        assert route.created_at is not None
    
    def test_increment_usage(self, sample_route, db_session):
        """Test d'incrémentation du compteur d'usage."""
        original_count = sample_route.usage_count
        sample_route.increment_usage()
        db_session.commit()
        
        assert sample_route.usage_count == original_count + 1
        assert sample_route.last_used is not None
    
    def test_toggle_favorite(self, sample_route, db_session):
        """Test du toggle favori."""
        assert sample_route.is_favorite is False
        
        sample_route.toggle_favorite()
        db_session.commit()
        assert sample_route.is_favorite is True
        
        sample_route.toggle_favorite()
        db_session.commit()
        assert sample_route.is_favorite is False
    
    def test_coordinates_property(self, sample_route):
        """Test de la propriété coordinates."""
        coords = sample_route.coordinates
        
        assert 'origin' in coords
        assert 'destination' in coords
        assert coords['origin']['lat'] == sample_route.origin_lat
        assert coords['origin']['lng'] == sample_route.origin_lng
        assert coords['destination']['lat'] == sample_route.destination_lat
        assert coords['destination']['lng'] == sample_route.destination_lng

@pytest.mark.unit
class TestRouteHistory:
    """Tests du modèle RouteHistory."""
    
    def test_route_history_creation(self, db_session, sample_user):
        """Test de création d'un historique de route."""
        history = RouteHistory(
            user_id=sample_user.id,
            origin_address='Paris',
            origin_lat=48.8566,
            origin_lng=2.3522,
            destination_address='Lyon',
            destination_lat=45.7640,
            destination_lng=4.8357,
            travel_time_seconds=14400,
            distance_meters=463000,
            optimization_score=8.5
        )
        db_session.add(history)
        db_session.commit()
        
        assert history.id is not None
        assert history.user_id == sample_user.id
        assert history.optimization_score == 8.5
        assert history.route_started is False
        assert history.route_completed is False
    
    def test_mark_as_started(self, sample_history, db_session):
        """Test de marquage comme démarré."""
        sample_history.mark_as_started()
        db_session.commit()
        
        assert sample_history.route_started is True
        assert sample_history.started_at is not None
    
    def test_mark_as_completed(self, sample_history, db_session):
        """Test de marquage comme terminé."""
        sample_history.mark_as_completed()
        db_session.commit()
        
        assert sample_history.route_completed is True
        assert sample_history.completed_at is not None
    
    def test_travel_time_display(self, sample_history):
        """Test de l'affichage du temps de trajet."""
        display = sample_history.travel_time_display
        assert 'h' in display or 'min' in display
    
    def test_distance_display(self, sample_history):
        """Test de l'affichage de la distance."""
        display = sample_history.distance_display
        assert 'km' in display or 'm' in display

@pytest.mark.unit 
class TestRouteAnalytics:
    """Tests du modèle RouteAnalytics."""
    
    def test_get_user_analytics(self, db_session, sample_user, sample_history):
        """Test de récupération des analytics utilisateur."""
        analytics = RouteAnalytics.get_user_analytics(sample_user.id)
        
        assert 'total_routes_searched' in analytics
        assert 'total_time_saved_minutes' in analytics
        assert 'total_distance_km' in analytics
        assert 'average_optimization_score' in analytics
        assert analytics['total_routes_searched'] >= 1
    
    def test_get_weekly_stats(self, db_session, sample_user, sample_history):
        """Test des statistiques hebdomadaires."""
        stats = RouteAnalytics.get_weekly_stats(sample_user.id)
        
        assert 'routes_count' in stats
        assert 'time_saved_minutes' in stats
        assert 'distance_km' in stats
        assert 'average_score' in stats
    
    def test_get_monthly_trends(self, db_session, sample_user):
        """Test des tendances mensuelles."""
        # Créer plusieurs historiques avec dates différentes
        for i in range(3):
            history = RouteHistory(
                user_id=sample_user.id,
                origin_address=f'Origin {i}',
                origin_lat=48.8566,
                origin_lng=2.3522,
                destination_address=f'Destination {i}',
                destination_lat=45.7640,
                destination_lng=4.8357,
                travel_time_seconds=3600,
                distance_meters=50000,
                optimization_score=8.0,
                created_at=datetime.utcnow() - timedelta(days=i*30)
            )
            db_session.add(history)
        db_session.commit()
        
        trends = RouteAnalytics.get_monthly_trends(sample_user.id)
        assert isinstance(trends, list)
        assert len(trends) > 0
        
        if trends:
            assert 'month' in trends[0]
            assert 'routes_count' in trends[0]
            assert 'time_saved_minutes' in trends[0]
    
    def test_get_efficiency_score(self, db_session, sample_user, sample_history):
        """Test du calcul du score d'efficacité."""
        score = RouteAnalytics.get_efficiency_score(sample_user.id)
        
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100