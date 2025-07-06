from flask import Blueprint, request, jsonify, session
from backend.models import db, User, SubscriptionPlan, UserSubscription, Advertisement
from datetime import datetime, timedelta

# Fonctions d'authentification simples (sans import externe)
def require_auth(f):
    """Décorateur simple pour vérifier l'authentification."""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({
                'success': False,
                'error': {'message': 'Authentification requise', 'code': 'AUTH_REQUIRED'}
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def optional_auth(f):
    """Décorateur pour authentification optionnelle."""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Récupérer l'utilisateur actuel depuis la session."""
    if 'user' not in session:
        return None
    
    user_data = session.get('user')
    if not user_data or not user_data.get('id'):
        return None
    
    try:
        return User.get_by_id(user_data['id'])
    except Exception:
        return None

def is_premium_user():
    """Vérifier si l'utilisateur est premium."""
    user = get_current_user()
    return user and hasattr(user, 'is_premium') and user.is_premium

# Blueprint
subscription_bp = Blueprint('subscription_api', __name__)

@subscription_bp.route('/plans', methods=['GET'])
@optional_auth
def get_subscription_plans():
    """Récupérer les plans d'abonnement disponibles."""
    try:
        plans = SubscriptionPlan.query.filter_by(is_active=True).all()
        
        # Récupérer l'abonnement actuel si utilisateur connecté
        current_subscription = None
        current_user = get_current_user()
        if current_user and hasattr(current_user, 'subscription') and current_user.subscription:
            current_subscription = current_user.subscription.to_dict()
        
        return jsonify({
            'success': True,
            'plans': [plan.to_dict() for plan in plans],
            'current_subscription': current_subscription
        })
        
    except Exception as e:
        print(f"Error in get_subscription_plans: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'message': 'Erreur lors du chargement des plans', 'code': 'LOAD_ERROR'}
        }), 500

@subscription_bp.route('/simulate-upgrade', methods=['POST'])
@require_auth
def simulate_upgrade():
    """Simuler l'upgrade vers Premium (démonstration)."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': {'message': 'Utilisateur non trouvé', 'code': 'USER_NOT_FOUND'}
            }), 404
        
        data = request.get_json()
        plan_type = data.get('plan')  # 'monthly' or 'yearly'
        payment_method = data.get('payment_method')
        
        if not plan_type or not payment_method:
            return jsonify({
                'success': False,
                'error': {'message': 'Données manquantes', 'code': 'VALIDATION_ERROR'}
            }), 400
        
        # Récupérer le plan Premium
        premium_plan = SubscriptionPlan.query.filter_by(name='premium').first()
        if not premium_plan:
            return jsonify({
                'success': False,
                'error': {'message': 'Plan Premium non trouvé', 'code': 'PLAN_NOT_FOUND'}
            }), 404
        
        # Calculer la date d'expiration
        if plan_type == 'yearly':
            expires_at = datetime.utcnow() + timedelta(days=365)
            billing_period = 'yearly'
        else:
            expires_at = datetime.utcnow() + timedelta(days=30)
            billing_period = 'monthly'
        
        # Annuler l'ancien abonnement s'il existe
        if hasattr(current_user, 'subscription') and current_user.subscription:
            current_user.subscription.status = 'cancelled'
            current_user.subscription.cancelled_at = datetime.utcnow()
        
        # Créer le nouvel abonnement (simulation)
        new_subscription = UserSubscription(
            user_id=current_user.id,
            plan_id=premium_plan.id,
            status='active',
            billing_period=billing_period,
            started_at=datetime.utcnow(),
            expires_at=expires_at,
            payment_method=payment_method,
            last_payment_date=datetime.utcnow(),
            next_payment_date=expires_at
        )
        
        new_subscription.save()
        
        # Mettre à jour la session avec le nouveau statut
        if 'user' in session:
            session['user']['subscription_type'] = 'premium'
            session['user']['is_premium'] = True
        
        print(f"[SIMULATION] User {current_user.id} upgraded to Premium ({plan_type})")
        
        return jsonify({
            'success': True,
            'message': 'Simulation d\'upgrade réussie',
            'subscription': new_subscription.to_dict(),
            'simulation': True
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in simulate_upgrade: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'message': 'Erreur lors de la simulation', 'code': 'SIMULATION_ERROR'}
        }), 500

@subscription_bp.route('/check-limits', methods=['POST'])
@optional_auth
def check_subscription_limits():
    """Vérifier les limites d'abonnement pour une action."""
    try:
        data = request.get_json()
        action = data.get('action')  # 'search', 'traffic_access', etc.
        
        current_user = get_current_user()
        
        # Utilisateur anonyme - limites par défaut
        if not current_user:
            return jsonify({
                'success': True,
                'allowed': True,
                'limits': {
                    'traffic_radius_km': 45,
                    'daily_searches': 10,  # Plus restrictif pour les invités
                    'countries_access': 1,
                    'has_ads': True
                },
                'subscription_type': 'guest'
            })
        
        # Récupérer le plan actuel
        if (hasattr(current_user, 'subscription') and 
            current_user.subscription and 
            current_user.subscription.is_active):
            plan = current_user.subscription.plan
            subscription = current_user.subscription
        else:
            # Plan gratuit par défaut
            plan = SubscriptionPlan.query.filter_by(name='free').first()
            subscription = None
        
        # Vérifier les limites spécifiques
        allowed = True
        limit_details = {}
        
        if action == 'search':
            if subscription:
                allowed = subscription.can_search()
                limit_details = {
                    'daily_searches_used': subscription.daily_searches_used,
                    'daily_searches_limit': plan.daily_searches
                }
            else:
                # Limites pour utilisateurs gratuits non connectés
                allowed = True  # On laisse passer mais avec restrictions
                limit_details = {
                    'daily_searches_used': 0,
                    'daily_searches_limit': 50
                }
        
        subscription_type = 'free'
        if subscription and subscription.is_active:
            subscription_type = subscription.plan.name
        
        return jsonify({
            'success': True,
            'allowed': allowed,
            'plan': plan.to_dict() if plan else None,
            'limits': limit_details,
            'subscription_type': subscription_type
        })
        
    except Exception as e:
        print(f"Error in check_subscription_limits: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'message': 'Erreur lors de la vérification', 'code': 'CHECK_ERROR'}
        }), 500

