from app.pdf_generator import generate_payment_receipt, generate_student_card
from flask import render_template, request, redirect, url_for, flash, send_file
from app import app, db
from app.models import Student, Payment, MobilePayment, CashRegister
from app.pdf_generator import generate_payment_receipt
import random
import string
from datetime import datetime
import traceback

# ============================================
# FRAIS DE SCOLARITÉ PAR CLASSE (pour l'année)
# ============================================
FRAIS_PAR_CLASSE = {
    '6ème': 50000,
    '5ème': 70000,
    '4ème': 75000,
    '3ème': 90000,
    'Seconde': 100000,
    'Première': 110000,
    'Terminale': 130000
}

# ============================================
# FONCTION DE VÉRIFICATION DES PAIEMENTS
# ============================================
def verifier_paiement_eleve(student_id, nouveau_montant, mois):
    """
    Vérifie si l'élève peut encore payer
    Retourne (bool, str, reste) : (peut_payer, message, reste)
    """
    student = Student.query.get(student_id)
    if not student:
        return False, "Élève non trouvé", 0

    total_du = FRAIS_PAR_CLASSE.get(student.class_name, 0)
    if total_du == 0:
        return False, f"Classe {student.class_name} non reconnue", 0

    paiements = Payment.query.filter_by(student_id=student_id, status='paid').all()
    total_paye = sum(p.amount for p in paiements) if paiements else 0

    mois_deja_paye = Payment.query.filter_by(student_id=student_id, month=mois, status='paid').first()
    if mois_deja_paye:
        return False, f"⛔ Le mois de {mois} a déjà été payé", total_du - total_paye

    nouveau_total = total_paye + nouveau_montant

    if nouveau_total > total_du:
        reste = total_du - total_paye
        return False, f"⛔ Montant trop élevé. Total dû: {total_du} FCFA, déjà payé: {total_paye} FCFA, reste à payer: {reste} FCFA", reste

    reste = total_du - nouveau_total

    if nouveau_total == total_du:
        return True, f"✅ Paiement accepté. Félicitations ! Scolarité complète pour {student.class_name}", reste
    else:
        return True, f"✅ Paiement accepté. Reste à payer : {reste} FCFA", reste

# ============================================
# ROUTES PRINCIPALES
# ============================================
@app.route('/')
def accueil():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    total_students = Student.query.count()
    total_payments = Payment.query.count()
    total_mobile_transactions = MobilePayment.query.count()
    total_cash = CashRegister.query.count()

    entries = CashRegister.query.all()
    total_income = sum(e.amount for e in entries if e.transaction_type == 'income')
    total_expense = sum(e.amount for e in entries if e.transaction_type == 'expense')
    balance = total_income - total_expense

    return render_template('dashboard.html',
                         total_students=total_students,
                         total_payments=total_payments,
                         total_mobile_transactions=total_mobile_transactions,
                         total_cash=total_cash,
                         total_income=total_income,
                         total_expense=total_expense,
                         balance=balance)

# ============================================
# ROUTES POUR LES ÉLÈVES
# ============================================
@app.route('/students')
def students_list():
    students = Student.query.all()
    return render_template('students/list.html',
                         students=students,
                         frais_par_classe=FRAIS_PAR_CLASSE)
