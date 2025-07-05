# test_api_routes.py - Tests d'intégration des API

import pytest
import json
from unittest.mock import patch, Mock
from datetime import datetime

@pytest.mark.integration
@pytest.mark.api
class TestRouteSearchAPI:
    """Tests de l'API de recherche d'itinéraires."""
    
    def test_search_routes_success(self, authenticated_client, mock_here_api, helpers):
        """Test de recherche d'itinéraire réussie."""
        route_data = helpers.create_route_data()
        
        response = authenticated_client.post(
            '/api/search-routes',
            data=json.dumps(route_data),
            content_type='application/json'
        )
        
        helpers.assert_route_response(response, 200)
        
        data = response.get_json()
        assert len(data['routes']) > 0
        assert 'summary' in data['routes'][0]
        assert 'optimization_score' in data['routes'][0]
    
    def test_search_routes_validation_error(self, authenticated_client):
        """Test de validation des données de recherche."""
        # Données manquantes
        response = authenticated_client.post(
            '/api/search-routes',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data
    
    def test_search_routes_unauthenticated(self, client, helpers):
        """Test de recherche sans authentification."""
        route_data = helpers.create_route_data()
        
        response = client.post(
            '/api/search-routes',
            data=json.dumps(route_data),
            content_type='application/json'
        )
        
        assert response.status_code == 401
    
    def test_search_routes_with_options(self, authenticated_client, mock_here_api, helpers):
        """Test de recherche avec options spécifiques."""
        route_data = helpers.create_route_data(
            avoid_tolls=True,
            avoid_highways=True,
            route_type='shortest'
        )
        
        response = authenticated_client.post(
            '/api/search-routes',
            data=json.dumps(route_data),
            content_type='application/json'
        )
        
        helpers.assert_route_response(response, 200)
        
        # Vérifier que les options ont été passées au service
        mock_here_api.calculate_route.assert_called_once()
        call_args = mock_here_api.calculate_route.call_args[1]
        assert call_args['avoid_tolls'] is True
        assert call_args['avoid_highways'] is True

@pytest.mark.integration
@pytest.mark.api
class TestSavedRoutesAPI:
    """Tests de l'API des routes sauvegardées."""
    
    def test_get_saved_routes(self, authenticated_client, sample_route):
        """Test de récupération des routes sauvegardées."""
        response = authenticated_client.get('/api/saved-routes')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['routes']) >= 1
        assert data['routes'][0]['name'] == sample_route.name
    
    def test_create_saved_route(self, authenticated_client, db_session):
        """Test de création d'une route sauvegardée."""
        route_data = {
            'name': 'Nouvelle Route',
            'origin_address': 'Paris, France',
            'origin_lat': 48.8566,
            'origin_lng': 2.3522,
            'destination_address': 'Lyon, France',
            'destination_lat': 45.7640,
            'destination_lng': 4.8357,
            'tags': ['travail', 'quotidien']
        }
        
        response = authenticated_client.post(
            '/api/saved-routes',
            data=json.dumps(route_data),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['route']['name'] == 'Nouvelle Route'
        assert 'id' in data['route']
    
    def test_update_saved_route(self, authenticated_client, sample_route):
        """Test de mise à jour d'une route sauvegardée."""
        update_data = {
            'name': 'Nom Modifié',
            'tags': ['nouveau', 'tag']
        }
        
        response = authenticated_client.put(
            f'/api/saved-routes/{sample_route.id}',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['route']['name'] == 'Nom Modifié'
    
    def test_delete_saved_route(self, authenticated_client, sample_route):
        """Test de suppression d'une route sauvegardée."""
        response = authenticated_client.delete(f'/api/saved-routes/{sample_route.id}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        
        # Vérifier que la route a été supprimée
        response = authenticated_client.get(f'/api/saved-routes/{sample_route.id}')
        assert response.status_code == 404
    
    def test_toggle_favorite(self, authenticated_client, sample_route):
        """Test du toggle favori."""
        assert sample_route.is_favorite is False
        
        response = authenticated_client.post(f'/api/saved-routes/{sample_route.id}/favorite')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['is_favorite'] is True

@pytest.mark.integration
@pytest.mark.api
class TestHistoryAPI:
    """Tests de l'API d'historique."""
    
    def test_get_history(self, authenticated_client, sample_history):
        """Test de récupération de l'historique."""
        response = authenticated_client.get('/api/history')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['history']) >= 1
        assert 'pagination' in data
    
    def test_get_history_with_pagination(self, authenticated_client, db_session, sample_user):
        """Test de pagination de l'historique."""
        # Créer plusieurs entrées d'historique
        for i in range(25):
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
                optimization_score=8.0
            )
            db_session.add(history)
        db_session.commit()
        
        # Test première page
        response = authenticated_client.get('/api/history?page=1&per_page=10')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['history']) == 10
        assert data['pagination']['page'] == 1
        assert data['pagination']['total'] >= 25
        
        # Test deuxième page
        response = authenticated_client.get('/api/history?page=2&per_page=10')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['history']) == 10
        assert data['pagination']['page'] == 2
    
    def test_get_single_history_item(self, authenticated_client, sample_history):
        """Test de récupération d'un élément d'historique spécifique."""
        response = authenticated_client.get(f'/api/history/{sample_history.id}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['route']['id'] == sample_history.id
    
    def test_export_history(self, authenticated_client, sample_history):
        """Test d'export de l'historique."""
        response = authenticated_client.post('/api/history/export')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'data' in data
        assert len(data['data']) >= 1
    
    def test_clear_history(self, authenticated_client, sample_history, db_session):
        """Test d'effacement de l'historique."""
        response = authenticated_client.delete('/api/history')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        
        # Vérifier que l'historique a été effacé
        response = authenticated_client.get('/api/history')
        data = response.get_json()
        assert len(data['history']) == 0

@pytest.mark.integration
@pytest.mark.api
class TestAnalyticsAPI:
    """Tests de l'API d'analytics."""
    
    def test_get_user_analytics(self, authenticated_client, sample_history):
        """Test de récupération des analytics utilisateur."""
        response = authenticated_client.get('/api/analytics')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'summary' in data
        assert 'weekly_stats' in data
        assert 'monthly_trends' in data
        
        # Vérifier la structure des données
        summary = data['summary']
        assert 'total_routes_searched' in summary
        assert 'total_time_saved_minutes' in summary
        assert 'average_optimization_score' in summary
        assert 'efficiency_score' in summary
    
    def test_get_monthly_trends(self, authenticated_client, sample_history):
        """Test de récupération des tendances mensuelles."""
        response = authenticated_client.get('/api/analytics/trends')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert isinstance(data['trends'], list)

@pytest.mark.integration
@pytest.mark.api
class TestAutocompleteAPI:
    """Tests de l'API d'autocomplétion."""
    
    @patch('backend.services.here_service.HereService.geocode')
    def test_autocomplete_success(self, mock_geocode, authenticated_client):
        """Test d'autocomplétion réussie."""
        mock_geocode.return_value = {
            'success': True,
            'results': [
                {
                    'title': 'Paris, France',
                    'label': 'Paris, Île-de-France, France',
                    'position': {'lat': 48.8566, 'lng': 2.3522}
                }
            ]
        }
        
        response = authenticated_client.get('/api/autocomplete?q=Paris')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['suggestions']) > 0
        assert 'title' in data['suggestions'][0]
        assert 'position' in data['suggestions'][0]
    
    def test_autocomplete_short_query(self, authenticated_client):
        """Test d'autocomplétion avec requête trop courte."""
        response = authenticated_client.get('/api/autocomplete?q=P')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
    
    def test_autocomplete_no_query(self, authenticated_client):
        """Test d'autocomplétion sans requête."""
        response = authenticated_client.get('/api/autocomplete')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False