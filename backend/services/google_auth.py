import json
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow
from flask import current_app, session, url_for
import secrets
import logging
from typing import Dict, List, Optional

class GoogleAuthService:
    """Service pour l'authentification Google OAuth 2.0"""
    
    def __init__(self):
        self.client_id = current_app.config['GOOGLE_CLIENT_ID']
        self.client_secret = current_app.config['GOOGLE_CLIENT_SECRET']
        self.redirect_uri = self._get_redirect_uri()
        self.scopes = [
            'openid',
            'email',
            'profile'
        ]
        
        self.logger = logging.getLogger(__name__)
        
        # Configuration OAuth Flow
        self.flow_config = {
            'web': {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
                'redirect_uris': [self.redirect_uri]
            }
        }
    
    def _get_redirect_uri(self) -> str:
        """Construire l'URI de redirection"""
        base_url = current_app.config.get('APP_URL', 'http://localhost:5000')
        #return f"{base_url}/auth/callback"
        return f"{current_app.config['APP_URL'].rstrip('/')}/auth/callback"
    
    def get_authorization_url(self) -> str:
        """Générer l'URL d'autorisation Google"""
        
        try:
            # Créer le flow OAuth
            flow = Flow.from_client_config(
                self.flow_config,
                scopes=self.scopes,
                redirect_uri=self.redirect_uri
            )
            
            # Générer un state pour sécuriser la requête
            state = secrets.token_urlsafe(32)
            session['oauth_state'] = state
            
            # Générer l'URL d'autorisation
            authorization_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state,
                prompt='select_account'  # Forcer la sélection de compte
            )
            
            return authorization_url
            
        except Exception as e:
            self.logger.error(f"Erreur génération URL autorisation: {str(e)}")
            raise Exception("Impossible de générer l'URL d'autorisation Google")
    
    def get_user_info(self, authorization_code: str) -> Optional[Dict]:
        """Échanger le code d'autorisation contre les informations utilisateur"""
        
        try:
            # Vérifier le state pour sécurité
            received_state = session.get('oauth_state')
            if not received_state:
                self.logger.warning("State OAuth manquant")
                return None
            
            # Créer le flow OAuth
            flow = Flow.from_client_config(
                self.flow_config,
                scopes=self.scopes,
                redirect_uri=self.redirect_uri,
                state=received_state
            )
            
            # Échanger le code contre les tokens
            flow.fetch_token(code=authorization_code)
            
            # Récupérer les informations utilisateur
            credentials = flow.credentials
            user_info = self._get_user_profile(credentials.token)
            
            # Nettoyer le state de la session
            session.pop('oauth_state', None)
            
            return user_info
            
        except Exception as e:
            self.logger.error(f"Erreur récupération infos utilisateur: {str(e)}")
            return None
    
    def verify_token(self, id_token_str: str) -> Optional[Dict]:
        """Vérifier un ID token Google et extraire les informations utilisateur"""
        
        try:
            # Vérifier et décoder le token
            idinfo = id_token.verify_oauth2_token(
                id_token_str, 
                google_requests.Request(), 
                self.client_id
            )
            
            # Vérifier l'issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                self.logger.warning(f"Token issuer invalide: {idinfo['iss']}")
                return None
            
            return idinfo
            
        except ValueError as e:
            self.logger.error(f"Token Google invalide: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Erreur vérification token: {str(e)}")
            return None
    
    def _get_user_profile(self, access_token: str) -> Optional[Dict]:
        """Récupérer le profil utilisateur avec l'access token"""
        
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers=headers,
                timeout=10
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            self.logger.error(f"Erreur récupération profil Google: {str(e)}")
            return None
    
    def revoke_token(self, access_token: str) -> bool:
        """Révoquer un token Google"""
        
        try:
            response = requests.post(
                'https://oauth2.googleapis.com/revoke',
                params={'token': access_token},
                headers={'content-type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Erreur révocation token: {str(e)}")
            return False
    
    def validate_client_config(self) -> Dict:
        """Valider la configuration du client Google"""
        
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Vérifier la présence des paramètres requis
        if not self.client_id:
            validation_result['valid'] = False
            validation_result['errors'].append('GOOGLE_CLIENT_ID manquant')
        
        if not self.client_secret:
            validation_result['valid'] = False
            validation_result['errors'].append('GOOGLE_CLIENT_SECRET manquant')
        
        # Vérifier le format du client_id
        if self.client_id and not self.client_id.endswith('.apps.googleusercontent.com'):
            validation_result['warnings'].append('Format client_id Google inhabituel')
        
        # Vérifier l'URI de redirection
        if not self.redirect_uri.startswith('https://') and not current_app.debug:
            validation_result['warnings'].append('URI de redirection devrait utiliser HTTPS en production')
        
        return validation_result
    
    def get_login_hint_url(self, email_hint: str = None) -> str:
        """Générer une URL de connexion avec suggestion d'email"""
        
        base_url = self.get_authorization_url()
        
        if email_hint:
            return f"{base_url}&login_hint={email_hint}"
        
        return base_url
    
    def create_client_config_js(self) -> str:
        """Créer la configuration JavaScript pour Google Sign-In"""
        
        config = {
            'client_id': self.client_id,
            'auto_select': False,
            'callback': 'handleCredentialResponse',
            'use_fedcm_for_prompt': True
        }
        
        return f"window.googleClientConfig = {json.dumps(config)};"
    
    def handle_sign_out(self, user_session: Dict) -> Dict:
        """Gérer la déconnexion d'un utilisateur Google"""
        
        result = {
            'success': True,
            'message': 'Déconnexion réussie',
            'actions_performed': []
        }
        
        try:
            # Si l'utilisateur a un access token, essayer de le révoquer
            if 'google_access_token' in user_session:
                revoke_success = self.revoke_token(user_session['google_access_token'])
                if revoke_success:
                    result['actions_performed'].append('token_revoked')
                else:
                    result['actions_performed'].append('token_revocation_failed')
            
            # Nettoyer les données Google de la session
            google_keys = ['google_id', 'google_access_token', 'google_refresh_token']
            for key in google_keys:
                if key in user_session:
                    del user_session[key]
                    result['actions_performed'].append(f'{key}_cleared')
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la déconnexion Google: {str(e)}")
            result['success'] = False
            result['message'] = 'Erreur lors de la déconnexion'
        
        return result
    
    def refresh_user_token(self, refresh_token: str) -> Optional[Dict]:
        """Rafraîchir l'access token d'un utilisateur"""
        
        try:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(
                'https://oauth2.googleapis.com/token',
                data=data,
                timeout=10
            )
            
            response.raise_for_status()
            token_data = response.json()
            
            return {
                'access_token': token_data.get('access_token'),
                'expires_in': token_data.get('expires_in'),
                'token_type': token_data.get('token_type', 'Bearer')
            }
            
        except Exception as e:
            self.logger.error(f"Erreur rafraîchissement token: {str(e)}")
            return None
    
    def get_user_permissions(self, access_token: str) -> List[str]:
        """Récupérer les permissions accordées par l'utilisateur"""
        
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                f'https://oauth2.googleapis.com/tokeninfo?access_token={access_token}',
                headers=headers,
                timeout=10
            )
            
            response.raise_for_status()
            token_info = response.json()
            
            scopes = token_info.get('scope', '').split(' ')
            return [scope.strip() for scope in scopes if scope.strip()]
            
        except Exception as e:
            self.logger.error(f"Erreur récupération permissions: {str(e)}")
            return []
    
    def check_service_availability(self) -> Dict:
        """Vérifier la disponibilité des services Google"""
        
        try:
            # Test de connectivité avec Google
            response = requests.get(
                'https://accounts.google.com/.well-known/openid_configuration',
                timeout=5
            )
            
            if response.status_code == 200:
                return {
                    'available': True,
                    'status': 'operational',
                    'response_time_ms': response.elapsed.total_seconds() * 1000
                }
            else:
                return {
                    'available': False,
                    'status': 'degraded',
                    'error': f'HTTP {response.status_code}'
                }
                
        except requests.RequestException as e:
            return {
                'available': False,
                'status': 'down',
                'error': str(e)
            }
        except Exception as e:
            return {
                'available': False,
                'status': 'unknown',
                'error': str(e)
            }