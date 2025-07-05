from flask import Blueprint, request, jsonify, session, current_app
from backend.services.here_api import HereApiService
from backend.services.traffic_analyzer import TrafficAnalyzer
from backend.utils.decorators import rate_limit
import json

maps_bp = Blueprint('maps', __name__)

@maps_bp.route('/traffic-layer', methods=['GET'])
@rate_limit('120 per minute')
def get_traffic_layer():
    """API pour récupérer la couche de trafic pour la carte"""
    
    try:
        # Paramètres de la zone visible
        bbox = request.args.get('bbox')  # "lat1,lng1,lat2,lng2"
        zoom = request.args.get('zoom', 10, type=int)
        
        if not bbox:
            return jsonify({'error': 'Bounding box requise'}), 400
        
        try:
            lat1, lng1, lat2, lng2 = map(float, bbox.split(','))
        except ValueError:
            return jsonify({'error': 'Format de bounding box invalide'}), 400
        
        here_api = HereApiService()
        traffic_data = here_api.get_traffic_layer(lat1, lng1, lat2, lng2, zoom)
        
        return jsonify({
            'success': True,
            'traffic_layer': traffic_data,
            'bbox': bbox,
            'zoom': zoom
        })
        
    except Exception as e:
        current_app.logger.error(f'Erreur couche trafic: {str(e)}')
        return jsonify({'error': 'Erreur lors du chargement du trafic'}), 500

@maps_bp.route('/incidents', methods=['GET'])
@rate_limit('60 per minute')
def get_traffic_incidents():
    """API pour récupérer les incidents de circulation"""
    
    try:
        # Paramètres de localisation
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        radius = request.args.get('radius', 10000, type=int)  # Rayon en mètres
        
        if not lat or not lng:
            return jsonify({'error': 'Coordonnées lat/lng requises'}), 400
        
        here_api = HereApiService()
        incidents = here_api.get_traffic_incidents(lat, lng, radius)
        
        return jsonify({
            'success': True,
            'incidents': incidents,
            'center': {'lat': lat, 'lng': lng},
            'radius': radius
        })
        
    except Exception as e:
        current_app.logger.error(f'Erreur incidents trafic: {str(e)}')
        return jsonify({'error': 'Erreur lors du chargement des incidents'}), 500

@maps_bp.route('/reverse-geocode', methods=['POST'])
@rate_limit('100 per minute')
def reverse_geocode():
    """API pour le géocodage inverse (coordonnées -> adresse)"""
    
    try:
        data = request.get_json()
        lat = data.get('lat') if data else None
        lng = data.get('lng') if data else None
        
        if not lat or not lng:
            return jsonify({'error': 'Coordonnées lat/lng requises'}), 400
        
        here_api = HereApiService()
        address_data = here_api.reverse_geocode(lat, lng)
        
        return jsonify({
            'success': True,
            'address': address_data,
            'coordinates': {'lat': lat, 'lng': lng}
        })
        
    except Exception as e:
        current_app.logger.error(f'Erreur géocodage inverse: {str(e)}')
        return jsonify({'error': 'Erreur lors du géocodage inverse'}), 500

@maps_bp.route('/isoline', methods=['POST'])
@rate_limit('30 per minute')
def calculate_isoline():
    """API pour calculer les isolignes (zones accessibles en X temps)"""
    
    try:
        data = request.get_json()
        
        required_fields = ['lat', 'lng', 'range_type', 'range_value']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Champ {field} requis'}), 400
        
        lat = data['lat']
        lng = data['lng']
        range_type = data['range_type']  # 'time' ou 'distance'
        range_value = data['range_value']  # en secondes ou mètres
        transport_mode = data.get('transport_mode', 'car')
        
        here_api = HereApiService()
        isoline_data = here_api.calculate_isoline(
            lat, lng, range_type, range_value, transport_mode
        )
        
        return jsonify({
            'success': True,
            'isoline': isoline_data,
            'parameters': {
                'center': {'lat': lat, 'lng': lng},
                'range_type': range_type,
                'range_value': range_value,
                'transport_mode': transport_mode
            }
        })
        
    except Exception as e:
        current_app.logger.error(f'Erreur calcul isoline: {str(e)}')
        return jsonify({'error': 'Erreur lors du calcul des isolignes'}), 500

