from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape, A5
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime
import random

# ============================================
# FONCTION POUR LES REÇUS DE PAIEMENT
# ============================================

def generate_payment_receipt(payment, student, mobile_payment=None):
    """
    Génère un reçu de paiement en PDF
    """
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=72)
    
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = styles['Heading1']
    title_style.alignment = 1
    
    heading2_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # En-tête
    elements.append(Paragraph("📚 ÉCOLE GESTION SCOLAIRE", title_style))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("Reçu de Paiement", heading2_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Numéro et date
    receipt_number = f"REC-{payment.id}-{payment.date.strftime('%Y%m')}"
    current_date = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    elements.append(Paragraph(f"<b>N° Reçu:</b> {receipt_number}", normal_style))
    elements.append(Paragraph(f"<b>Date d'émission:</b> {current_date}", normal_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Informations élève
    elements.append(Paragraph("<b>INFORMATIONS ÉLÈVE</b>", heading2_style))
    elements.append(Spacer(1, 0.1*inch))
    
    student_info = [
        f"<b>Nom complet:</b> {student.first_name} {student.last_name}",
        f"<b>Classe:</b> {student.class_name}",
        f"<b>Téléphone parent:</b> {student.parent_phone or 'Non renseigné'}"
    ]
    for info in student_info:
        elements.append(Paragraph(info, normal_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Détails du paiement
    elements.append(Paragraph("<b>DÉTAILS DU PAIEMENT</b>", heading2_style))
    elements.append(Spacer(1, 0.1*inch))
    
    data = [
        ['Description', 'Détails'],
        ['Mois concerné', payment.month],
        ['Montant', f"{payment.amount:,.0f} FCFA"],
        ['Date de paiement', payment.date.strftime('%d/%m/%Y')],
        ['Statut', '✅ Payé']
    ]
    
    if mobile_payment:
        data.append(['Mode de paiement', f"Mobile Money ({mobile_payment.operator.upper()})"])
        data.append(['Téléphone', mobile_payment.phone_number])
        data.append(['Transaction ID', mobile_payment.transaction_id])
        data.append(['Référence', mobile_payment.reference])
    else:
        data.append(['Mode de paiement', 'Espèces'])
    
    table = Table(data, colWidths=[150, 250])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Signature
    signature_data = [
        ['', ''],
        ['', ''],
        ['Cachet de l\'école', 'Signature du responsable']
    ]
    
    signature_table = Table(signature_data, colWidths=[200, 200])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, -1), (0, -1), 'CENTER'),
        ('ALIGN', (1, -1), (1, -1), 'CENTER'),
        ('LINEABOVE', (0, -2), (-1, -2), 1, colors.black),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(signature_table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer


# ============================================
# FONCTION POUR LA CARTE SCOLAIRE
# ============================================

def generate_student_card(student):
    """
    Génère une carte d'identité scolaire avec design épuré bleu-blanc-vert
    """
    buffer = BytesIO()
    
    # Format carte de crédit (85.6 mm × 53.98 mm)
    CARD_WIDTH = 85.6 * mm
    CARD_HEIGHT = 53.98 * mm
    
    c = canvas.Canvas(buffer, pagesize=(CARD_WIDTH, CARD_HEIGHT))
    
    # ============================================
    # FOND BLANC PROPRE
    # ============================================
    c.setFillColor(colors.white)
    c.rect(0, 0, CARD_WIDTH, CARD_HEIGHT, fill=1, stroke=0)
    
    # ============================================
    # BANDE BLEUE EN HAUT
    # ============================================
    c.setFillColor(colors.HexColor('#1a5f9e'))  # Bleu foncé
    c.rect(0, CARD_HEIGHT-12*mm, CARD_WIDTH, 12*mm, fill=1, stroke=0)
    
    # Texte blanc sur bande bleue
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(CARD_WIDTH/2, CARD_HEIGHT-7*mm, "ÉCOLE GESTION SCOLAIRE")
    
    c.setFont("Helvetica", 7)
    c.drawCentredString(CARD_WIDTH/2, CARD_HEIGHT-10*mm, "Carte d'identité scolaire")
    
    # ============================================
    # BANDE VERTE EN BAS
    # ============================================
    c.setFillColor(colors.HexColor('#27ae60'))  # Vert
    c.rect(0, 0, CARD_WIDTH, 5*mm, fill=1, stroke=0)
    
    # ============================================
    # CADRE PHOTO (à gauche)
    # ============================================
    photo_x = 5*mm
    photo_y = CARD_HEIGHT - 35*mm
    photo_width = 20*mm
    photo_height = 25*mm
    
    # Fond gris clair pour la photo
    c.setFillColor(colors.HexColor('#ecf0f1'))
    c.rect(photo_x, photo_y, photo_width, photo_height, fill=1, stroke=0)
    
    # Bordure bleue
    c.setStrokeColor(colors.HexColor('#1a5f9e'))
    c.setLineWidth(0.5)
    c.rect(photo_x, photo_y, photo_width, photo_height, fill=0, stroke=1)
    
    # Texte "PHOTO" en gris
    c.setFillColor(colors.HexColor('#bdc3c7'))
    c.setFont("Helvetica", 8)
    c.drawCentredString(photo_x + photo_width/2, photo_y + photo_height/2, "PHOTO")
    
    # ============================================
    # INFORMATIONS PERSONNELLES (à droite)
    # ============================================
    info_x = photo_x + photo_width + 7*mm
    info_y = CARD_HEIGHT - 18*mm
    line_height = 5*mm
    
    # Fonction pour afficher une ligne d'information
    def draw_info_line(label, value, y_pos, is_important=False):
        # Label en bleu
        c.setFillColor(colors.HexColor('#1a5f9e'))
        c.setFont("Helvetica-Bold", 6)
        c.drawString(info_x, y_pos, label)
        
        # Valeur en noir
        if is_important:
            c.setFillColor(colors.HexColor('#27ae60'))  # Vert pour les valeurs importantes
            c.setFont("Helvetica-Bold", 8)
        else:
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 8)
        
        c.drawString(info_x + 20*mm, y_pos, str(value))
    
    # Afficher toutes les informations
    draw_info_line("NOM :", student.last_name.upper(), info_y)
    draw_info_line("PRÉNOM :", student.first_name, info_y - line_height)
    draw_info_line("CLASSE :", student.class_name, info_y - 2*line_height)
    
    # Date de naissance (formatée)
    birth_date = student.carte_date_emission.strftime('%d/%m/%Y') if student.carte_date_emission else "01/01/2000"
    draw_info_line("NÉ(E) LE :", birth_date, info_y - 3*line_height)
    
    draw_info_line("NATIONALITÉ :", student.nationalite or "Nigérienne", info_y - 4*line_height)
    
    # ============================================
    # NUMÉRO DE CARTE (en bas, bien visible)
    # ============================================
    carte_num = student.carte_numero or f"{student.class_name[:3].upper()}-{student.id:04d}"
    
    # Fond vert pour le numéro
    c.setFillColor(colors.HexColor('#27ae60'))
    c.rect(5*mm, 10*mm, CARD_WIDTH-10*mm, 8*mm, fill=1, stroke=0)
    
    # Numéro en blanc
    c.setFillColor(colors.white)
    c.setFont("Courier-Bold", 12)
    c.drawCentredString(CARD_WIDTH/2, 14*mm, carte_num)
    
    # Label au-dessus du numéro
    c.setFillColor(colors.HexColor('#1a5f9e'))
    c.setFont("Helvetica-Bold", 5)
    c.drawCentredString(CARD_WIDTH/2, 9*mm, "NUMÉRO D'IDENTIFICATION")
    
    # ============================================
    # DATES DE VALIDITÉ (en bas, à gauche et droite)
    # ============================================
    emission_date = student.carte_date_emission.strftime('%d/%m/%Y') if student.carte_date_emission else datetime.now().strftime('%d/%m/%Y')
    annee = datetime.now().year
    
    c.setFillColor(colors.HexColor('#1a5f9e'))
    c.setFont("Helvetica", 5)
    c.drawString(5*mm, 4*mm, f"Émis le: {emission_date}")
    c.drawRightString(CARD_WIDTH-5*mm, 4*mm, f"Valable: {annee}-{annee+1}")
    
    # ============================================
    # ÉLÉMENTS DE SÉCURITÉ DISCRETS
    # ============================================
    
    # Micro-texte en fond (très discret)
    c.setFillColor(colors.HexColor('#ecf0f1'))
    c.setFont("Helvetica", 3)
    for i in range(3):
        c.drawString(5*mm, 2*mm + i, "ECOLE GESTION SCOLAIRE • DOCUMENT OFFICIEL • ")
    
    # Petit hologramme (cercle vert)
    c.setFillColor(colors.HexColor('#27ae60'))
    c.circle(CARD_WIDTH - 8*mm, 8*mm, 1*mm, fill=1, stroke=0)
    
    # ============================================
    # LIGNES DE SÉPARATION POUR UNE MEILLEURE LECTURE
    # ============================================
    c.setStrokeColor(colors.HexColor('#bdc3c7'))
    c.setLineWidth(0.2)
    
    # Ligne verticale de séparation
    c.line(photo_x + photo_width + 3*mm, CARD_HEIGHT-15*mm, 
           photo_x + photo_width + 3*mm, CARD_HEIGHT-45*mm)
    
    # Lignes horizontales légères
    for i in range(5):
        y = CARD_HEIGHT - (18 + i*5) * mm
        c.line(info_x, y + 2*mm, info_x + 45*mm, y + 2*mm)
    
    c.save()
    buffer.seek(0)
    return buffer
