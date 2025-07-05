from backend.app import create_app
from backend.models.subscription import initialize_subscription_system

if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
        success = initialize_subscription_system()
        if success:
            print("🎉 Système d'abonnement prêt !")
        else:
            print("❌ Échec de l'initialisation")