@app.route('/students/add', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        print("="*50)
        print("1️⃣ DONNÉES REÇUES DU FORMULAIRE:")
        for key, value in request.form.items():
            print(f"   {key}: {value}")
        print("="*50)
        
        try:
            # Téléphone
            parent_phone = request.form.get('parent_phone', '')
            parent_phone = ''.join(filter(str.isdigit, parent_phone))
            if parent_phone:
                if len(parent_phone) != 8:
                    flash('❌ Le numéro de téléphone doit contenir exactement 8 chiffres', 'error')
                    return redirect(url_for('add_student'))
                formatted_phone = f"+227 {parent_phone[:2]} {parent_phone[2:4]} {parent_phone[4:6]} {parent_phone[6:8]}"
            else:
                formatted_phone = ''

            # Frais d'inscription (sécurisé)
            registration_fee_str = request.form.get('registration_fee', '0')
            try:
                registration_fee = float(registration_fee_str) if registration_fee_str else 0
            except:
                registration_fee = 0
                print(f"   ⚠️ Conversion registration_fee échouée, valeur: {registration_fee_str}")

            # Création de l'élève
            print("2️⃣ CRÉATION DE L'ÉLÈVE...")
            student = Student(
                first_name=request.form.get('first_name', '').strip(),
                last_name=request.form.get('last_name', '').strip(),
                class_name=request.form.get('class_name', '').strip(),
                parent_phone=formatted_phone,
                registration_fee=registration_fee,
                registration_paid=(request.form.get('registration_payment_method') != 'pending'),
                registration_payment_method=request.form.get('registration_payment_method', 'pending'),
                nationalite=request.form.get('nationalite', '').strip(),
                extrait_naissance='extrait_naissance' in request.form,
                bulletins_fournis='bulletins_fournis' in request.form,
                carte_valide='carte_valide' in request.form
            )
            print(f"   Élève créé: {student.first_name} {student.last_name}")

            if student.registration_paid:
                student.registration_date = datetime.utcnow()
                print(f"   Date d'inscription enregistrée")

            print("3️⃣ AJOUT À LA SESSION...")
            db.session.add(student)
            db.session.flush()  # ← C'est ici que l'ID est généré
            print(f"   ID attribué: {student.id}")

            # ✅ GÉNÉRER LA CARTE APRÈS AVOIR L'ID
            if student.carte_valide:
                student.carte_numero = student.generer_numero_carte()
                student.carte_date_emission = datetime.utcnow()
                print(f"   Carte générée: {student.carte_numero}")

            if student.registration_paid and student.registration_fee > 0:
                cash_entry = CashRegister(
                    transaction_type='income',
                    category='registration',
                    amount=student.registration_fee,
                    description=f"Frais d'inscription - {student.first_name} {student.last_name}",
                    student_id=student.id,
                    payment_method='cash' if student.registration_payment_method == 'cash' else 'mobile',
                    reference=f"REG-{student.id}-{datetime.now().strftime('%Y%m')}",
                    created_by='admin'
                )
                db.session.add(cash_entry)
                print(f"   Entrée en caisse ajoutée")

            print("4️⃣ COMMIT...")
            db.session.commit()
            print("5️⃣ COMMIT RÉUSSI !")

            # Messages flash
            flash(f'✅ Élève {student.first_name} {student.last_name} ajouté avec succès !', 'success')

            if student.registration_paid:
                flash(f'💰 Frais d\'inscription de {int(student.registration_fee)} FCFA enregistrés', 'success')
            else:
                flash(f'⚠️ N\'oubliez pas de payer les frais d\'inscription de {int(student.registration_fee)} FCFA', 'info')

            if student.carte_valide and student.carte_numero:
                flash(f'🆔 Carte scolaire générée: {student.carte_numero}', 'success')

            print("="*50)
            print("✅ FIN - Redirection vers students_list")
            print("="*50)
            
            return redirect(url_for('students_list'))

        except Exception as e:
            db.session.rollback()
            error_message = str(e)
            print("❌"*50)
            print(f"ERREUR DÉTAILLÉE: {error_message}")
            traceback.print_exc()
            print("❌"*50)
            flash(f'❌ Erreur: {error_message}', 'error')
            return redirect(url_for('add_student'))

    return render_template('students/add.html')


@app.route('/students/edit/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)

    if request.method == 'POST':
        try:
            # Téléphone
            parent_phone = request.form.get('parent_phone', '')
            parent_phone = ''.join(filter(str.isdigit, parent_phone))
            if parent_phone:
                if len(parent_phone) != 8:
                    flash('❌ Le numéro doit contenir exactement 8 chiffres', 'error')
                    return redirect(url_for('edit_student', student_id=student_id))
                formatted_phone = f"+227 {parent_phone[:2]} {parent_phone[2:4]} {parent_phone[4:6]} {parent_phone[6:8]}"
            else:
                formatted_phone = ''

            # Frais d'inscription
            registration_fee_str = request.form.get('registration_fee', '0')
            try:
                registration_fee = float(registration_fee_str) if registration_fee_str else 0
            except:
                registration_fee = 0

            # Mise à jour des champs
            student.first_name = request.form.get('first_name', '').strip()
            student.last_name = request.form.get('last_name', '').strip()
            student.class_name = request.form.get('class_name', '').strip()
            student.parent_phone = formatted_phone
            student.registration_fee = registration_fee

            # Mode de paiement
            new_method = request.form.get('registration_payment_method', 'pending')
            if new_method != student.registration_payment_method:
                student.registration_payment_method = new_method
                student.registration_paid = (new_method != 'pending')
                if student.registration_paid and not student.registration_date:
                    student.registration_date = datetime.utcnow()

            # Critères
            student.nationalite = request.form.get('nationalite', '').strip()
            student.extrait_naissance = 'extrait_naissance' in request.form
            student.bulletins_fournis = 'bulletins_fournis' in request.form

            # Carte scolaire
            carte_valide = 'carte_valide' in request.form
            if carte_valide and not student.carte_valide:
                student.carte_valide = True
                student.carte_numero = student.generer_numero_carte()
                student.carte_date_emission = datetime.utcnow()
            elif not carte_valide and student.carte_valide:
                student.carte_valide = False

            db.session.commit()
            flash(f'✅ Élève {student.first_name} {student.last_name} modifié !', 'success')
            return redirect(url_for('students_list'))

        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur: {str(e)}', 'error')
            return redirect(url_for('edit_student', student_id=student_id))

    return render_template('students/edit.html', student=student)

@app.route('/students/delete/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    try:
        if Payment.query.filter_by(student_id=student_id).count() > 0:
            flash('❌ Impossible : cet élève a des paiements', 'error')
            return redirect(url_for('students_list'))
        db.session.delete(student)
        db.session.commit()
        flash(f'✅ Élève {student.first_name} {student.last_name} supprimé', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur: {str(e)}', 'error')
    return redirect(url_for('students_list'))

@app.route('/student/carte/<int:student_id>')
def view_carte(student_id):
    student = Student.query.get_or_404(student_id)
    return render_template('students/carte.html', student=student)

# ============================================
# ROUTES POUR LES PAIEMENTS NORMAUX
# ============================================
@app.route('/payments')
def payments_list():
    payments = Payment.query.all()
    return render_template('payments/list.html', payments=payments)

@app.route('/payments/add', methods=['GET', 'POST'])
def add_payment():
    if request.method == 'POST':
        try:
            student_id = int(request.form.get('student_id'))
            amount = float(request.form.get('amount'))
            month = request.form.get('month')

            peut_payer, message, reste = verifier_paiement_eleve(student_id, amount, month)
            if not peut_payer:
                flash(f'❌ {message}', 'error')
                return redirect(url_for('add_payment'))

            payment = Payment(
                student_id=student_id,
                amount=amount,
                month=month,
                status='paid'
            )
            db.session.add(payment)
            db.session.flush()

            cash_entry = CashRegister(
                transaction_type='income',
                category='tuition',
                amount=amount,
                description=f"Paiement scolarité - {month}",
                student_id=student_id,
                payment_id=payment.id,
                payment_method='cash',
                reference=f"PAY-{payment.id}-{datetime.now().strftime('%Y%m')}",
                created_by='admin'
            )
            db.session.add(cash_entry)
            db.session.commit()

            flash(f'✅ Paiement de {amount} FCFA enregistré !', 'success')
            if reste == 0:
                flash(f'🎉 Scolarité complète pour cet élève !', 'success')
            else:
                flash(f'💰 Reste à payer : {reste} FCFA', 'info')
            return redirect(url_for('payments_list'))

        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {str(e)}', 'error')
            return redirect(url_for('add_payment'))

    students = Student.query.all()
    students_data = []
    for student in students:
        paiements = Payment.query.filter_by(student_id=student.id, status='paid').all()
        total_paye = sum(p.amount for p in paiements) if paiements else 0
        total_du = FRAIS_PAR_CLASSE.get(student.class_name, 0)
        reste = total_du - total_paye
        students_data.append({
            'student': student,
            'total_paye': total_paye,
            'total_du': total_du,
            'reste': reste,
            'complete': reste <= 0
        })
    return render_template('payments/add.html', students_data=students_data)

# ============================================
# ROUTES POUR LES PAIEMENTS MOBILE
# ============================================
@app.route('/payments/mobile')
def mobile_payment():
    students = Student.query.all()
    students_data = []
    for student in students:
        paiements = Payment.query.filter_by(student_id=student.id, status='paid').all()
        total_paye = sum(p.amount for p in paiements) if paiements else 0
        total_du = FRAIS_PAR_CLASSE.get(student.class_name, 0)
        reste = total_du - total_paye
        students_data.append({
            'student': student,
            'total_paye': total_paye,
            'total_du': total_du,
            'reste': reste,
            'complete': reste <= 0
        })
    return render_template('payments/mobile.html', students_data=students_data)

@app.route('/process-mobile-payment', methods=['POST'])
def process_mobile_payment():
    try:
        student_id = request.form.get('student_id')
        operator = request.form.get('operator')
        phone_number = request.form.get('phone_number')

        phone_number = ''.join(filter(str.isdigit, phone_number))
        if len(phone_number) != 8:
            flash('❌ Le numéro doit contenir exactement 8 chiffres', 'error')
            return redirect(url_for('mobile_payment'))

        full_phone = f"+227 {phone_number[:2]} {phone_number[2:4]} {phone_number[4:6]} {phone_number[6:8]}"
        amount = float(request.form.get('amount'))
        month = request.form.get('month')

        student = Student.query.get(student_id)
        if not student:
            flash('❌ Élève non trouvé', 'error')
            return redirect(url_for('mobile_payment'))

        peut_payer, message, reste = verifier_paiement_eleve(student_id, amount, month)
        if not peut_payer:
            flash(f'❌ {message}', 'error')
            return redirect(url_for('mobile_payment'))

        transaction_id = 'TXN' + ''.join(random.choices(string.digits, k=10))
        reference = 'REF' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        flash(f'📱 Demande de paiement envoyée au {full_phone}', 'info')
        success = random.choices([True, False], weights=[80, 20])[0]

        if success:
            payment = Payment(
                student_id=student_id,
                amount=amount,
                month=month,
                status='paid'
            )
            db.session.add(payment)
            db.session.flush()

            mobile_transaction = MobilePayment(
                student_id=student_id,
                payment_id=payment.id,
                phone_number=full_phone,
                operator=operator,
                amount=amount,
                transaction_id=transaction_id,
                reference=reference,
                status='success',
                completed_at=datetime.utcnow()
            )
            db.session.add(mobile_transaction)
            db.session.flush()

            cash_entry = CashRegister(
                transaction_type='income',
                category='tuition',
                amount=amount,
                description=f"Paiement mobile - {student.first_name} {student.last_name} - {month}",
                student_id=student_id,
                payment_id=payment.id,
                mobile_payment_id=mobile_transaction.id,
                payment_method='mobile',
                reference=reference,
                created_by='system'
            )
            db.session.add(cash_entry)
            db.session.commit()

            flash('✅ Paiement mobile réussi !', 'success')
            if reste == 0:
                flash(f'🎉 Scolarité complète pour {student.class_name}', 'success')
            return render_template('payments/confirm.html',
                                 success=True,
                                 transaction=mobile_transaction,
                                 student=student,
                                 month=month)
        else:
            mobile_transaction = MobilePayment(
                student_id=student_id,
                phone_number=full_phone,
                operator=operator,
                amount=amount,
                transaction_id=transaction_id,
                reference=reference,
                status='failed'
            )
            db.session.add(mobile_transaction)
            db.session.commit()
            error_msg = "Échec de la transaction. Veuillez réessayer."
            return render_template('payments/confirm.html',
                                 success=False,
                                 error=error_msg)

    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur: {str(e)}', 'error')
        return redirect(url_for('mobile_payment'))

@app.route('/mobile-transactions')
def mobile_transactions():
    transactions = MobilePayment.query.order_by(MobilePayment.created_at.desc()).all()
    return render_template('payments/transactions.html', transactions=transactions)

# ============================================
# ROUTES POUR LA CAISSE
# ============================================
@app.route('/cash-register')
def cash_register():
    entries = CashRegister.query.order_by(CashRegister.created_at.desc()).all()
    total_income = sum(e.amount for e in entries if e.transaction_type == 'income')
    total_expense = sum(e.amount for e in entries if e.transaction_type == 'expense')
    balance = total_income - total_expense
    return render_template('cash_register.html',
                         entries=entries,
                         total_income=total_income,
                         total_expense=total_expense,
                         balance=balance)

@app.route('/add-expense', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        try:
            expense = CashRegister(
                transaction_type='expense',
                category=request.form.get('category'),
                amount=float(request.form.get('amount')),
                description=request.form.get('description'),
                payment_method=request.form.get('payment_method'),
                reference=request.form.get('reference', f"EXP-{datetime.now().strftime('%Y%m%d%H%M')}"),
                created_by='admin'
            )
            db.session.add(expense)
            db.session.commit()
            flash('✅ Dépense enregistrée', 'success')
            return redirect(url_for('cash_register'))
        except Exception as e:
            flash(f'❌ Erreur: {str(e)}', 'error')
    return render_template('add_expense.html')

# ============================================
# ROUTES POUR LES REÇUS PDF
# ============================================
@app.route('/receipt/<int:payment_id>')
def download_receipt(payment_id):
    try:
        payment = Payment.query.get_or_404(payment_id)
        student = Student.query.get(payment.student_id)
        mobile_payment = MobilePayment.query.filter_by(payment_id=payment_id).first()
        pdf_buffer = generate_payment_receipt(payment, student, mobile_payment)
        filename = f"recu_paiement_{student.first_name}_{student.last_name}_{payment.month}.pdf"
        filename = filename.replace(' ', '_')
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'❌ Erreur lors de la génération du PDF: {str(e)}', 'error')
        return redirect(url_for('payments_list'))
@app.route('/student/carte/download/<int:student_id>')
def download_student_card(student_id):
    try:
        student = Student.query.get_or_404(student_id)
        
        if not student.carte_valide or not student.carte_numero:
            flash('❌ Cet élève n\'a pas de carte valide', 'error')
            return redirect(url_for('students_list'))
        
        pdf_buffer = generate_student_card(student)
        
        filename = f"carte_scolaire_{student.first_name}_{student.last_name}.pdf"
        filename = filename.replace(' ', '_')
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'❌ Erreur: {str(e)}', 'error')
        return redirect(url_for('students_list'))
