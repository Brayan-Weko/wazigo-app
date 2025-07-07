import time
from datetime import datetime
from flask import current_app
from .here_api import HereApiService
from .route_optimizer import RouteOptimizer
from .traffic_analyzer import TrafficAnalyzer

class RouteService:
    """Service principal pour la recherche d'itinéraires."""
    
    def __init__(self):
        self.here_service = HereApiService()
        self.route_optimizer = RouteOptimizer()
        self.traffic_analyzer = TrafficAnalyzer()
    
    def find_optimal_routes(self, origin, destination, **kwargs):
        """
        Trouver les itinéraires optimaux.
        """
        start_time = time.time()
        
        try:
            current_app.logger.info(f"RouteService: Searching routes from {origin} to {destination}")
            
            # Validation des paramètres
            if not self._validate_locations(origin, destination):
                return {
                    'success': False,
                    'error': {
                        'message': 'Données de localisation invalides',
                        'code': 'INVALID_LOCATIONS'
                    }
                }
            
            # Préparer les paramètres pour HERE Maps
            here_params = self._prepare_here_params(origin, destination, **kwargs)
            current_app.logger.info(f"HERE params prepared: {here_params}")
            
            # Appel au service HERE Maps
            here_result = self.here_service.calculate_routes(here_params)
            
            if not here_result or 'routes' not in here_result:
                current_app.logger.error("No routes returned from HERE API")
                return {
                    'success': False,
                    'error': {
                        'message': 'Aucun itinéraire trouvé',
                        'code': 'NO_ROUTES_FOUND'
                    },
                    'query_time': time.time() - start_time
                }
            
            current_app.logger.info(f"HERE returned {len(here_result['routes'])} routes")
            
            # Traiter et enrichir les résultats avec l'optimiseur
            raw_routes = here_result['routes']
            optimized_routes = self.route_optimizer.optimize_routes(raw_routes, kwargs)
            
            current_app.logger.info(f"Optimized to {len(optimized_routes)} routes")
            
            # Analyser le trafic pour chaque route
            for i, route in enumerate(optimized_routes):
                try:
                    traffic_analysis = self.traffic_analyzer.analyze_route_traffic(route.get('original_data', route))
                    route['traffic_analysis'] = traffic_analysis.get('global_analysis', {})
                    route['critical_points'] = traffic_analysis.get('critical_points', [])
                except Exception as e:
                    current_app.logger.warning(f"Traffic analysis failed for route {i}: {str(e)}")
                    route['traffic_analysis'] = {}
                    route['critical_points'] = []
            
            return {
                'success': True,
                'routes': optimized_routes,
                'query_time': time.time() - start_time,
                'metadata': {
                    'provider': 'HERE Maps',
                    'alternatives_requested': kwargs.get('alternatives', 3),
                    'subscription_type': kwargs.get('subscription_type', 'free'),
                    'routes_found': len(optimized_routes)
                }
            }
            
        except Exception as e:
            current_app.logger.error(f'Erreur RouteService: {str(e)}', exc_info=True)
            return {
                'success': False,
                'error': {
                    'message': 'Erreur lors de la recherche d\'itinéraires',
                    'code': 'SERVICE_ERROR',
                    'details': str(e) if current_app.debug else None
                },
                'query_time': time.time() - start_time
            }
    
    def _validate_locations(self, origin, destination):
        """Valider les données de localisation."""
        try:
            # Vérifier que les données sont des dictionnaires
            if not isinstance(origin, dict) or not isinstance(destination, dict):
                current_app.logger.warning(f"Locations not dict: origin={type(origin)}, dest={type(destination)}")
                return False
            
            # Vérifier qu'au minimum une adresse est fournie
            origin_valid = (
                origin.get('address') or 
                (origin.get('lat') is not None and origin.get('lng') is not None)
            )
            
            destination_valid = (
                destination.get('address') or 
                (destination.get('lat') is not None and destination.get('lng') is not None)
            )
            
            if not origin_valid:
                current_app.logger.warning(f"Invalid origin: {origin}")
            if not destination_valid:
                current_app.logger.warning(f"Invalid destination: {destination}")
            
            return origin_valid and destination_valid
            
        except Exception as e:
            current_app.logger.error(f"Error validating locations: {str(e)}")
            return False
    
    def _prepare_here_params(self, origin, destination, **kwargs):
        """Préparer les paramètres pour l'API HERE Maps."""
        
        params = {
            'origin': self._format_location_for_here(origin),
            'destination': self._format_location_for_here(destination),
            'route_type': kwargs.get('route_type', 'fastest'),
            'avoid_tolls': kwargs.get('avoid_tolls', False),
            'avoid_highways': kwargs.get('avoid_highways', False),
            'avoid_ferries': kwargs.get('avoid_ferries', False),
            'alternatives': kwargs.get('alternatives', 3)
        }
        
        departure_time = kwargs.get('departure_time')
        if departure_time and str(departure_time).strip():
            params['departure_time'] = str(departure_time).strip()
        
        # Appliquer les limites d'abonnement
        subscription_type = kwargs.get('subscription_type', 'free')
        if subscription_type in ['guest', 'free']:
            # Limiter le rayon de trafic pour les utilisateurs gratuits
            traffic_radius = kwargs.get('traffic_radius_km', 45)
            params['traffic_radius_km'] = traffic_radius
        
        return params
    
    def _format_location_for_here(self, location):
        """Formater une localisation pour l'API HERE Maps."""
        try:
            current_app.logger.info(f"Formatting location: {location}")
            
            # Si on a des coordonnées précises, les utiliser
            if location.get('lat') is not None and location.get('lng') is not None:
                try:
                    lat = float(location['lat'])
                    lng = float(location['lng'])
                    
                    # Valider les coordonnées
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        formatted = f"{lat},{lng}"
                        current_app.logger.info(f"Using coordinates: {formatted}")
                        return formatted
                    else:
                        current_app.logger.error(f"Invalid coordinates: lat={lat}, lng={lng}")
                except (ValueError, TypeError) as e:
                    current_app.logger.error(f"Error converting coordinates: {e}")
            
            # Sinon utiliser l'adresse
            address = location.get('address', '')
            if isinstance(address, str) and address.strip():
                formatted = address.strip()
                current_app.logger.info(f"Using address: {formatted}")
                return formatted
            
            # Fallback
            current_app.logger.error(f"No valid location format found: {location}")
            raise ValueError(f"Format de localisation invalide: {location}")
            
        except Exception as e:
            current_app.logger.error(f"Error formatting location {location}: {str(e)}")
            raise ValueError(f"Impossible de formater la localisation: {location}")