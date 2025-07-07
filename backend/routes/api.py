import json
from flask import Blueprint, request, jsonify, session, current_app, redirect, url_for
from backend.models import User, SavedRoute, RouteHistory, UserAnalytics, Feedback, db
from backend.services.here_api import HereApiService
from backend.services.route_optimizer import RouteOptimizer
from backend.services.traffic_analyzer import TrafficAnalyzer
from backend.utils.decorators import api_login_required, rate_limit
from datetime import datetime
import uuid

api_bp = Blueprint('api', __name__)

# Routes de recherche d'itinéraire

@api_bp.route('/search-routes', methods=['POST'])
@rate_limit('30 per minute')
def search_routes():
    """Rechercher des itinéraires optimisés"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {'message': 'Données manquantes', 'code': 'VALIDATION_ERROR'}
            }), 400
        
        # ✅ CORRECTION: Log des données reçues pour debug
        current_app.logger.info(f"Données reçues: {data}")

        # Validation et nettoyage des données de localisation
        origin_data = data.get('origin')
        destination_data = data.get('destination')

        current_app.logger.info(f"Origin raw: {origin_data}")
        current_app.logger.info(f"Destination raw: {destination_data}")
        
        # Nettoyer et normaliser les données de localisation
        origin_info = normalize_location_data(origin_data)
        destination_info = normalize_location_data(destination_data)

        current_app.logger.info(f"Origin normalized: {origin_info}")
        current_app.logger.info(f"Destination normalized: {destination_info}")
        
        # Validation plus détaillée avec messages spécifiques
        if not origin_info:
            return jsonify({
                'success': False,
                'error': {
                    'message': 'Point de départ invalide ou manquant',
                    'code': 'INVALID_ORIGIN',
                    'details': f'Données reçues: {origin_data}'
                }
            }), 400
            
        if not destination_info:
            return jsonify({
                'success': False,
                'error': {
                    'message': 'Point d\'arrivée invalide ou manquant',
                    'code': 'INVALID_DESTINATION', 
                    'details': f'Données reçues: {destination_data}'
                }
            }), 400
        
        # Vérifier que les adresses ne sont pas vides
        if not origin_info.get('address') or not origin_info['address'].strip():
            return jsonify({
                'success': False,
                'error': {
                    'message': 'Adresse de départ vide',
                    'code': 'EMPTY_ORIGIN_ADDRESS'
                }
            }), 400
            
        if not destination_info.get('address') or not destination_info['address'].strip():
            return jsonify({
                'success': False,
                'error': {
                    'message': 'Adresse d\'arrivée vide',
                    'code': 'EMPTY_DESTINATION_ADDRESS'
                }
            }), 400

        # Vérifier les limites d'abonnement
        user_id = session.get('user', {}).get('id')
        subscription_check = check_user_limits(user_id, 'search')
        
        if not subscription_check['allowed']:
            return jsonify({
                'success': False,
                'error': {
                    'message': 'Limite de recherches atteinte',
                    'code': 'LIMIT_EXCEEDED',
                    'limits': subscription_check['limits']
                }
            }), 429

        # Préparer les paramètres de recherche
        search_params = {
            'origin': origin_info,
            'destination': destination_info,
            'departure_time': data.get('departure_time'),
            'route_type': data.get('route_type', 'fastest'),
            'avoid_tolls': data.get('avoid_tolls', False),
            'avoid_highways': data.get('avoid_highways', False),
            'avoid_ferries': data.get('avoid_ferries', False),
            'alternatives': min(int(data.get('alternatives', 3)), 5),
            'subscription_type': subscription_check.get('subscription_type', 'guest'),
            'traffic_radius_km': subscription_check.get('limits', {}).get('traffic_radius_km', 45)
        }

        # Rechercher les itinéraires
        from backend.services.route_service import RouteService
        route_service = RouteService()
        
        routes_result = route_service.find_optimal_routes(**search_params)
        
        if not routes_result['success']:
            return jsonify({
                'success': False,
                'error': routes_result['error']
            }), 500

        # Enregistrer dans l'historique si utilisateur connecté
        if user_id:
            save_route_to_history(user_id, search_params, routes_result['routes'])
            
            # Incrémenter le compteur d'usage
            track_user_usage(user_id, 'search')

        # Préparer la réponse
        response_data = {
            'success': True,
            'routes': routes_result['routes'],
            'search_metadata': {
                'query_time': routes_result.get('query_time', 0),
                'total_routes': len(routes_result['routes']),
                'subscription_type': subscription_check.get('subscription_type', 'guest'),
                'traffic_radius_applied': search_params['traffic_radius_km'],
                'timestamp': datetime.utcnow().isoformat()
            }
        }

        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f'Erreur recherche itinéraires: {str(e)}')
        return jsonify({
            'success': False,
            'error': {
                'message': 'Erreur lors de la recherche d\'itinéraires',
                'code': 'SEARCH_ERROR'
            }
        }), 500

def normalize_location_data(location_data):
    """Normaliser les données de localisation en format standard."""
    if not location_data:
        return None
    
    # Si c'est déjà une string (adresse simple)
    if isinstance(location_data, str):
        address = location_data.strip()
        if not address:
            return None
        return {
            'address': address,
            'lat': None,
            'lng': None,
            'type': 'address'
        }
    
    # Si c'est un dictionnaire (données structurées)
    if isinstance(location_data, dict):
        address = location_data.get('address', '').strip()
        lat = location_data.get('lat')
        lng = location_data.get('lng')
        
        # Cas 1: Coordonnées GPS avec adresse
        if lat is not None and lng is not None:
            try:
                lat_float = float(lat)
                lng_float = float(lng)
                # Valider les coordonnées
                if -90 <= lat_float <= 90 and -180 <= lng_float <= 180:
                    return {
                        'address': address if address else f"{lat_float}, {lng_float}",
                        'lat': lat_float,
                        'lng': lng_float,
                        'type': 'coordinates',
                        'country': location_data.get('country'),
                        'source': location_data.get('source', 'manual')
                    }
            except (ValueError, TypeError):
                pass
        
        # Cas 2: Adresse avec métadonnées (sans coordonnées valides)
        if address:
            return {
                'address': address,
                'lat': lat,
                'lng': lng,
                'type': 'address',
                'country': location_data.get('country'),
                'source': location_data.get('source', 'manual')
            }
        
        # Cas 3: Format HERE Maps/Google
        if 'title' in location_data and 'position' in location_data:
            title = str(location_data['title']).strip()
            pos = location_data['position']
            if title and pos.get('lat') is not None and pos.get('lng') is not None:
                return {
                    'address': title,
                    'lat': pos.get('lat'),
                    'lng': pos.get('lng'),
                    'type': 'geocoded'
                }
    
    # ✅ Log pour debug
    current_app.logger.warning(f"Failed to normalize location data: {location_data}")
    return None
    """
    # Fallback: convertir en string
    try:
        return {
            'address': str(location_data).strip(),
            'lat': None,
            'lng': None,
            'type': 'fallback'
        }
    except:
        return None
    """

def check_user_limits(user_id, action):
    """Vérifier les limites d'utilisation de l'utilisateur."""
    try:
        if not user_id:
            # Utilisateur invité
            return {
                'allowed': True,
                'subscription_type': 'guest',
                'limits': {
                    'traffic_radius_km': 45,
                    'daily_searches': 10,
                    'countries_access': 1,
                    'has_ads': True
                }
            }
        
        from backend.models.user import User
        user = User.get_by_id(user_id)
        
        if not user:
            # Utilisateur non trouvé, traiter comme invité
            return {
                'allowed': True,
                'subscription_type': 'guest',
                'limits': {
                    'traffic_radius_km': 45,
                    'daily_searches': 10,
                    'countries_access': 1,
                    'has_ads': True
                }
            }
        
        # Récupérer les limites d'abonnement
        if hasattr(user, 'get_subscription_limits'):
            limits = user.get_subscription_limits()
            subscription_type = user.subscription_type if hasattr(user, 'subscription_type') else 'free'
            
            # Vérifier les limites de recherche
            if action == 'search':
                if hasattr(user, 'can_search'):
                    allowed = user.can_search()
                else:
                    allowed = True  # Par défaut autorisé
                
                return {
                    'allowed': allowed,
                    'subscription_type': subscription_type,
                    'limits': limits
                }
        
        # Fallback pour utilisateur sans abonnement
        return {
            'allowed': True,
            'subscription_type': 'free',
            'limits': {
                'traffic_radius_km': 45,
                'daily_searches': 50,
                'countries_access': 1,
                'has_ads': True
            }
        }
        
    except Exception as e:
        current_app.logger.warning(f'Erreur vérification limites: {str(e)}')
        # En cas d'erreur, autoriser avec limites de base
        return {
            'allowed': True,
            'subscription_type': 'free',
            'limits': {
                'traffic_radius_km': 45,
                'daily_searches': 50,
                'countries_access': 1,
                'has_ads': True
            }
        }

def save_route_to_history(user_id, search_params, routes):
    """Sauvegarder la recherche dans l'historique utilisateur."""
    try:
        if not routes or len(routes) == 0:
            return
        
        from backend.models.history import RouteHistory
        from flask import session

        best_route = routes[0]
        
        # Adapter à la structure des routes optimisées
        if 'summary' in best_route:
            summary = best_route['summary']
        elif 'original_data' in best_route:
            summary = best_route['original_data'].get('summary', {})
        else:
            summary = {}

        session_id = session.get('session_id', 'default_session')
        if not session_id or session_id == 'default_session':
            import uuid
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id

        # Préparer selected_route_data selon le format attendu
        selected_route_data = {
            'route_type': search_params.get('route_type', 'fastest'),
            'summary': summary,
            'optimization_score': best_route.get('optimization_score', 0),
            'traffic_analysis': best_route.get('traffic_analysis', {}),
            'alternatives_count': len(routes),
            'search_options': {
                'avoid_tolls': search_params.get('avoid_tolls', False),
                'avoid_highways': search_params.get('avoid_highways', False),
                'avoid_ferries': search_params.get('avoid_ferries', False)
            }
        }

        origin_lat = search_params['origin'].get('lat', 0)
        origin_lng = search_params['origin'].get('lng', 0)
        dest_lat = search_params['destination'].get('lat', 0)
        dest_lng = search_params['destination'].get('lng', 0)

        try:
            origin_lat = float(origin_lat) if origin_lat is not None else 0.0
            origin_lng = float(origin_lng) if origin_lng is not None else 0.0
            dest_lat = float(dest_lat) if dest_lat is not None else 0.0
            dest_lng = float(dest_lng) if dest_lng is not None else 0.0
        except (ValueError, TypeError):
            current_app.logger.warning("Invalid coordinates, using defaults")
            origin_lat = origin_lng = dest_lat = dest_lng = 0.0
        
        # Créer l'entrée avec la signature correcte
        history_entry = RouteHistory(
            session_id=session_id,
            origin_address=search_params['origin']['address'][:250],
            origin_lat=search_params['origin'].get('lat', 0),
            origin_lng=search_params['origin'].get('lng', 0),
            destination_address=search_params['destination']['address'][:250],
            destination_lat=search_params['destination'].get('lat', 0),
            destination_lng=search_params['destination'].get('lng', 0),
            selected_route_data=selected_route_data,
            travel_time_seconds=int(summary.get('duration', 0)),
            distance_meters=int(summary.get('length', 0)),
            optimization_score=float(best_route.get('optimization_score', 0)),
            user_id=user_id,
            time_saved_seconds=int(best_route.get('time_saved', 0))
        )

        # Ajouter les routes alternatives si disponibles
        if len(routes) > 1:
            alternative_routes = []
            for route in routes[1:]:  # Toutes sauf la première
                alt_summary = route.get('summary', {})
                if 'original_data' in route:
                    alt_summary = route['original_data'].get('summary', {})
                
                alternative_routes.append({
                    'duration': alt_summary.get('duration', 0),
                    'length': alt_summary.get('length', 0),
                    'optimization_score': route.get('optimization_score', 0)
                })
            
            history_entry.alternative_routes = alternative_routes
            history_entry.calculate_time_saved(alternative_routes)
        
        history_entry.save()
        current_app.logger.info(f'✅ Route sauvegardée dans historique: ID {history_entry.id}')
        
    except Exception as e:
        current_app.logger.warning(f'Erreur sauvegarde historique: {str(e)}')
        current_app.logger.error(f'Détails erreur - Origin: {search_params.get("origin")}, Dest: {search_params.get("destination")}')

