import requests
import json
from datetime import datetime, timedelta
from flask import current_app
import time
from typing import Dict, List, Optional, Tuple
import logging
from backend.utils.date_helpers import validate_here_datetime, get_here_current_time

class HereApiService:
    """Service pour interagir avec l'API HERE Maps"""
    
    def __init__(self):
        self.api_key = current_app.config['HERE_API_KEY']
        self.base_url = current_app.config['HERE_BASE_URL']
        self.geocoding_url = current_app.config['HERE_GEOCODING_URL']
        self.traffic_url = current_app.config['HERE_TRAFFIC_URL']
        
        # Configuration des sessions pour optimiser les performances
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SmartRoute/1.0',
            'Accept': 'application/json'
        })
        
        # Cache simple en mémoire (en production, utiliser Redis)
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
        
        self.logger = logging.getLogger(__name__)
    
    def _make_request(self, url: str, params: Dict, cache_key: str = None, timeout: int = 30) -> Optional[Dict]:
        """Faire une requête vers l'API HERE avec gestion du cache et des erreurs"""
        
        # Vérifier le cache
        if cache_key and cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                self.logger.info("Using cached data")
                return cached_data
        
        # Ajouter la clé API
        params_with_key = params.copy()
        params_with_key['apikey'] = self.api_key
        
        try:
            self.logger.info(f"Making HTTP request to: {url}")
            
            response = self.session.get(url, params=params_with_key, timeout=timeout)
            
            # Log de la réponse pour débogage
            self.logger.info(f"HERE API Response status: {response.status_code}")
            
            if response.status_code == 400:
                # Erreur 400 - analyser la réponse
                try:
                    error_data = response.json()
                    self.logger.error(f"HERE API 400 Error: {error_data}")
                    
                    # Vérifier les erreurs courantes
                    if 'error' in error_data:
                        error_msg = error_data['error'].get('message', 'Unknown error')
                        self.logger.error(f"HERE API Error Message: {error_msg}")
                    elif 'notices' in error_data:
                        for notice in error_data['notices']:
                            self.logger.error(f"HERE API Notice: {notice}")
                except Exception as e:
                    self.logger.error(f"HERE API 400 Error - Raw response: {response.text[:500]}")
                
                return None
            
            elif response.status_code == 401:
                self.logger.error("HERE API 401 - Invalid API key")
                return None
            
            elif response.status_code == 429:
                self.logger.error("HERE API 429 - Rate limit exceeded")
                return None
            
            # Vérifier le succès
            response.raise_for_status()
            
            try:
                data = response.json()
                self.logger.info("HERE API request successful")
                
                # Mettre en cache seulement si succès
                if cache_key and data:
                    self._cache[cache_key] = (data, time.time())
                
                return data
                
            except json.JSONDecodeError as e:
                self.logger.error(f"HERE API returned invalid JSON: {e}")
                self.logger.error(f"Response content: {response.text[:500]}")
                return None
            
        except requests.exceptions.Timeout as e:
            self.logger.error(f"HERE API timeout: {str(e)}")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"HERE API request error: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in HERE API request: {str(e)}")
            return None
    
    def calculate_routes(self, search_params: Dict) -> Optional[Dict]:
        """Calculer plusieurs itinéraires entre deux points"""
        
        url = f"{self.base_url}/routes"
        
        # Geocoder les adresses si nécessaire
        origin_coords = self._get_coordinates(search_params['origin'])
        destination_coords = self._get_coordinates(search_params['destination'])
        
        if not origin_coords or not destination_coords:
            self.logger.error("Impossible de géocoder les adresses")
            return None
        
        # ✅ CORRECTION: Paramètres conformes à HERE Maps v8
        params = {
            'transportMode': 'car',
            'origin': f"{origin_coords['lat']},{origin_coords['lng']}",
            'destination': f"{destination_coords['lat']},{destination_coords['lng']}",
            'return': 'summary,polyline,actions,instructions',  # ✅ Ajouter 'actions' pour les instructions
            'alternatives': min(search_params.get('alternatives', 3), 7),  # HERE limite à 7
            'units': 'metric'
        }
        
        # Format datetime pour HERE Maps (sans microsecondes)
        params['departureTime'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        
        # Type de route (HERE v8 utilise routingMode)
        route_type = search_params.get('route_type', 'fastest')
        if route_type == 'shortest':
            params['routingMode'] = 'short'
        elif route_type == 'balanced':
            params['routingMode'] = 'balanced'
        else:  # fastest
            params['routingMode'] = 'fast'
        
        # Options d'évitement (HERE v8 format)
        avoid_features = []
        if search_params.get('avoid_tolls'):
            avoid_features.append('tollRoad')
        if search_params.get('avoid_highways'):
            avoid_features.append('controlledAccessHighway')
        if search_params.get('avoid_ferries'):
            avoid_features.append('ferry')
        
        if avoid_features:
            params['avoid[features]'] = ','.join(avoid_features)
        
        # Cache key
        cache_key = f"routes_{hash(str(sorted(params.items())))}"
        
        # Faire la requête
        self.logger.info(f"HERE API Request: {url}")
        self.logger.info(f"HERE API Params: {params}")
        
        data = self._make_request(url, params, cache_key)
        
        if data and 'routes' in data:
            self.logger.info(f"HERE API returned {len(data['routes'])} routes")
            
            # Enrichir les données avec les coordonnées d'origine
            for i, route in enumerate(data['routes']):
                route['origin_coords'] = origin_coords
                route['destination_coords'] = destination_coords
                
                # Ajouter les informations de trafic si disponibles
                if 'summary' in route:
                    summary = route['summary']
                    
                    # Calculer les informations de trafic
                    duration = summary.get('duration', 0)
                    typical_duration = summary.get('typicalDuration', duration)
                    
                    route['traffic_analysis'] = {
                        'ratio': duration / typical_duration if typical_duration > 0 else 1.0,
                        'delay_seconds': max(0, duration - typical_duration),
                        'status': self._get_traffic_status(summary),
                        'level': self._get_traffic_level(duration, typical_duration)
                    }
                    
                    self.logger.info(f"Route {i}: Duration={duration}s, Length={summary.get('length', 0)}m, Traffic={route['traffic_analysis']['status']}")
            
            return data
        
        self.logger.error(f"HERE API failed or returned no routes")
        return None
    
    def _get_traffic_level(self, duration, typical_duration):
        """Calculer le niveau de trafic numérique"""
        if typical_duration == 0:
            return 5
        
        ratio = duration / typical_duration
        
        if ratio <= 1.1:
            return 9  # Excellent
        elif ratio <= 1.3:
            return 7  # Bon
        elif ratio <= 1.6:
            return 5  # Moyen
        elif ratio <= 2.0:
            return 3  # Mauvais
        else:
            return 1  # Très mauvais

    def _get_traffic_status(self, summary: Dict) -> str:
        """Déterminer le statut du trafic basé sur la durée"""
        duration = summary.get('duration', 0)
        typical_duration = summary.get('typicalDuration', duration)
        
        if typical_duration == 0:
            return 'unknown'
        
        ratio = duration / typical_duration
        
        if ratio <= 1.1:
            return 'free'
        elif ratio <= 1.3:
            return 'light'
        elif ratio <= 1.6:
            return 'moderate'
        else:
            return 'heavy'
    
    def _get_coordinates(self, address: str) -> Optional[Dict]:
        """Récupérer les coordonnées d'une adresse"""
        
        # Si c'est déjà des coordonnées (lat,lng)
        if isinstance(address, str) and ',' in address:
            try:
                parts = address.split(',')
                if len(parts) == 2:
                    lat, lng = map(float, parts)
                    # Valider les coordonnées
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        return {'lat': lat, 'lng': lng, 'address': address}
            except ValueError:
                pass
        
        # Si c'est une adresse textuelle, la géocoder
        if isinstance(address, str) and address.strip():
            geocode_result = self.geocode_address(address.strip())
            if geocode_result and len(geocode_result) > 0:
                first_result = geocode_result[0]
                return {
                    'lat': first_result['position']['lat'],
                    'lng': first_result['position']['lng'],
                    'address': first_result['title']
                }
        
        self.logger.error(f"Impossible de récupérer les coordonnées pour: {address}")
        return None
    
    def geocode_address(self, address: str, limit: int = 5) -> Optional[List[Dict]]:
        """Géocoder une adresse en coordonnées"""
        
        url = f"{self.geocoding_url}/geocode"
        
        params = {
            'q': address,
            'limit': limit,
            'lang': 'fr'
        }
        
        cache_key = f"geocode_{hash(address)}"
        data = self._make_request(url, params, cache_key)
        
        if data and 'items' in data:
            return data['items']
        
        return None
    
    def reverse_geocode(self, lat: float, lng: float) -> Optional[Dict]:
        """Géocodage inverse: coordonnées vers adresse"""
        
        url = f"{self.geocoding_url}/revgeocode"
        
        params = {
            'at': f"{lat},{lng}",
            'lang': 'fr'
        }
        
        cache_key = f"reverse_{lat}_{lng}"
        data = self._make_request(url, params, cache_key)
        
        if data and 'items' in data and len(data['items']) > 0:
            return data['items'][0]
        
        return None
    
    def autocomplete_address(self, query: str, limit: int = 10) -> List[Dict]:
        """Autocomplétion d'adresses"""
        
        if len(query) < 3:
            return []
        
        url = f"{self.geocoding_url}/autosuggest"
        
        params = {
            'q': query,
            'limit': limit,
            'lang': 'fr',
            'resultTypes': 'place,street,houseNumber'
        }
        
        # Cache court pour autocomplétion
        cache_key = f"autocomplete_{hash(query)}"
        data = self._make_request(url, params, cache_key)
        
        suggestions = []
        if data and 'items' in data:
            for item in data['items']:
                suggestion = {
                    'title': item.get('title', ''),
                    'label': item.get('address', {}).get('label', ''),
                    'position': item.get('position', {}),
                    'result_type': item.get('resultType', ''),
                    'highlight': item.get('highlights', {})
                }
                suggestions.append(suggestion)
        
        return suggestions
    
    def get_traffic_layer(self, lat1: float, lng1: float, lat2: float, lng2: float, zoom: int = 10) -> Optional[Dict]:
        """Récupérer la couche de trafic pour une zone"""
        
        url = f"{self.traffic_url}/flow"
        
        params = {
            'bbox': f"{lat1},{lng1},{lat2},{lng2}",
            'locationReferencing': 'shape'
        }
        
        cache_key = f"traffic_layer_{lat1}_{lng1}_{lat2}_{lng2}_{zoom}"
        data = self._make_request(url, params, cache_key)
        
        if data:
            # Traiter les données de trafic pour les rendre plus utilisables
            traffic_segments = []
            
            if 'results' in data:
                for result in data['results']:
                    location = result.get('location', {})
                    current_flow = result.get('currentFlow', {})
                    
                    segment = {
                        'geometry': location.get('shape', {}),
                        'speed': current_flow.get('speed', 0),
                        'free_flow_speed': current_flow.get('freeFlowSpeed', 0),
                        'jam_factor': current_flow.get('jamFactor', 0),
                        'confidence': current_flow.get('confidence', 0),
                        'traversability': current_flow.get('traversability', 'open'),
                        'traffic_level': self._calculate_traffic_level(current_flow)
                    }
                    traffic_segments.append(segment)
            
            return {
                'segments': traffic_segments,
                'bbox': f"{lat1},{lng1},{lat2},{lng2}",
                'timestamp': datetime.utcnow().isoformat()
            }
        
        return None
    
    def get_traffic_incidents(self, lat: float, lng: float, radius: int = 10000) -> List[Dict]:
        """Récupérer les incidents de circulation dans une zone"""
        
        url = f"{self.traffic_url}/incidents"
        
        params = {
            'at': f"{lat},{lng}",
            'radius': radius,
            'units': 'metric'
        }
        
        cache_key = f"incidents_{lat}_{lng}_{radius}"
        data = self._make_request(url, params, cache_key, timeout=10)
        
        incidents = []
        if data and 'results' in data:
            for result in data['results']:
                location = result.get('location', {})
                incident_details = result.get('incidentDetails', {})
                
                incident = {
                    'id': result.get('incidentId', ''),
                    'type': incident_details.get('type', 'unknown'),
                    'criticality': incident_details.get('criticality', 0),
                    'description': incident_details.get('description', ''),
                    'start_time': incident_details.get('startTime', ''),
                    'end_time': incident_details.get('endTime', ''),
                    'position': location.get('shape', {}).get('links', [{}])[0].get('points', [{}])[0] if location.get('shape') else {},
                    'road_name': location.get('description', ''),
                    'impact_level': self._calculate_impact_level(incident_details),
                    'estimated_duration': self._calculate_incident_duration(incident_details)
                }
                incidents.append(incident)
        
        return incidents
    
    def calculate_isoline(self, lat: float, lng: float, range_type: str, range_value: int, transport_mode: str = 'car') -> Optional[Dict]:
        """Calculer les isolignes (zones accessibles en X temps/distance)"""
        
        url = "https://isoline.router.hereapi.com/v8/isolines"
        
        params = {
            'transportMode': transport_mode,
            'origin': f"{lat},{lng}",
            'range[type]': range_type,  # 'time' ou 'distance'
            'range[values]': str(range_value),
            'routingMode': 'fast',
            'departure': datetime.now().isoformat()
        }
        
        cache_key = f"isoline_{lat}_{lng}_{range_type}_{range_value}_{transport_mode}"
        data = self._make_request(url, params, cache_key)
        
        if data and 'isolines' in data:
            return {
                'isolines': data['isolines'],
                'center': {'lat': lat, 'lng': lng},
                'range_type': range_type,
                'range_value': range_value
            }
        
        return None
    
    def get_places_nearby(self, lat: float, lng: float, category: str, radius: int = 2000, limit: int = 10) -> List[Dict]:
        """Récupérer les lieux d'intérêt à proximité"""
        
        url = "https://discover.search.hereapi.com/v1/discover"
        
        params = {
            'at': f"{lat},{lng}",
            'categories': category,
            'limit': limit,
            'lang': 'fr'
        }
        
        if radius:
            params['in'] = f"circle:{lat},{lng};r={radius}"
        
        cache_key = f"places_{lat}_{lng}_{category}_{radius}_{limit}"
        data = self._make_request(url, params, cache_key)
        
        places = []
        if data and 'items' in data:
            for item in data['items']:
                place = {
                    'id': item.get('id', ''),
                    'title': item.get('title', ''),
                    'category': item.get('categories', [{}])[0].get('name', '') if item.get('categories') else '',
                    'position': item.get('position', {}),
                    'distance': item.get('distance', 0),
                    'address': item.get('address', {}).get('label', ''),
                    'contacts': item.get('contacts', []),
                    'opening_hours': item.get('openingHours', []),
                    'rating': item.get('rating', {}).get('average', 0) if item.get('rating') else 0
                }
                places.append(place)
        
        return places
    
    def calculate_matrix(self, origins: List[Dict], destinations: List[Dict], transport_mode: str = 'car', traffic: bool = True) -> Optional[Dict]:
        """Calculer une matrice de distances/temps entre plusieurs points"""
        
        url = "https://matrix.router.hereapi.com/v8/matrix"
        
        # Préparer les origines et destinations
        origins_str = '|'.join([f"{o['lat']},{o['lng']}" for o in origins])
        destinations_str = '|'.join([f"{d['lat']},{d['lng']}" for d in destinations])
        
        params = {
            'origins': origins_str,
            'destinations': destinations_str,
            'transportMode': transport_mode,
            'matrixAttributes': 'distances,travelTimes',
            'routingMode': 'fast',
            'units': 'metric'
        }
        
        if traffic:
            params['departure'] = datetime.now().isoformat()
        
        cache_key = f"matrix_{hash(origins_str)}_{hash(destinations_str)}_{transport_mode}_{traffic}"
        data = self._make_request(url, params, cache_key)
        
        if data and 'matrix' in data:
            return {
                'matrix': data['matrix'],
                'origins': origins,
                'destinations': destinations,
                'metadata': {
                    'transport_mode': transport_mode,
                    'traffic_enabled': traffic,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
        
        return None
    
    def _calculate_traffic_level(self, current_flow: Dict) -> str:
        """Calculer le niveau de trafic basé sur les données de flow"""
        
        jam_factor = current_flow.get('jamFactor', 0)
        
        if jam_factor < 2:
            return 'free'
        elif jam_factor < 4:
            return 'light'
        elif jam_factor < 7:
            return 'moderate'
        elif jam_factor < 10:
            return 'heavy'
        else:
            return 'severe'
    
    def _calculate_impact_level(self, incident_details: Dict) -> str:
        """Calculer l'impact d'un incident"""
        
        criticality = incident_details.get('criticality', 0)
        incident_type = incident_details.get('type', '')
        
        if criticality >= 8 or incident_type in ['roadClosure', 'majorEvent']:
            return 'severe'
        elif criticality >= 5:
            return 'high'
        elif criticality >= 3:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_incident_duration(self, incident_details: Dict) -> Optional[int]:
        """Calculer la durée estimée d'un incident en minutes"""
        
        start_time = incident_details.get('startTime')
        end_time = incident_details.get('endTime')
        
        if start_time and end_time:
            try:
                start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                duration = (end - start).total_seconds() / 60
                return int(duration)
            except:
                pass
        
        # Estimation basée sur le type d'incident
        incident_type = incident_details.get('type', '')
        criticality = incident_details.get('criticality', 0)
        
        if incident_type == 'roadClosure':
            return 120  # 2 heures
        elif incident_type == 'accident':
            return 30 + (criticality * 10)  # 30min + 10min par niveau de criticité
        elif incident_type == 'construction':
            return 60  # 1 heure
        else:
            return 15  # 15 minutes par défaut
    
    def check_service_status(self) -> Dict:
        """Vérifier le statut des services HERE"""
        
        try:
            # Test simple de géocodage
            test_result = self.geocode_address("Paris, France", limit=1)
            
            return {
                'routing': 'operational',
                'geocoding': 'operational' if test_result else 'degraded',
                'traffic': 'operational',
                'last_check': datetime.utcnow().isoformat()
            }
        except:
            return {
                'routing': 'down',
                'geocoding': 'down',
                'traffic': 'down',
                'last_check': datetime.utcnow().isoformat()
            }
    
    def get_current_time(self) -> str:
        """Récupérer l'heure actuelle ISO"""
        return datetime.utcnow().isoformat()
    
    def clear_cache(self):
        """Vider le cache"""
        self._cache.clear()