from flask import Blueprint, request, redirect, url_for, session, flash, jsonify, current_app
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from backend.models import User, db
from backend.services.google_auth import GoogleAuthService
from datetime import datetime
import json

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    """Rediriger vers la page de connexion Google"""
    
    # Si l'utilisateur est déjà connecté, rediriger
    if 'user' in session:
        return redirect(url_for('main.index'))
    
    # Générer l'URL d'autorisation Google
    google_auth = GoogleAuthService()
    authorization_url = google_auth.get_authorization_url()
    
    return redirect(authorization_url)

@auth_bp.route('/callback')
def callback():
    """Callback après authentification Google"""
    
    try:
        # Récupérer le code d'autorisation
        authorization_code = request.args.get('code')
        if not authorization_code:
            flash('Erreur lors de la connexion avec Google.', 'error')
            return redirect(url_for('main.index'))
        
        # Échanger le code contre un token
        google_auth = GoogleAuthService()
        user_info = google_auth.get_user_info(authorization_code)
        
        if not user_info:
            flash('Impossible de récupérer les informations utilisateur.', 'error')
            return redirect(url_for('main.index'))
        
        # Rechercher ou créer l'utilisateur
        user = User.find_by_google_id(user_info.get('sub'))
        
        if not user:
            # Vérifier si un utilisateur existe avec cet email
            user = User.find_by_email(user_info.get('email'))
            
            if user:
                # Lier le compte Google à l'utilisateur existant
                user.google_id = user_info.get('sub')
                user.avatar_url = user_info.get('picture')
                user.save()
            else:
                # Créer un nouvel utilisateur
                user = User.create_from_google(user_info)
                user.save()
        else:
            # Mettre à jour les informations de l'utilisateur existant
            user.name = user_info.get('name')
            user.avatar_url = user_info.get('picture')
            user.last_login = datetime.utcnow()
            user.save()
        
        # Créer la session utilisateur
        session['user'] = {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'avatar_url': user.avatar_url,
            'google_id': user.google_id
        }
        
        # Mettre à jour la dernière activité
        user.update_last_activity()
        
        flash(f'Bienvenue, {user.name}!', 'success')
        
        # Rediriger vers la page demandée ou l'accueil
        next_page = session.pop('next_page', None)
        return redirect(next_page or url_for('main.index'))
        
    except Exception as e:
        current_app.logger.error(f'Erreur lors de l\'authentification: {str(e)}')
        flash('Erreur lors de la connexion. Veuillez réessayer.', 'error')
        return redirect(url_for('main.index'))

@auth_bp.route('/logout')
def logout():
    """Déconnexion de l'utilisateur"""
    
    user_name = session.get('user', {}).get('name', 'Utilisateur')
    
    # Supprimer les données de session
    session.pop('user', None)
    
    flash(f'Au revoir, {user_name}!', 'info')
    return redirect(url_for('main.index'))

# API Routes pour authentification

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """API endpoint pour la connexion avec Google ID Token"""
    
    try:
        data = request.get_json()
        if not data or 'credential' not in data:
            return jsonify({'error': 'Token Google requis'}), 400
        
        # Vérifier le token Google
        google_auth = GoogleAuthService()
        user_info = google_auth.verify_token(data['credential'])
        
        if not user_info:
            return jsonify({'error': 'Token invalide'}), 401
        
        # Rechercher ou créer l'utilisateur
        user = User.find_by_google_id(user_info.get('sub'))
        
        if not user:
            user = User.find_by_email(user_info.get('email'))
            
            if user:
                user.google_id = user_info.get('sub')
                user.avatar_url = user_info.get('picture')
                user.save()
            else:
                user = User.create_from_google(user_info)
                user.save()
        else:
            user.last_login = datetime.utcnow()
            user.save()
        
        # Créer la session
        session['user'] = {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'avatar_url': user.avatar_url,
            'google_id': user.google_id
        }
        
        user.update_last_activity()
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'message': f'Bienvenue, {user.name}!'
        })
        
    except Exception as e:
        current_app.logger.error(f'Erreur API login: {str(e)}')
        return jsonify({'error': 'Erreur lors de la connexion'}), 500

@auth_bp.route('/api/logout', methods=['POST'])
def api_logout():
    """API endpoint pour la déconnexion"""
    
    user_name = session.get('user', {}).get('name', 'Utilisateur')
    session.pop('user', None)
    
    return jsonify({
        'success': True,
        'message': f'Au revoir, {user_name}!'
    })

@auth_bp.route('/api/user')
def api_current_user():
    """API endpoint pour récupérer l'utilisateur actuel"""
    
    if 'user' not in session:
        return jsonify({'authenticated': False}), 401
    
    user_id = session['user']['id']
    user = User.get_by_id(user_id)
    
    if not user:
        session.pop('user', None)
        return jsonify({'authenticated': False}), 401
    
    return jsonify({
        'authenticated': True,
        'user': user.to_dict()
    })

@auth_bp.route('/api/preferences', methods=['GET', 'POST'])
def api_user_preferences():
    """API endpoint pour gérer les préférences utilisateur"""
    
    if 'user' not in session:
        return jsonify({'error': 'Authentification requise'}), 401
    
    user_id = session['user']['id']
    user = User.get_by_id(user_id)
    
    if not user:
        return jsonify({'error': 'Utilisateur introuvable'}), 404
    
    if request.method == 'GET':
        return jsonify({
            'preferences': user.preferences or User.get_default_preferences()
        })
    
    elif request.method == 'POST':
        try:
            new_preferences = request.get_json()
            if not new_preferences:
                return jsonify({'error': 'Données invalides'}), 400
            
            user.update_preferences(new_preferences)
            
            return jsonify({
                'success': True,
                'preferences': user.preferences,
                'message': 'Préférences mises à jour avec succès'
            })
            
        except Exception as e:
            current_app.logger.error(f'Erreur mise à jour préférences: {str(e)}')
            return jsonify({'error': 'Erreur lors de la mise à jour'}), 500

@auth_bp.route('/api/delete-account', methods=['POST'])
def api_delete_account():
    """API endpoint pour supprimer le compte utilisateur"""
    
    if 'user' not in session:
        return jsonify({'error': 'Authentification requise'}), 401
    
    try:
        user_id = session['user']['id']
        user = User.get_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'Utilisateur introuvable'}), 404
        
        # Confirmation requise
        data = request.get_json()
        if not data or not data.get('confirm'):
            return jsonify({'error': 'Confirmation requise'}), 400
        
        # Supprimer l'utilisateur (cascade vers les autres tables)
        user.delete()
        
        # Supprimer la session
        session.pop('user', None)
        
        return jsonify({
            'success': True,
            'message': 'Compte supprimé avec succès'
        })
        
    except Exception as e:
        current_app.logger.error(f'Erreur suppression compte: {str(e)}')
        return jsonify({'error': 'Erreur lors de la suppression'}), 500

# Route de test (à supprimer en production)
@auth_bp.route('/test-login')
def test_login():
    """Route de test pour l'authentification (développement uniquement)"""
    
    if not current_app.debug:
        return "Non autorisé", 403
    
    # Créer un utilisateur de test
    test_user = {
        'id': 999,
        'email': 'test@smartroute.dev',
        'name': 'Utilisateur Test',
        'avatar_url': 'https://via.placeholder.com/150',
        'google_id': 'test_google_id'
    }
    
    session['user'] = test_user
    flash('Connexion de test réussie!', 'success')
    
    return redirect(url_for('main.index'))