def track_user_usage(user_id, action):
    """Tracker l'utilisation des fonctionnalités."""
    try:
        # Import direct pour éviter les conflits
        from backend.models.user import User
        user = User.get_by_id(user_id)
        
        if user and hasattr(user, 'subscription') and user.subscription:
            if action == 'search':
                user.subscription.increment_daily_searches()
        
        # Mettre à jour les analytics utilisateur si elles existent
        try:
            from backend.models.analytics import UserAnalytics
            analytics = UserAnalytics.get_or_create(user_id)
            if hasattr(analytics, 'total_routes_searched'):
                analytics.total_routes_searched += 1
            analytics.last_activity = datetime.utcnow()
            analytics.save()
        except Exception as analytics_error:
            current_app.logger.warning(f'Erreur mise à jour analytics: {str(analytics_error)}')

        # Traiter l'abonnement si disponible
        if hasattr(user, 'subscription') and user.subscription:
            if action == 'search' and hasattr(user.subscription, 'increment_daily_searches'):
                user.subscription.increment_daily_searches()
            
    except Exception as e:
        current_app.logger.warning(f'Erreur tracking usage: {str(e)}')

@api_bp.route('/geocode', methods=['POST'])
@rate_limit('60 per minute')
def geocode_address():
    """API pour géocoder une adresse"""
    
    try:
        data = request.get_json()
        address = data.get('address') if data else None
        
        if not address:
            return jsonify({'error': 'Adresse requise'}), 400
        
        here_api = HereApiService()
        geocode_result = here_api.geocode_address(address)
        
        if not geocode_result:
            return jsonify({'error': 'Adresse non trouvée'}), 404
        
        return jsonify({
            'success': True,
            'results': geocode_result
        })
        
    except Exception as e:
        current_app.logger.error(f'Erreur géocodage: {str(e)}')
        return jsonify({'error': 'Erreur lors du géocodage'}), 500

