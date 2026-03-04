from app import app, db
from app import models  # Important pour charger les modèles

if __name__ == '__main__':
    # Créer toutes les tables dans la base de données
    with app.app_context():
        db.create_all()
        print("✅ Base de données créée avec succès !")
    
    # Lancer l'application
    app.run(debug=True)
