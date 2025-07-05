import re
import hashlib
import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from flask import request, current_app
import json
import uuid
import unicodedata

def generate_session_id() -> str:
    """Générer un ID de session unique"""
    return str(uuid.uuid4())

def generate_secure_token(length: int = 32) -> str:
    """Générer un token sécurisé"""
    return secrets.token_urlsafe(length)

def generate_api_key(prefix: str = "sr") -> str:
    """Générer une clé API"""
    random_part = secrets.token_hex(16)
    return f"{prefix}_{random_part}"

def hash_string(text: str, salt: str = None) -> str:
    """Hasher une chaîne de caractères"""
    if salt is None:
        salt = secrets.token_hex(16)
    
    combined = f"{text}{salt}"
    hashed = hashlib.sha256(combined.encode()).hexdigest()
    return f"{salt}${hashed}"

def verify_hash(text: str, hashed: str) -> bool:
    """Vérifier un hash"""
    try:
        salt, expected_hash = hashed.split('$', 1)
        actual_hash = hashlib.sha256(f"{text}{salt}".encode()).hexdigest()
        return actual_hash == expected_hash
    except ValueError:
        return False

def sanitize_filename(filename: str) -> str:
    """Nettoyer un nom de fichier"""
    # Supprimer les caractères dangereux
    filename = re.sub(r'[^\w\s.-]', '', filename)
    # Supprimer les espaces multiples
    filename = re.sub(r'\s+', '_', filename)
    # Limiter la longueur
    if len(filename) > 100:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = f"{name[:95]}.{ext}" if ext else filename[:100]
    
    return filename

def slugify(text: str, max_length: int = 50) -> str:
    """Convertir du texte en slug URL-friendly"""
    # Normaliser les caractères Unicode
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    # Convertir en minuscules et remplacer les espaces
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '-', text)
    
    # Supprimer les tirets en début/fin
    text = text.strip('-')
    
    # Limiter la longueur
    if len(text) > max_length:
        text = text[:max_length].rstrip('-')
    
    return text

def format_file_size(size_bytes: int) -> str:
    """Formater la taille d'un fichier en format lisible"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def format_duration(seconds: int, short: bool = False) -> str:
    """Formater une durée en format lisible"""
    if seconds < 0:
        return "0s" if short else "0 seconde"
    
    units = [
        (86400, 'j' if short else 'jour'),
        (3600, 'h' if short else 'heure'),
        (60, 'm' if short else 'minute'),
        (1, 's' if short else 'seconde')
    ]
    
    result = []
    for value, unit in units:
        if seconds >= value:
            count = seconds // value
            seconds %= value
            
            if short:
                result.append(f"{count}{unit}")
            else:
                plural = 's' if count > 1 and unit != 'heure' else ''
                if unit == 'heure' and count > 1:
                    plural = 's'
                result.append(f"{count} {unit}{plural}")
        
        if len(result) >= 2:  # Limiter à 2 unités
            break
    
    if not result:
        return "0s" if short else "0 seconde"
    
    return ' '.join(result) if short else ' et '.join(result)

def format_distance(meters: float, metric: bool = True) -> str:
    """Formater une distance en format lisible"""
    if metric:
        if meters < 1000:
            return f"{int(meters)} m"
        else:
            km = meters / 1000
            if km < 10:
                return f"{km:.1f} km"
            else:
                return f"{int(km)} km"
    else:
        # Système impérial
        feet = meters * 3.28084
        if feet < 5280:
            return f"{int(feet)} ft"
        else:
            miles = feet / 5280
            if miles < 10:
                return f"{miles:.1f} mi"
            else:
                return f"{int(miles)} mi"

def format_speed(kmh: float, metric: bool = True) -> str:
    """Formater une vitesse"""
    if metric:
        return f"{int(kmh)} km/h"
    else:
        mph = kmh * 0.621371
        return f"{int(mph)} mph"

def parse_coordinates(coord_string: str) -> Optional[Dict[str, float]]:
    """Parser une chaîne de coordonnées"""
    try:
        # Formats supportés: "lat,lng" ou "lat lng" ou "lat;lng"
        coord_string = coord_string.strip()
        
        # Essayer différents séparateurs
        for sep in [',', ';', ' ']:
            if sep in coord_string:
                parts = coord_string.split(sep)
                if len(parts) == 2:
                    lat = float(parts[0].strip())
                    lng = float(parts[1].strip())
                    
                    # Vérifier les limites
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        return {'lat': lat, 'lng': lng}
        
        return None
    except (ValueError, AttributeError):
        return None

def validate_email(email: str) -> bool:
    """Valider une adresse email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str, country_code: str = "FR") -> bool:
    """Valider un numéro de téléphone (basique)"""
    # Supprimer tous les caractères non numériques
    digits = re.sub(r'\D', '', phone)
    
    # Règles basiques selon le pays
    if country_code == "FR":
        return len(digits) == 10 and digits.startswith(('01', '02', '03', '04', '05', '06', '07', '08', '09'))
    elif country_code == "US":
        return len(digits) == 10 or (len(digits) == 11 and digits.startswith('1'))
    else:
        # Validation générique
        return 7 <= len(digits) <= 15

def clean_phone_number(phone: str) -> str:
    """Nettoyer un numéro de téléphone"""
    return re.sub(r'[^\d+]', '', phone)

def mask_sensitive_data(data: str, visible_chars: int = 4, mask_char: str = '*') -> str:
    """Masquer des données sensibles"""
    if len(data) <= visible_chars:
        return mask_char * len(data)
    
    return data[:visible_chars] + mask_char * (len(data) - visible_chars)