@api_bp.route('/autocomplete', methods=['GET'])
@rate_limit('100 per minute')
def autocomplete_address():
    """API pour l'autocomplétion d'adresses"""
    
    try:
        query = request.args.get('q', '').strip()
        if len(query) < 3:
            return jsonify({'suggestions': []})
        
        here_api = HereApiService()
        suggestions = here_api.autocomplete_address(query)
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        current_app.logger.error(f'Erreur autocomplétion: {str(e)}')
        return jsonify({'error': 'Erreur lors de l\'autocomplétion'}), 500

# Routes de gestion des itinéraires sauvegardés

@api_bp.route('/saved-routes', methods=['GET', 'POST'])
@api_login_required
def manage_saved_routes():
    """API pour gérer les itinéraires sauvegardés"""
    
    user_id = session['user']['id']
    
    if request.method == 'GET':
        # Récupérer les itinéraires sauvegardés
        favorites_only = request.args.get('favorites_only') == 'true'
        saved_routes = SavedRoute.get_user_routes(user_id, favorites_only)
        
        return jsonify({
            'success': True,
            'routes': [route.to_dict() for route in saved_routes]
        })
    
    elif request.method == 'POST':
        # Sauvegarder un nouvel itinéraire
        try:
            data = request.get_json()
            
            required_fields = ['name', 'origin_address', 'origin_lat', 'origin_lng', 
                             'destination_address', 'destination_lat', 'destination_lng']
            
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Champ {field} requis'}), 400
            
            # Vérifier si un itinéraire similaire existe déjà
            existing_route = SavedRoute.find_similar_route(
                user_id, 
                data['origin_lat'], 
                data['origin_lng'],
                data['destination_lat'], 
                data['destination_lng']
            )
            
            if existing_route:
                return jsonify({
                    'error': 'Un itinéraire similaire existe déjà',
                    'existing_route': existing_route.to_dict()
                }), 409
            
            # Créer le nouvel itinéraire
            saved_route = SavedRoute(
                name=data['name'],
                origin_address=data['origin_address'],
                origin_lat=data['origin_lat'],
                origin_lng=data['origin_lng'],
                destination_address=data['destination_address'],
                destination_lat=data['destination_lat'],
                destination_lng=data['destination_lng'],
                user_id=user_id,
                description=data.get('description')
            )
            
            # Ajouter des tags si fournis
            if 'tags' in data and isinstance(data['tags'], list):
                for tag in data['tags']:
                    saved_route.add_tag(tag)
            
            saved_route.save()
            
            return jsonify({
                'success': True,
                'route': saved_route.to_dict(),
                'message': 'Itinéraire sauvegardé avec succès'
            }), 201
            
        except Exception as e:
            current_app.logger.error(f'Erreur sauvegarde itinéraire: {str(e)}')
            return jsonify({'error': 'Erreur lors de la sauvegarde'}), 500