@subscription_bp.route('/usage', methods=['POST'])
@require_auth
def track_usage():
    """Enregistrer l'utilisation d'une fonctionnalité."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': {'message': 'Utilisateur non trouvé', 'code': 'USER_NOT_FOUND'}
            }), 404
        
        data = request.get_json()
        action = data.get('action')
        
        if not hasattr(current_user, 'subscription') or not current_user.subscription:
            return jsonify({'success': True, 'message': 'No subscription to track'})
        
        # Incrémenter les compteurs selon l'action
        if action == 'search':
            current_user.subscription.increment_daily_searches()
        
        return jsonify({
            'success': True,
            'message': 'Usage tracked successfully'
        })
        
    except Exception as e:
        print(f"Error in track_usage: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'message': 'Erreur lors du tracking', 'code': 'TRACKING_ERROR'}
        }), 500

@subscription_bp.route('/status', methods=['GET'])
@optional_auth
def get_subscription_status():
    """Récupérer le statut d'abonnement de l'utilisateur."""
    try:
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({
                'success': True,
                'subscription_type': 'guest',
                'is_premium': False,
                'limits': {
                    'traffic_radius_km': 45,
                    'daily_searches': 10,
                    'countries_access': 1,
                    'has_ads': True
                }
            })
        
        # Récupérer les limites actuelles
        limits = current_user.get_subscription_limits() if hasattr(current_user, 'get_subscription_limits') else {
            'traffic_radius_km': 45,
            'daily_searches': 50,
            'countries_access': 1,
            'has_ads': True
        }
        
        return jsonify({
            'success': True,
            'user_id': current_user.id,
            'subscription_type': current_user.subscription_type if hasattr(current_user, 'subscription_type') else 'free',
            'is_premium': current_user.is_premium if hasattr(current_user, 'is_premium') else False,
            'subscription': current_user.subscription.to_dict() if hasattr(current_user, 'subscription') and current_user.subscription else None,
            'limits': limits
        })
        
    except Exception as e:
        print(f"Error in get_subscription_status: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'message': 'Erreur lors de la récupération du statut', 'code': 'STATUS_ERROR'}
        }), 500

# Endpoints pour les publicités
@subscription_bp.route('/advertisements', methods=['GET'])
@optional_auth
def get_advertisements():
    """Récupérer les publicités pour utilisateurs gratuits."""
    try:
        current_user = get_current_user()
        
        # Vérifier si l'utilisateur doit voir des publicités
        should_show_ads = True
        if current_user and hasattr(current_user, 'subscription') and current_user.subscription:
            if current_user.subscription.is_active:
                should_show_ads = current_user.subscription.plan.has_ads
        
        if not should_show_ads:
            return jsonify({
                'success': True,
                'ads': [],
                'message': 'Premium user - no ads'
            })
        
        # Récupérer les publicités actives
        ads = Advertisement.query.filter(
            Advertisement.is_active == True,
            Advertisement.start_date <= datetime.utcnow(),
            (Advertisement.end_date.is_(None)) | (Advertisement.end_date > datetime.utcnow())
        ).order_by(Advertisement.priority.desc()).limit(10).all()
        
        return jsonify({
            'success': True,
            'ads': [ad.to_dict() for ad in ads]
        })
        
    except Exception as e:
        print(f"Error in get_advertisements: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'message': 'Erreur lors du chargement des publicités', 'code': 'ADS_ERROR'}
        }), 500

@subscription_bp.route('/advertisements/impression', methods=['GET', 'POST'])
@optional_auth
def track_ad_impression():
    """Enregistrer une impression publicitaire."""
    try:
        if request.method == 'GET':
            ad_id = request.args.get('ad_id')
        else:
            data = request.get_json()
            ad_id = data.get('ad_id')
        
        if not ad_id:
            return jsonify({
                'success': False,
                'error': {'message': 'ID publicité manquant', 'code': 'VALIDATION_ERROR'}
            }), 400
        
        ad = Advertisement.query.get(ad_id)
        if ad:
            ad.increment_impression()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error in track_ad_impression: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'message': 'Erreur lors du tracking', 'code': 'TRACKING_ERROR'}
        }), 500

@subscription_bp.route('/advertisements/click', methods=['POST'])
@optional_auth
def track_ad_click():
    """Enregistrer un clic publicitaire."""
    try:
        data = request.get_json()
        ad_id = data.get('ad_id')
        
        if not ad_id:
            return jsonify({
                'success': False,
                'error': {'message': 'ID publicité manquant', 'code': 'VALIDATION_ERROR'}
            }), 400
        
        ad = Advertisement.query.get(ad_id)
        if ad:
            ad.increment_click()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error in track_ad_click: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'message': 'Erreur lors du tracking', 'code': 'TRACKING_ERROR'}
        }), 500

@subscription_bp.route('/cancel', methods=['POST'])
@require_auth
def cancel_subscription():
    """Annuler l'abonnement Premium."""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'error': {'message': 'Utilisateur non trouvé', 'code': 'USER_NOT_FOUND'}
            }), 404
        
        if not hasattr(current_user, 'subscription') or not current_user.subscription:
            return jsonify({
                'success': False,
                'error': {'message': 'Aucun abonnement à annuler', 'code': 'NO_SUBSCRIPTION'}
            }), 400
        
        # Annuler l'abonnement
        current_user.subscription.cancel_subscription()
        
        # Mettre à jour la session
        if 'user' in session:
            session['user']['subscription_type'] = 'free'
            session['user']['is_premium'] = False
        
        return jsonify({
            'success': True,
            'message': 'Abonnement annulé avec succès',
            'subscription': current_user.subscription.to_dict()
        })
        
    except Exception as e:
        print(f"Error in cancel_subscription: {str(e)}")
        return jsonify({
            'success': False,
            'error': {'message': 'Erreur lors de l\'annulation', 'code': 'CANCEL_ERROR'}
        }), 500

# Enregistrer le blueprint
def register_subscription_routes(app):
    """Enregistrer les routes d'abonnement."""
    app.register_blueprint(subscription_bp, url_prefix='/api/subscription')