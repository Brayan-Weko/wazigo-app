from flask import Blueprint, request, jsonify, session, current_app
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
    """API pour rechercher des itinéraires optimisés"""
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        # Validation des données
        required_fields = ['origin', 'destination']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Champ {field} requis'}), 400
        
        # Paramètres de recherche
        search_params = {
            'origin': data['origin'],
            'destination': data['destination'],
            'departure_time': data.get('departure_time'),
            'avoid_tolls': data.get('avoid_tolls', False),
            'avoid_highways': data.get('avoid_highways', False),
            'avoid_ferries': data.get('avoid_ferries', False),
            'route_type': data.get('route_type', 'fastest'),
            'alternatives': data.get('alternatives', 3)
        }
        
        # Rechercher les itinéraires avec HERE Maps
        here_api = HereApiService()
        routes_data = here_api.calculate_routes(search_params)
        
        if not routes_data or 'routes' not in routes_data:
            return jsonify({'error': 'Aucun itinéraire trouvé'}), 404
        
        # Analyser le trafic pour chaque itinéraire
        traffic_analyzer = TrafficAnalyzer()
        
        # Optimiser et scorer les itinéraires
        route_optimizer = RouteOptimizer()
        optimized_routes = route_optimizer.optimize_routes(
            routes_data['routes'], 
            search_params
        )
        
        # Sauvegarder dans l'historique
        user_id = session.get('user', {}).get('id')
        session_id = session.get('session_id')
        
        if optimized_routes:
            best_route = optimized_routes[0]
            
            history_entry = RouteHistory(
                session_id=session_id,
                origin_address=search_params['origin'],
                origin_lat=best_route['summary']['origin']['lat'],
                origin_lng=best_route['summary']['origin']['lng'],
                destination_address=search_params['destination'],
                destination_lat=best_route['summary']['destination']['lat'],
                destination_lng=best_route['summary']['destination']['lng'],
                selected_route_data=best_route,
                travel_time_seconds=best_route['summary']['duration'],
                distance_meters=best_route['summary']['length'],
                optimization_score=best_route['optimization_score'],
                user_id=user_id
            )
            
            # Calculer le temps économisé
            if len(optimized_routes) > 1:
                history_entry.calculate_time_saved([r['summary'] for r in optimized_routes[1:]])
            
            history_entry.save()
            
            # Mettre à jour les analytics si utilisateur connecté
            if user_id:
                analytics = UserAnalytics.get_or_create(user_id)
                analytics.update_from_route_history()
        
        return jsonify({
            'success': True,
            'routes': optimized_routes,
            'search_params': search_params,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f'Erreur recherche itinéraires: {str(e)}')
        return jsonify({'error': 'Erreur lors de la recherche d\'itinéraires'}), 500

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