@api_bp.route('/saved-routes/<int:route_id>', methods=['GET', 'PUT', 'DELETE'])
@api_login_required
def manage_single_saved_route(route_id):
    """API pour gérer un itinéraire sauvegardé spécifique"""
    
    user_id = session['user']['id']
    saved_route = SavedRoute.query.filter_by(id=route_id, user_id=user_id).first()
    
    if not saved_route:
        return jsonify({'error': 'Itinéraire non trouvé'}), 404
    
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'route': saved_route.to_dict()
        })
    
    elif request.method == 'PUT':
        # Mettre à jour l'itinéraire
        try:
            data = request.get_json()
            
            if 'name' in data:
                saved_route.name = data['name']
            if 'description' in data:
                saved_route.description = data['description']
            if 'is_favorite' in data:
                saved_route.is_favorite = data['is_favorite']
            if 'tags' in data:
                saved_route.tags = data['tags']
            
            saved_route.save()
            
            return jsonify({
                'success': True,
                'route': saved_route.to_dict(),
                'message': 'Itinéraire mis à jour avec succès'
            })
            
        except Exception as e:
            current_app.logger.error(f'Erreur mise à jour itinéraire: {str(e)}')
            return jsonify({'error': 'Erreur lors de la mise à jour'}), 500
    
    elif request.method == 'DELETE':
        # Supprimer l'itinéraire
        try:
            saved_route.delete()
            
            return jsonify({
                'success': True,
                'message': 'Itinéraire supprimé avec succès'
            })
            
        except Exception as e:
            current_app.logger.error(f'Erreur suppression itinéraire: {str(e)}')
            return jsonify({'error': 'Erreur lors de la suppression'}), 500

