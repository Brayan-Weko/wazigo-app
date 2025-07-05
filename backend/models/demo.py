# Exemple d'utilisation dans une route Flask
from ..models import User, SavedRoute, RouteHistory, UserAnalytics

# Créer un utilisateur
user = User(email='user@example.com', name='John Doe')
user.save()

# Sauvegarder un itinéraire
route = SavedRoute(
    name='Maison → Travail',
    origin_address='123 Rue de la Paix',
    origin_lat=48.8566,
    origin_lng=2.3522,
    destination_address='456 Avenue des Champs',
    destination_lat=48.8738,
    destination_lng=2.2950,
    user_id=user.id
)
route.save()

# Enregistrer un trajet dans l'historique
history = RouteHistory(
    session_id='abc123',
    origin_address='123 Rue de la Paix',
    origin_lat=48.8566,
    origin_lng=2.3522,
    destination_address='456 Avenue des Champs',
    destination_lat=48.8738,
    destination_lng=2.2950,
    selected_route_data={'route': 'data'},
    travel_time_seconds=1800,
    distance_meters=12000,
    optimization_score=8.5,
    user_id=user.id
)
history.save()

# Mettre à jour les analytics
analytics = UserAnalytics.get_or_create(user.id)
analytics.update_from_route_history()