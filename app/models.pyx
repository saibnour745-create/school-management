from app import db
from datetime import datetime

# Modèle pour les élèves
class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)  # Prénom
    last_name = db.Column(db.String(50), nullable=False)   # Nom
    class_name = db.Column(db.String(20), nullable=False)  # Classe
    parent_phone = db.Column(db.String(20))                 # Téléphone parent
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Student {self.first_name} {self.last_name}>'

# Modèle pour les paiements
class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)            # Montant
    month = db.Column(db.String(20), nullable=False)        # Mois concerné
    status = db.Column(db.String(20), default='pending')    # État (payé/en attente)
    date = db.Column(db.DateTime, default=datetime.utcnow)  # Date du paiement
    
    # Relation avec l'élève
    student = db.relationship('Student', backref='payments')
    
    def __repr__(self):
        return f'<Payment {self.amount} FCFA - {self.month}>'