@api_bp.route('/saved-routes/<int:route_id>/toggle-favorite', methods=['POST'])
@api_login_required
def toggle_favorite_route(route_id):
    """API pour basculer le statut favori d'un itinéraire"""
    
    user_id = session['user']['id']
    saved_route = SavedRoute.query.filter_by(id=route_id, user_id=user_id).first()
    
    if not saved_route:
        return jsonify({'error': 'Itinéraire non trouvé'}), 404
    
    try:
        is_favorite = saved_route.toggle_favorite()
        
        return jsonify({
            'success': True,
            'is_favorite': is_favorite,
            'message': f'Itinéraire {"ajouté aux" if is_favorite else "retiré des"} favoris'
        })
        
    except Exception as e:
        current_app.logger.error(f'Erreur toggle favori: {str(e)}')
        return jsonify({'error': 'Erreur lors de la mise à jour'}), 500

# Routes d'historique et analytics

@api_bp.route('/history', methods=['GET'])
def get_route_history():
    """API pour récupérer l'historique des trajets"""
    
    user_id = session.get('user', {}).get('id')
    session_id = session.get('session_id')
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    if user_id:
        history_query = RouteHistory.query.filter_by(user_id=user_id)
    else:
        history_query = RouteHistory.query.filter_by(session_id=session_id)
    
    # Filtres
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    if date_from:
        history_query = history_query.filter(RouteHistory.created_at >= date_from)
    if date_to:
        history_query = history_query.filter(RouteHistory.created_at <= date_to)
    
    # Pagination
    history_pagination = (history_query
                         .order_by(RouteHistory.created_at.desc())
                         .paginate(page=page, per_page=per_page, error_out=False))
    
    return jsonify({
        'success': True,
        'history': [route.to_dict() for route in history_pagination.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': history_pagination.total,
            'pages': history_pagination.pages,
            'has_next': history_pagination.has_next,
            'has_prev': history_pagination.has_prev
        }
    })

@api_bp.route('/analytics', methods=['GET'])
@api_login_required
def get_user_analytics():
    """API pour récupérer les analytics utilisateur"""
    
    user_id = session['user']['id']
    analytics = UserAnalytics.get_or_create(user_id)
    analytics.update_from_route_history()
    
    return jsonify({
        'success': True,
        'analytics': analytics.to_dict(),
        'weekly_stats': analytics.get_weekly_stats(),
        'monthly_trends': analytics.get_monthly_trends()
    })

# Routes de feedback

@api_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    """API pour soumettre un feedback"""
    
    try:
        data = request.get_json()
        
        required_fields = ['rating', 'feedback_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Champ {field} requis'}), 400
        
        # Validation de la note
        rating = data['rating']
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({'error': 'La note doit être entre 1 et 5'}), 400
        
        # Validation du type de feedback
        valid_types = ['route_quality', 'app_performance', 'feature_request', 'bug_report']
        if data['feedback_type'] not in valid_types:
            return jsonify({'error': 'Type de feedback invalide'}), 400
        
        # Créer le feedback
        feedback = Feedback(
            rating=rating,
            feedback_type=data['feedback_type'],
            comment=data.get('comment'),
            user_id=session.get('user', {}).get('id'),
            session_id=session.get('session_id'),
            route_id=data.get('route_id')
        )
        
        feedback.save()
        
        return jsonify({
            'success': True,
            'message': 'Merci pour votre feedback!',
            'feedback_id': feedback.id
        }), 201
        
    except Exception as e:
        current_app.logger.error(f'Erreur soumission feedback: {str(e)}')
        return jsonify({'error': 'Erreur lors de la soumission'}), 500