@maps_bp.route('/places-nearby', methods=['GET'])
@rate_limit('100 per minute')
def get_places_nearby():
    """API pour récupérer les lieux d'intérêt à proximité"""
    
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        category = request.args.get('category', 'gas-station')  # station-service par défaut
        radius = request.args.get('radius', 2000, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        if not lat or not lng:
            return jsonify({'error': 'Coordonnées lat/lng requises'}), 400
        
        here_api = HereApiService()
        places = here_api.get_places_nearby(lat, lng, category, radius, limit)
        
        return jsonify({
            'success': True,
            'places': places,
            'search_params': {
                'center': {'lat': lat, 'lng': lng},
                'category': category,
                'radius': radius,
                'limit': limit
            }
        })
        
    except Exception as e:
        current_app.logger.error(f'Erreur lieux proximité: {str(e)}')
        return jsonify({'error': 'Erreur lors de la recherche de lieux'}), 500

@maps_bp.route('/route-matrix', methods=['POST'])
@rate_limit('20 per minute')
def calculate_route_matrix():
    """API pour calculer une matrice de distances/temps entre plusieurs points"""
    
    try:
        data = request.get_json()
        
        if not data or 'origins' not in data or 'destinations' not in data:
            return jsonify({'error': 'Origins et destinations requises'}), 400
        
        origins = data['origins']
        destinations = data['destinations']
        
        # Limiter le nombre de points pour éviter la surcharge
        if len(origins) > 10 or len(destinations) > 10:
            return jsonify({'error': 'Maximum 10 origines et 10 destinations'}), 400
        
        transport_mode = data.get('transport_mode', 'car')
        traffic = data.get('traffic', True)
        
        here_api = HereApiService()
        matrix_data = here_api.calculate_matrix(
            origins, destinations, transport_mode, traffic
        )
        
        return jsonify({
            'success': True,
            'matrix': matrix_data,
            'origins': origins,
            'destinations': destinations
        })
        
    except Exception as e:
        current_app.logger.error(f'Erreur matrice routes: {str(e)}')
        return jsonify({'error': 'Erreur lors du calcul de la matrice'}), 500

@maps_bp.route('/weather', methods=['GET'])
@rate_limit('120 per minute')
def get_weather_info():
    """API pour récupérer les informations météo (affect le trafic)"""
    
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        
        if not lat or not lng:
            return jsonify({'error': 'Coordonnées lat/lng requises'}), 400
        
        # Note: Implémenter avec une API météo comme OpenWeatherMap
        # Pour l'instant, retourner des données simulées
        weather_data = {
            'current': {
                'temperature': 22,
                'condition': 'Ensoleillé',
                'humidity': 65,
                'visibility': 10000,  # en mètres
                'precipitation': 0,
                'traffic_impact': 'low'  # low, medium, high
            },
            'forecast': [
                {
                    'time': '2024-01-01T12:00:00Z',
                    'condition': 'Nuageux',
                    'precipitation_probability': 20,
                    'traffic_impact': 'low'
                }
            ]
        }
        
        return jsonify({
            'success': True,
            'weather': weather_data,
            'coordinates': {'lat': lat, 'lng': lng}
        })
        
    except Exception as e:
        current_app.logger.error(f'Erreur info météo: {str(e)}')
        return jsonify({'error': 'Erreur lors de la récupération météo'}), 500

# Routes de configuration et état

@maps_bp.route('/config', methods=['GET'])
def get_maps_config():
    """API pour récupérer la configuration des cartes"""
    
    config = {
        'here_api_key': current_app.config.get('HERE_API_KEY', ''),
        'default_center': {
            'lat': 48.8566,  # Paris par défaut
            'lng': 2.3522
        },
        'default_zoom': 12,
        'traffic_enabled': True,
        'incidents_enabled': True,
        'places_categories': [
            'gas-station',
            'restaurant',
            'hospital',
            'atm',
            'parking',
            'hotel'
        ],
        'supported_transport_modes': [
            'car',
            'truck',
            'pedestrian',
            'bicycle'
        ]
    }
    
    return jsonify({
        'success': True,
        'config': config
    })

@maps_bp.route('/status', methods=['GET'])
def get_maps_status():
    """API pour vérifier le statut des services de cartographie"""
    
    try:
        here_api = HereApiService()
        status = here_api.check_service_status()
        
        return jsonify({
            'success': True,
            'status': status,
            'timestamp': here_api.get_current_time()
        })
        
    except Exception as e:
        current_app.logger.error(f'Erreur statut cartes: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Erreur lors de la vérification du statut'
        }), 503