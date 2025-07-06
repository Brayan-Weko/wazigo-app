import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app
from backend.models import db
from backend.models.subscription import init_subscription_plans, init_default_ads

def main():
    """Initialiser le système d'abonnement."""
    print("🚀 Initialisation du système d'abonnement Smart Route...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Créer les tables si elles n'existent pas
            db.create_all()
            print("✅ Tables de base de données créées/vérifiées")
            
            # Initialiser les plans d'abonnement
            init_subscription_plans()
            print("✅ Plans d'abonnement initialisés")
            
            # Initialiser les publicités par défaut
            init_default_ads()
            print("✅ Publicités de démonstration créées")
            
            print("\n🎉 Système d'abonnement initialisé avec succès !")
            print("\nPlans disponibles :")
            print("- Gratuit : 45km trafic, 1 pays, 50 recherches/jour, avec pub")
            print("- Premium : Illimité, sans pub, 2$/mois")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation : {str(e)}")
            return False
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)