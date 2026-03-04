from app import db
from datetime import datetime

class Student(db.Model):
    __tablename__ = 'students'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    class_name = db.Column(db.String(20), nullable=False)
    parent_phone = db.Column(db.String(20))

    # Frais d'inscription
    registration_fee = db.Column(db.Float, default=0)
    registration_paid = db.Column(db.Boolean, default=False)
    registration_date = db.Column(db.DateTime, nullable=True)
    registration_payment_method = db.Column(db.String(20), default='pending')

    # Critères d'inscription
    nationalite = db.Column(db.String(50), nullable=True)
    extrait_naissance = db.Column(db.Boolean, default=False)
    bulletins_fournis = db.Column(db.Boolean, default=False)

    # Carte scolaire
    carte_numero = db.Column(db.String(20), unique=True, nullable=True)
    carte_date_emission = db.Column(db.DateTime, nullable=True)
    carte_valide = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # RELATIONS CORRIGÉES - Chaque back_populates correspond à l'autre côté
    payments = db.relationship('Payment', back_populates='student_rel', lazy=True)
    mobile_payments = db.relationship('MobilePayment', back_populates='student_rel', lazy=True)
    cash_entries = db.relationship('CashRegister', back_populates='student_rel', lazy=True)

    def __repr__(self):
        return f'<Student {self.first_name} {self.last_name}>'

    def generer_numero_carte(self):
        """Génère un numéro de carte unique"""
        annee = datetime.now().strftime('%Y')
        classe_code = self.class_name[:3].upper() if self.class_name else 'XXX'
        return f"{annee}-{classe_code}-{self.id:04d}"


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    month = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='pending')
    date = db.Column(db.DateTime, default=datetime.utcnow)

    # Relation corrigée - nom différent pour éviter les conflits
    student_rel = db.relationship('Student', back_populates='payments')
    mobile_payment_rel = db.relationship('MobilePayment', back_populates='payment_rel', uselist=False)
    cash_entry_rel = db.relationship('CashRegister', back_populates='payment_rel', uselist=False)

    def __repr__(self):
        return f'<Payment {self.amount} FCFA - {self.month}>'


class MobilePayment(db.Model):
    __tablename__ = 'mobile_payments'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=True)
    phone_number = db.Column(db.String(20), nullable=False)
    operator = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_id = db.Column(db.String(50), unique=True)
    status = db.Column(db.String(20), default='pending')
    reference = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relations corrigées
    student_rel = db.relationship('Student', back_populates='mobile_payments')
    payment_rel = db.relationship('Payment', back_populates='mobile_payment_rel')
    cash_entry_rel = db.relationship('CashRegister', back_populates='mobile_payment_rel', uselist=False)

    def __repr__(self):
        return f'<MobilePayment {self.transaction_id} - {self.amount} FCFA>'


class CashRegister(db.Model):
    __tablename__ = 'cash_register'

    id = db.Column(db.Integer, primary_key=True)
    transaction_type = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))

    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=True)
    mobile_payment_id = db.Column(db.Integer, db.ForeignKey('mobile_payments.id'), nullable=True)

    payment_method = db.Column(db.String(20), default='cash')
    reference = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50), default='system')

    # Relations corrigées
    student_rel = db.relationship('Student', back_populates='cash_entries')
    payment_rel = db.relationship('Payment', back_populates='cash_entry_rel')
    mobile_payment_rel = db.relationship('MobilePayment', back_populates='cash_entry_rel')

    def __repr__(self):
        return f'<Cash {self.transaction_type} {self.amount} FCFA>'
