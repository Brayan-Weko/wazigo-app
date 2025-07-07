# utils/date_helpers.py
from datetime import datetime
import re

def validate_here_datetime(dt_string):
    """Valider et formater une date/heure pour HERE Maps API"""
    
    if not dt_string or not str(dt_string).strip():
        return None
    
    try:
        dt_str = str(dt_string).strip()
        
        # Supprimer les microsecondes si présentes
        if '.' in dt_str:
            dt_str = dt_str.split('.')[0]
        
        # Supprimer la timezone si présente
        if dt_str.endswith('Z'):
            dt_str = dt_str[:-1]
        elif '+' in dt_str:
            dt_str = dt_str.split('+')[0]
        
        # Vérifier le format attendu par HERE: YYYY-MM-DDTHH:MM:SS
        pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$'
        
        if re.match(pattern, dt_str):
            # Valider que c'est une vraie date
            datetime.fromisoformat(dt_str)
            return dt_str
        else:
            # Essayer de parser et reformater
            dt = datetime.fromisoformat(dt_str)
            return dt.strftime('%Y-%m-%dT%H:%M:%S')
            
    except (ValueError, TypeError, AttributeError) as e:
        print(f"Error validating datetime '{dt_string}': {e}")
        return None

def get_here_current_time():
    """Obtenir l'heure actuelle au format HERE Maps"""
    return datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

# Test de la fonction
if __name__ == "__main__":
    test_cases = [
        "2025-07-07T01:50:55.708956",  # Avec microsecondes
        "2025-07-07T01:50:55",        # Format correct
        "2025-07-07T01:50:55Z",       # Avec timezone
        "",                           # Vide
        None,                         # None
        "invalid"                     # Invalide
    ]
    
    for test in test_cases:
        result = validate_here_datetime(test)
        print(f"Input: {test} -> Output: {result}")