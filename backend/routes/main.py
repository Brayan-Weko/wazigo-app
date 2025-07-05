from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from backend.models import User, SavedRoute, RouteHistory, UserAnalytics, db
from backend.services.route_optimizer import RouteOptimizer
from backend.utils.decorators import optional_login_required
import uuid

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Page d'accueil de l'application"""
    
    # Statistiques globales pour la page d'accueil
    stats = {
        'total_routes': RouteHistory.query.count(),
        'total_users': User.query.filter_by(is_active=True).count(),
        'total_time_saved': db.session.query(db.func.sum(RouteHistory.time_saved_seconds)).scalar() or 0,
        'average_score': db.session.query(db.func.avg(RouteHistory.optimization_score)).scalar() or 0
    }
    
    # Convertir le temps économisé en heures
    stats['total_time_saved_hours'] = stats['total_time_saved'] // 3600
    stats['average_score'] = round(float(stats['average_score']), 1) if stats['average_score'] else 0
    
    # Routes populaires récentes
    popular_routes = RouteHistory.get_popular_routes(days=7, limit=5)
    
    return render_template('index.html', 
                         stats=stats, 
                         popular_routes=popular_routes)

@main_bp.route('/search')
@optional_login_required
def search():
    """Page de recherche d'itinéraire"""
    
    user_id = session.get('user', {}).get('id')
    saved_routes = []
    recent_routes = []
    
    if user_id:
        # Récupérer les itinéraires sauvegardés
        saved_routes = SavedRoute.get_user_routes(user_id, include_favorites_only=True)
        
        # Récupérer l'historique récent
        user = User.get_by_id(user_id)
        if user:
            recent_routes = user.get_recent_routes(limit=5)
    
    # Récupérer les paramètres de l'URL (si redirection depuis une autre page)
    search_params = {
        'origin': request.args.get('origin', ''),
        'destination': request.args.get('destination', ''),
        'departure_time': request.args.get('departure_time', ''),
        'route_type': request.args.get('route_type', 'fastest')
    }
    
    return render_template('search.html', 
                         saved_routes=saved_routes,
                         recent_routes=recent_routes,
                         search_params=search_params)

@main_bp.route('/results')
@optional_login_required
def results():
    """Page d'affichage des résultats d'itinéraire"""
    
    # Récupérer les paramètres de recherche
    origin = request.args.get('origin')
    destination = request.args.get('destination')
    
    if not origin or not destination:
        flash('Veuillez spécifier un point de départ et une destination.', 'error')
        return redirect(url_for('main.search'))
    
    # Stocker les paramètres de recherche en session pour la page de résultats
    search_data = {
        'origin': origin,
        'destination': destination,
        'departure_time': request.args.get('departure_time', ''),
        'avoid_tolls': request.args.get('avoid_tolls') == 'true',
        'avoid_highways': request.args.get('avoid_highways') == 'true',
        'avoid_ferries': request.args.get('avoid_ferries') == 'true',
        'route_type': request.args.get('route_type', 'fastest')
    }
    
    session['current_search'] = search_data
    
    return render_template('results.html', search_data=search_data)

@main_bp.route('/navigation')
@optional_login_required
def navigation():
    """Page de navigation en temps réel"""
    
    route_id = request.args.get('route_id')
    if not route_id:
        flash('Aucun itinéraire sélectionné pour la navigation.', 'error')
        return redirect(url_for('main.search'))
    
    # Récupérer les données de l'itinéraire
    route_history = RouteHistory.get_by_id(route_id)
    if not route_history:
        flash('Itinéraire introuvable.', 'error')
        return redirect(url_for('main.search'))
    
    # Marquer l'itinéraire comme commencé
    route_history.mark_as_started()
    
    return render_template('navigation.html', 
                         route_data=route_history.to_dict(include_detailed_route=True))

@main_bp.route('/history')
@optional_login_required
def history():
    """Page d'historique des trajets"""
    
    user_id = session.get('user', {}).get('id')
    session_id = session.get('session_id')
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    if user_id:
        # Historique de l'utilisateur connecté
        history_query = RouteHistory.query.filter_by(user_id=user_id)
        user_analytics = UserAnalytics.get_or_create(user_id)
        analytics_data = user_analytics.to_dict()
    else:
        # Historique de la session pour utilisateur anonyme
        history_query = RouteHistory.query.filter_by(session_id=session_id)
        analytics_data = RouteHistory.get_analytics_data(days=30)
    
    # Filtres optionnels
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    if date_from:
        from datetime import datetime
        history_query = history_query.filter(RouteHistory.created_at >= datetime.fromisoformat(date_from))
    
    if date_to:
        from datetime import datetime
        history_query = history_query.filter(RouteHistory.created_at <= datetime.fromisoformat(date_to))
    
    # Pagination
    history_pagination = (history_query
                         .order_by(RouteHistory.created_at.desc())
                         .paginate(page=page, per_page=per_page, error_out=False))
    
    return render_template('history.html', 
                         history_pagination=history_pagination,
                         analytics_data=analytics_data)

