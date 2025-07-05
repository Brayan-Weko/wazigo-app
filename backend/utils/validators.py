import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
from flask import current_app
import ipaddress

class ValidationError(Exception):
    """Exception pour les erreurs de validation"""
    def __init__(self, message: str, field: str = None, code: str = None):
        self.message = message
        self.field = field
        self.code = code or 'VALIDATION_ERROR'
        super().__init__(self.message)

class Validator:
    """Classe de base pour les validateurs"""
    
    def __init__(self, required: bool = True, allow_none: bool = False):
        self.required = required
        self.allow_none = allow_none
    
    def validate(self, value: Any, field_name: str = None) -> Any:
        """Valider une valeur"""
        if value is None:
            if self.required and not self.allow_none:
                raise ValidationError(f"Le champ est requis", field_name, 'REQUIRED')
            elif self.allow_none:
                return None
        
        return self._validate_value(value, field_name)
    
    def _validate_value(self, value: Any, field_name: str = None) -> Any:
        """Méthode à implémenter dans les sous-classes"""
        return value

class StringValidator(Validator):
    """Validateur pour les chaînes de caractères"""
    
    def __init__(self, min_length: int = None, max_length: int = None, 
                 pattern: str = None, choices: List[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if pattern else None
        self.choices = choices
    
    def _validate_value(self, value: Any, field_name: str = None) -> str:
        if not isinstance(value, str):
            raise ValidationError("Doit être une chaîne de caractères", field_name, 'INVALID_TYPE')
        
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(f"Doit contenir au moins {self.min_length} caractères", 
                                field_name, 'TOO_SHORT')
        
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(f"Ne peut pas dépasser {self.max_length} caractères", 
                                field_name, 'TOO_LONG')
        
        if self.pattern and not self.pattern.match(value):
            raise ValidationError("Format invalide", field_name, 'INVALID_FORMAT')
        
        if self.choices and value not in self.choices:
            raise ValidationError(f"Doit être l'une des valeurs: {', '.join(self.choices)}", 
                                field_name, 'INVALID_CHOICE')
        
        return value.strip()

class EmailValidator(StringValidator):
    """Validateur pour les adresses email"""
    
    def __init__(self, **kwargs):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        super().__init__(pattern=pattern, max_length=254, **kwargs)
    
    def _validate_value(self, value: Any, field_name: str = None) -> str:
        email = super()._validate_value(value, field_name)
        
        # Vérifications supplémentaires
        if email.count('@') != 1:
            raise ValidationError("Adresse email invalide", field_name, 'INVALID_EMAIL')
        
        local, domain = email.split('@')
        
        if len(local) > 64:
            raise ValidationError("Partie locale de l'email trop longue", field_name, 'INVALID_EMAIL')
        
        if len(domain) > 253:
            raise ValidationError("Domaine de l'email trop long", field_name, 'INVALID_EMAIL')
        
        return email.lower()

class NumberValidator(Validator):
    """Validateur pour les nombres"""
    
    def __init__(self, min_value: float = None, max_value: float = None, 
                 integer_only: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value
        self.integer_only = integer_only
    
    def _validate_value(self, value: Any, field_name: str = None) -> float:
        try:
            if self.integer_only:
                num_value = int(value)
            else:
                num_value = float(value)
        except (ValueError, TypeError):
            raise ValidationError("Doit être un nombre valide", field_name, 'INVALID_NUMBER')
        
        if self.min_value is not None and num_value < self.min_value:
            raise ValidationError(f"Doit être supérieur ou égal à {self.min_value}", 
                                field_name, 'TOO_SMALL')
        
        if self.max_value is not None and num_value > self.max_value:
            raise ValidationError(f"Doit être inférieur ou égal à {self.max_value}", 
                                field_name, 'TOO_LARGE')
        
        return num_value

class BooleanValidator(Validator):
    """Validateur pour les booléens"""
    
    def _validate_value(self, value: Any, field_name: str = None) -> bool:
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            if value.lower() in ('true', '1', 'yes', 'on'):
                return True
            elif value.lower() in ('false', '0', 'no', 'off'):
                return False
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        raise ValidationError("Doit être un booléen valide", field_name, 'INVALID_BOOLEAN')

class DateValidator(Validator):
    """Validateur pour les dates"""
    
    def __init__(self, min_date: date = None, max_date: date = None, 
                 format_string: str = "%Y-%m-%d", **kwargs):
        super().__init__(**kwargs)
        self.min_date = min_date
        self.max_date = max_date
        self.format_string = format_string
    
    def _validate_value(self, value: Any, field_name: str = None) -> date:
        if isinstance(value, date):
            date_value = value
        elif isinstance(value, datetime):
            date_value = value.date()
        elif isinstance(value, str):
            try:
                date_value = datetime.strptime(value, self.format_string).date()
            except ValueError:
                raise ValidationError(f"Format de date invalide. Attendu: {self.format_string}", 
                                    field_name, 'INVALID_DATE_FORMAT')
        else:
            raise ValidationError("Type de date invalide", field_name, 'INVALID_DATE_TYPE')
        
        if self.min_date and date_value < self.min_date:
            raise ValidationError(f"Date trop ancienne. Minimum: {self.min_date}", 
                                field_name, 'DATE_TOO_OLD')
        
        if self.max_date and date_value > self.max_date:
            raise ValidationError(f"Date trop récente. Maximum: {self.max_date}", 
                                field_name, 'DATE_TOO_RECENT')
        
        return date_value

class CoordinatesValidator(Validator):
    """Validateur pour les coordonnées géographiques"""
    
    def _validate_value(self, value: Any, field_name: str = None) -> Dict[str, float]:
        if isinstance(value, dict):
            if 'lat' not in value or 'lng' not in value:
                raise ValidationError("Les coordonnées doivent contenir 'lat' et 'lng'", 
                                    field_name, 'MISSING_COORDINATES')
            
            try:
                lat = float(value['lat'])
                lng = float(value['lng'])
            except (ValueError, TypeError):
                raise ValidationError("Coordonnées invalides", field_name, 'INVALID_COORDINATES')
        
        elif isinstance(value, str):
            # Parser "lat,lng"
            try:
                parts = value.split(',')
                if len(parts) != 2:
                    raise ValueError()
                lat, lng = float(parts[0].strip()), float(parts[1].strip())
            except ValueError:
                raise ValidationError("Format de coordonnées invalide. Attendu: 'lat,lng'", 
                                    field_name, 'INVALID_COORDINATES_FORMAT')
        
        else:
            raise ValidationError("Type de coordonnées invalide", field_name, 'INVALID_COORDINATES_TYPE')
        
        # Vérifier les limites
        if not (-90 <= lat <= 90):
            raise ValidationError("Latitude doit être entre -90 et 90", field_name, 'INVALID_LATITUDE')
        
        if not (-180 <= lng <= 180):
            raise ValidationError("Longitude doit être entre -180 et 180", field_name, 'INVALID_LONGITUDE')
        
        return {'lat': lat, 'lng': lng}

class ListValidator(Validator):
    """Validateur pour les listes"""
    
    def __init__(self, item_validator: Validator = None, min_items: int = None, 
                 max_items: int = None, unique: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.item_validator = item_validator
        self.min_items = min_items
        self.max_items = max_items
        self.unique = unique
    
    def _validate_value(self, value: Any, field_name: str = None) -> List:
        if not isinstance(value, (list, tuple)):
            raise ValidationError("Doit être une liste", field_name, 'INVALID_LIST')
        
        items = list(value)
        
        if self.min_items is not None and len(items) < self.min_items:
            raise ValidationError(f"Doit contenir au moins {self.min_items} éléments", 
                                field_name, 'TOO_FEW_ITEMS')
        
        if self.max_items is not None and len(items) > self.max_items:
            raise ValidationError(f"Ne peut pas contenir plus de {self.max_items} éléments", 
                                field_name, 'TOO_MANY_ITEMS')
        
        if self.unique and len(items) != len(set(items)):
            raise ValidationError("Les éléments doivent être uniques", field_name, 'DUPLICATE_ITEMS')
        
        # Valider chaque élément
        if self.item_validator:
            validated_items = []
            for i, item in enumerate(items):
                try:
                    validated_item = self.item_validator.validate(item, f"{field_name}[{i}]")
                    validated_items.append(validated_item)
                except ValidationError as e:
                    raise ValidationError(f"Élément {i}: {e.message}", field_name, e.code)
            return validated_items
        
        return items

class DictValidator(Validator):
    """Validateur pour les dictionnaires/objets"""
    
    def __init__(self, schema: Dict[str, Validator] = None, strict: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.schema = schema or {}
        self.strict = strict  # Si True, rejette les clés non définies dans le schéma
    
    def _validate_value(self, value: Any, field_name: str = None) -> Dict:
        if not isinstance(value, dict):
            raise ValidationError("Doit être un objet", field_name, 'INVALID_OBJECT')
        
        validated_data = {}
        
        # Valider selon le schéma
        for key, validator in self.schema.items():
            try:
                validated_value = validator.validate(value.get(key), f"{field_name}.{key}" if field_name else key)
                if validated_value is not None:
                    validated_data[key] = validated_value
            except ValidationError:
                raise
        
        # Vérifier les clés supplémentaires
        if self.strict:
            extra_keys = set(value.keys()) - set(self.schema.keys())
            if extra_keys:
                raise ValidationError(f"Clés non autorisées: {', '.join(extra_keys)}", 
                                    field_name, 'EXTRA_KEYS')
        else:
            # Ajouter les clés non validées
            for key, val in value.items():
                if key not in self.schema:
                    validated_data[key] = val
        
        return validated_data

class URLValidator(StringValidator):
    """Validateur pour les URLs"""
    
    def __init__(self, schemes: List[str] = None, **kwargs):
        self.schemes = schemes or ['http', 'https']
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        super().__init__(pattern=pattern, **kwargs)
    
    def _validate_value(self, value: Any, field_name: str = None) -> str:
        url = super()._validate_value(value, field_name)
        
        # Vérifier le schéma
        scheme = url.split('://')[0].lower()
        if scheme not in self.schemes:
            raise ValidationError(f"Schéma non autorisé. Autorisés: {', '.join(self.schemes)}", 
                                field_name, 'INVALID_URL_SCHEME')
        
        return url

class IPAddressValidator(StringValidator):
    """Validateur pour les adresses IP"""
    
    def __init__(self, version: int = None, **kwargs):
        self.version = version  # 4, 6, ou None pour les deux
        super().__init__(**kwargs)
    
    def _validate_value(self, value: Any, field_name: str = None) -> str:
        ip_str = super()._validate_value(value, field_name)
        
        try:
            ip = ipaddress.ip_address(ip_str)
            
            if self.version == 4 and not isinstance(ip, ipaddress.IPv4Address):
                raise ValidationError("Doit être une adresse IPv4", field_name, 'INVALID_IPV4')
            
            if self.version == 6 and not isinstance(ip, ipaddress.IPv6Address):
                raise ValidationError("Doit être une adresse IPv6", field_name, 'INVALID_IPV6')
            
            return str(ip)
            
        except ipaddress.AddressValueError:
            raise ValidationError("Adresse IP invalide", field_name, 'INVALID_IP')

class FormValidator:
    """Validateur de formulaire complet"""
    
    def __init__(self, schema: Dict[str, Validator]):
        self.schema = schema
    
    def validate(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Valider des données selon le schéma
        
        Returns:
            Tuple: (données validées, erreurs)
        """
        validated_data = {}
        errors = {}
        
        for field_name, validator in self.schema.items():
            try:
                validated_value = validator.validate(data.get(field_name), field_name)
                if validated_value is not None:
                    validated_data[field_name] = validated_value
            except ValidationError as e:
                errors[field_name] = e.message
        
        return validated_data, errors
    
    def validate_or_raise(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valider des données et lever une exception en cas d'erreur
        
        Returns:
            Dict: données validées
        
        Raises:
            ValidationError: Si des erreurs de validation
        """
        validated_data, errors = self.validate(data)
        
        if errors:
            error_messages = [f"{field}: {message}" for field, message in errors.items()]
            raise ValidationError(
                f"Erreurs de validation: {'; '.join(error_messages)}",
                code='VALIDATION_ERRORS'
            )
        
        return validated_data

# Schémas de validation prédéfinis

ROUTE_SEARCH_SCHEMA = {
    'origin': CoordinatesValidator(),
    'destination': CoordinatesValidator(),
    'departure_time': DateValidator(required=False, allow_none=True),
    'avoid_tolls': BooleanValidator(required=False),
    'avoid_highways': BooleanValidator(required=False),
    'avoid_ferries': BooleanValidator(required=False),
    'route_type': StringValidator(choices=['fastest', 'shortest', 'balanced'], required=False),
    'alternatives': NumberValidator(min_value=1, max_value=5, integer_only=True, required=False)
}

USER_REGISTRATION_SCHEMA = {
    'email': EmailValidator(),
    'name': StringValidator(min_length=2, max_length=100),
    'google_id': StringValidator(required=False, allow_none=True),
    'avatar_url': URLValidator(required=False, allow_none=True)
}

SAVED_ROUTE_SCHEMA = {
    'name': StringValidator(min_length=1, max_length=100),
    'description': StringValidator(max_length=500, required=False, allow_none=True),
    'origin_address': StringValidator(min_length=1, max_length=255),
    'origin_lat': NumberValidator(min_value=-90, max_value=90),
    'origin_lng': NumberValidator(min_value=-180, max_value=180),
    'destination_address': StringValidator(min_length=1, max_length=255),
    'destination_lat': NumberValidator(min_value=-90, max_value=90),
    'destination_lng': NumberValidator(min_value=-180, max_value=180),
    'tags': ListValidator(
        item_validator=StringValidator(min_length=1, max_length=50),
        max_items=10,
        required=False,
        allow_none=True
    )
}

FEEDBACK_SCHEMA = {
    'rating': NumberValidator(min_value=1, max_value=5, integer_only=True),
    'feedback_type': StringValidator(choices=['route_quality', 'app_performance', 'feature_request', 'bug_report']),
    'comment': StringValidator(max_length=1000, required=False, allow_none=True),
    'route_id': NumberValidator(min_value=1, integer_only=True, required=False, allow_none=True)
}

USER_PREFERENCES_SCHEMA = {
    'route_preferences': DictValidator({
        'avoid_tolls': BooleanValidator(required=False),
        'avoid_highways': BooleanValidator(required=False),
        'avoid_ferries': BooleanValidator(required=False),
        'prefer_fastest': BooleanValidator(required=False)
    }, required=False),
    'notifications': DictValidator({
        'traffic_alerts': BooleanValidator(required=False),
        'route_suggestions': BooleanValidator(required=False),
        'email_updates': BooleanValidator(required=False)
    }, required=False),
    'display': DictValidator({
        'units': StringValidator(choices=['metric', 'imperial'], required=False),
        'language': StringValidator(choices=['fr', 'en'], required=False),
        'theme': StringValidator(choices=['light', 'dark', 'auto'], required=False)
    }, required=False)
}

def validate_route_search(data: Dict[str, Any]) -> Dict[str, Any]:
    """Valider les données de recherche d'itinéraire"""
    validator = FormValidator(ROUTE_SEARCH_SCHEMA)
    return validator.validate_or_raise(data)

def validate_user_registration(data: Dict[str, Any]) -> Dict[str, Any]:
    """Valider les données d'inscription utilisateur"""
    validator = FormValidator(USER_REGISTRATION_SCHEMA)
    return validator.validate_or_raise(data)

def validate_saved_route(data: Dict[str, Any]) -> Dict[str, Any]:
    """Valider les données de sauvegarde d'itinéraire"""
    validator = FormValidator(SAVED_ROUTE_SCHEMA)
    return validator.validate_or_raise(data)

def validate_feedback(data: Dict[str, Any]) -> Dict[str, Any]:
    """Valider les données de feedback"""
    validator = FormValidator(FEEDBACK_SCHEMA)
    return validator.validate_or_raise(data)

def validate_user_preferences(data: Dict[str, Any]) -> Dict[str, Any]:
    """Valider les préférences utilisateur"""
    validator = FormValidator(USER_PREFERENCES_SCHEMA)
    return validator.validate_or_raise(data)