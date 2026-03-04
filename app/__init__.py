from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

# Création de l'application Flask
app = Flask(__name__)
app.config.from_object(Config)

# Initialisation de la base de données
db = SQLAlchemy(app)

# Importer les routes APRÈS la création de app et db
from app import routes  # ← Cette ligne est CRUCIALE
from app import models