@main_bp.route('/analytics')
@optional_login_required
def analytics():
    """Page d'analytics et statistiques"""
    
    user_id = session.get('user', {}).get('id')
    
    if not user_id:
        flash('Veuillez vous connecter pour accéder aux analytics détaillés.', 'info')
        return redirect(url_for('auth.login'))
    
    user_analytics = UserAnalytics.get_or_create(user_id)
    user_analytics.update_from_route_history()
    
    # Données pour les graphiques
    analytics_data = {
        'summary': user_analytics.to_dict(),
        'weekly_stats': user_analytics.get_weekly_stats(),
        'monthly_trends': user_analytics.get_monthly_trends(),
        'efficiency_score': user_analytics.get_efficiency_score()
    }
    
    return render_template('analytics.html', analytics_data=analytics_data)

@main_bp.route('/settings')
@optional_login_required
def settings():
    """Page des paramètres utilisateur"""
    
    user_id = session.get('user', {}).get('id')
    
    if not user_id:
        flash('Veuillez vous connecter pour accéder aux paramètres.', 'info')
        return redirect(url_for('auth.login'))
    
    user = User.get_by_id(user_id)
    if not user:
        flash('Utilisateur introuvable.', 'error')
        return redirect(url_for('main.index'))
    
    # Récupérer les itinéraires sauvegardés pour la gestion
    saved_routes = SavedRoute.get_user_routes(user_id)
    
    return render_template('settings.html', 
                         user=user, 
                         saved_routes=saved_routes)

@main_bp.route('/profile')
@optional_login_required
def profile():
    """Page de profil utilisateur"""
    
    user_id = session.get('user', {}).get('id')
    
    if not user_id:
        flash('Veuillez vous connecter pour accéder à votre profil.', 'info')
        return redirect(url_for('auth.login'))
    
    user = User.get_by_id(user_id)
    if not user:
        flash('Utilisateur introuvable.', 'error')
        return redirect(url_for('main.index'))
    
    # Statistiques du profil
    user_analytics = UserAnalytics.get_or_create(user_id)
    favorite_routes = user.get_favorite_routes()
    recent_activity = user.get_recent_routes(limit=10)
    
    profile_data = {
        'user': user.to_dict(include_sensitive=True),
        'analytics': user_analytics.to_dict(),
        'favorite_routes': [route.to_dict() for route in favorite_routes],
        'recent_activity': [route.to_dict() for route in recent_activity]
    }
    
    return render_template('profile.html', profile_data=profile_data)

@main_bp.route('/about')
def about():
    """Page à propos de l'application"""
    
    # Statistiques globales pour la page about
    global_stats = {
        'total_routes_calculated': RouteHistory.query.count(),
        'total_active_users': User.query.filter_by(is_active=True).count(),
        'total_time_saved_hours': (db.session.query(db.func.sum(RouteHistory.time_saved_seconds)).scalar() or 0) // 3600,
        'average_optimization_score': round(float(db.session.query(db.func.avg(RouteHistory.optimization_score)).scalar() or 0), 1)
    }
    
    return render_template('about.html', global_stats=global_stats)

# Routes utilitaires

@main_bp.route('/health')
def health_check():
    """Endpoint de vérification de santé de l'application"""
    try:
        # Vérifier la connexion à la base de données
        db.session.execute('SELECT 1')
        
        return jsonify({
            'status': 'healthy',
            'timestamp': db.func.now(),
            'version': '1.0.0'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

@main_bp.route('/privacy')
def privacy():
    """Page de politique de confidentialité"""
    return render_template('legal/privacy.html')

@main_bp.route('/terms')
def terms():
    """Page des conditions d'utilisation"""
    return render_template('legal/terms.html')

# Gestion des erreurs spécifiques au blueprint

@main_bp.errorhandler(404)
def page_not_found(error):
    """Gestionnaire d'erreur 404 pour le blueprint main"""
    return render_template('errors/404.html'), 404

@main_bp.errorhandler(500)
def internal_server_error(error):
    """Gestionnaire d'erreur 500 pour le blueprint main"""
    db.session.rollback()
    return render_template('errors/500.html'), 500