def mask_email(email: str) -> str:
    """Masquer une adresse email"""
    try:
        local, domain = email.split('@')
        if len(local) <= 2:
            masked_local = '*' * len(local)
        else:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
        
        domain_parts = domain.split('.')
        if len(domain_parts[0]) <= 2:
            masked_domain = '*' * len(domain_parts[0])
        else:
            masked_domain = domain_parts[0][0] + '*' * (len(domain_parts[0]) - 2) + domain_parts[0][-1]
        
        return f"{masked_local}@{masked_domain}.{'.'.join(domain_parts[1:])}"
    except ValueError:
        return mask_sensitive_data(email)

def get_client_ip() -> str:
    """Récupérer l'IP réelle du client"""
    # Vérifier les headers de proxy
    forwarded_for = request.environ.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    
    real_ip = request.environ.get('HTTP_X_REAL_IP')
    if real_ip:
        return real_ip
    
    return request.remote_addr

def get_user_agent_info() -> Dict[str, str]:
    """Analyser les informations du user agent"""
    user_agent = request.user_agent
    
    return {
        'string': user_agent.string,
        'platform': user_agent.platform or 'unknown',
        'browser': user_agent.browser or 'unknown',
        'version': user_agent.version or 'unknown',
        'language': user_agent.language or 'unknown'
    }

def paginate_query(query, page: int, per_page: int, max_per_page: int = 100):
    """Paginer une requête SQLAlchemy"""
    # Limiter le nombre d'éléments par page
    per_page = min(per_page, max_per_page)
    
    # S'assurer que la page est positive
    page = max(1, page)
    
    return query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

def safe_json_loads(json_string: str, default: Any = None) -> Any:
    """Parser du JSON de manière sécurisée"""
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return default

def safe_int(value: Any, default: int = 0) -> int:
    """Convertir en entier de manière sécurisée"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value: Any, default: float = 0.0) -> float:
    """Convertir en float de manière sécurisée"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def chunks(lst: List, chunk_size: int) -> List[List]:
    """Diviser une liste en chunks"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """Aplatir un dictionnaire imbriqué"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def deep_merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Fusionner profondément deux dictionnaires"""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculer la distance entre deux points (formule haversine)"""
    import math
    
    # Convertir en radians
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    
    # Formule haversine
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Rayon de la Terre en kilomètres
    r = 6371
    
    return c * r

def calculate_bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculer le cap entre deux points"""
    import math
    
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    
    dlng = lng2 - lng1
    
    y = math.sin(dlng) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlng)
    
    bearing = math.atan2(y, x)
    
    # Convertir en degrés et normaliser (0-360)
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360
    
    return bearing

def is_point_in_bbox(lat: float, lng: float, bbox: Dict[str, float]) -> bool:
    """Vérifier si un point est dans une bounding box"""
    return (bbox['south'] <= lat <= bbox['north'] and 
            bbox['west'] <= lng <= bbox['east'])

def generate_bbox(lat: float, lng: float, radius_km: float) -> Dict[str, float]:
    """Générer une bounding box autour d'un point"""
    # Approximation rapide (1 degré ≈ 111 km)
    lat_delta = radius_km / 111.0
    lng_delta = radius_km / (111.0 * abs(math.cos(math.radians(lat))))
    
    return {
        'north': lat + lat_delta,
        'south': lat - lat_delta,
        'east': lng + lng_delta,
        'west': lng - lng_delta
    }

def debounce_key(func_name: str, args: tuple, delay_seconds: int = 1) -> str:
    """Générer une clé pour le debouncing"""
    args_str = str(args)
    key_data = f"{func_name}:{args_str}:{delay_seconds}"
    return hashlib.md5(key_data.encode()).hexdigest()

def get_time_ago(dt: datetime) -> str:
    """Formater une date en 'il y a X temps'"""
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 0:
        if diff.days == 1:
            return "il y a 1 jour"
        elif diff.days < 7:
            return f"il y a {diff.days} jours"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"il y a {weeks} semaine{'s' if weeks > 1 else ''}"
        elif diff.days < 365:
            months = diff.days // 30
            return f"il y a {months} mois"
        else:
            years = diff.days // 365
            return f"il y a {years} an{'s' if years > 1 else ''}"
    
    seconds = diff.seconds
    if seconds < 60:
        return "il y a moins d'une minute"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"il y a {minutes} minute{'s' if minutes > 1 else ''}"
    else:
        hours = seconds // 3600
        return f"il y a {hours} heure{'s' if hours > 1 else ''}"

def is_weekend(dt: datetime = None) -> bool:
    """Vérifier si c'est le week-end"""
    if dt is None:
        dt = datetime.now()
    return dt.weekday() >= 5  # 5 = samedi, 6 = dimanche

def is_business_hours(dt: datetime = None, start_hour: int = 9, end_hour: int = 17) -> bool:
    """Vérifier si c'est les heures ouvrables"""
    if dt is None:
        dt = datetime.now()
    
    return (not is_weekend(dt) and start_hour <= dt.hour < end_hour)

def next_business_day(dt: datetime = None) -> datetime:
    """Trouver le prochain jour ouvrable"""
    if dt is None:
        dt = datetime.now()
    
    while is_weekend(dt):
        dt += timedelta(days=1)
    
    return dt

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Tronquer un texte"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def extract_numbers(text: str) -> List[float]:
    """Extraire tous les nombres d'un texte"""
    pattern = r'-?\d+\.?\d*'
    matches = re.findall(pattern, text)
    return [float(match) for match in matches]

def normalize_whitespace(text: str) -> str:
    """Normaliser les espaces dans un texte"""
    return re.sub(r'\s+', ' ', text.strip())

import math