# Routes utilitaires

@api_bp.route('/traffic-status', methods=['GET'])
@rate_limit('60 per minute')
def get_traffic_status():
    """API pour récupérer le statut du trafic en temps réel"""
    
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        radius = request.args.get('radius', 5000, type=int)  # Rayon en mètres
        
        if not lat or not lng:
            return jsonify({'error': 'Coordonnées lat/lng requises'}), 400
        
        traffic_analyzer = TrafficAnalyzer()
        traffic_data = traffic_analyzer.get_traffic_status(lat, lng, radius)
        
        return jsonify({
            'success': True,
            'traffic_data': traffic_data,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f'Erreur statut trafic: {str(e)}')
        return jsonify({'error': 'Erreur lors de la récupération du trafic'}), 500

@api_bp.route('/route/<int:route_id>/start', methods=['POST'])
def start_navigation(route_id):
    """API pour démarrer la navigation d'un itinéraire"""
    
    try:
        route_history = RouteHistory.get_by_id(route_id)
        if not route_history:
            return jsonify({'error': 'Itinéraire non trouvé'}), 404
        
        # Vérifier que l'itinéraire appartient à l'utilisateur ou à la session
        user_id = session.get('user', {}).get('id')
        session_id = session.get('session_id')
        
        if route_history.user_id != user_id and route_history.session_id != session_id:
            return jsonify({'error': 'Accès non autorisé'}), 403
        
        # Marquer comme commencé
        route_history.mark_as_started()
        
        return jsonify({
            'success': True,
            'message': 'Navigation démarrée',
            'route': route_history.to_dict(include_detailed_route=True)
        })
        
    except Exception as e:
        current_app.logger.error(f'Erreur démarrage navigation: {str(e)}')
        return jsonify({'error': 'Erreur lors du démarrage'}), 500

@api_bp.route('/route/<int:route_id>/complete', methods=['POST'])
def complete_navigation(route_id):
    """API pour marquer un itinéraire comme terminé"""
    
    try:
        route_history = RouteHistory.get_by_id(route_id)
        if not route_history:
            return jsonify({'error': 'Itinéraire non trouvé'}), 404
        
        # Vérifier les permissions
        user_id = session.get('user', {}).get('id')
        session_id = session.get('session_id')
        
        if route_history.user_id != user_id and route_history.session_id != session_id:
            return jsonify({'error': 'Accès non autorisé'}), 403
        
        # Marquer comme terminé
        route_history.mark_as_completed()
        
        # Mettre à jour les analytics si utilisateur connecté
        if user_id:
            analytics = UserAnalytics.get_or_create(user_id)
            analytics.update_from_route_history()
        
        return jsonify({
            'success': True,
            'message': 'Trajet terminé avec succès',
            'route': route_history.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f'Erreur fin navigation: {str(e)}')
        return jsonify({'error': 'Erreur lors de la finalisation'}), 500  

@api_bp.route('/advertisements', methods=['GET'])
def get_advertisements():
    """Route de fallback pour les publicités."""
    try:
        # Rediriger vers la route subscription
        return redirect(url_for('subscription_api.get_advertisements'))
    except Exception as e:
        return jsonify({
            'success': True,
            'ads': [],
            'message': 'No ads available'
        })

@api_bp.route('/advertisements/impression', methods=['GET', 'POST'])
def track_advertisement_impression():
    """Route de fallback pour tracking impressions."""
    try:
        data = request.get_json()
        ad_id = data.get('ad_id')
        if ad_id:
            return redirect(url_for('subscription_api.track_ad_impression', ad_id=ad_id))
        return jsonify({'success': False, 'error': 'Missing ad_id'}), 400
    except Exception as e:
        return jsonify({'success': True})

@api_bp.route('/advertisements/click', methods=['POST'])  
def track_advertisement_click():
    """Route de fallback pour tracking clics."""
    try:
        return redirect(url_for('subscription_api.track_ad_click'))
    except Exception as e:
        return jsonify({'success': True})