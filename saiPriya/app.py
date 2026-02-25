from flask import Flask, request, jsonify, send_file
import random
from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import units
from reportlab.lib.pagesizes import A4
import io
from datetime import datetime

from flask_mysqldb import MySQL



app = Flask(__name__)
app.secret_key = "super_secret_key_123"


# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'priya_electrical'
mysql = MySQL(app)




suppliers = []

@app.route('/')
@app.route('/')
def home():
    return render_template('index.html', admin=False)




@app.route('/api/quote', methods=['POST'])
def add_quote():
    data = request.json
    cur = mysql.connection.cursor()

    quote_id = f"RFQ-{random.randint(1000,9999)}"

    cur.execute("""
        INSERT INTO quotes (id, name, phone, item, detail, status, address, latitude, longitude)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        quote_id,
        data['name'],
        data['phone'],
        data['item'],
        data['detail'],
        "pending",
        data.get('address'),
        data.get('latitude'),
        data.get('longitude')
    ))

    mysql.connection.commit()
    cur.close()

    return jsonify({
    "message": "Quote added",
    "quote_id": quote_id
})


@app.route('/api/quotes')
def get_quotes():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM quotes")
    rows = cur.fetchall()
    cur.close()

    quotes = []

    for row in rows:
        quotes.append({
            "id": row[0],
            "name": row[1],
            "phone": row[2],
            "item": row[3],
            "detail": row[4],
            "status": row[5],
            "address": row[6],
            "latitude": row[7],
            "longitude": row[8]
        })

    return jsonify(quotes)

@app.route('/api/quote/<id>', methods=['PUT'])
def update_quote(id):
    data = request.json
    cur = mysql.connection.cursor()

    cur.execute("UPDATE quotes SET status=%s WHERE id=%s",
                (data['status'], id))

    mysql.connection.commit()
    cur.close()

    return jsonify({"message": "Updated"})


@app.route('/api/quote/<id>', methods=['DELETE'])
def delete_quote(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM quotes WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()

    return jsonify({"message": "Deleted"})


@app.route('/api/supplier', methods=['POST'])
def add_supplier():
    data = request.json
    suppliers.append({
        "id": f"S-{random.randint(100,999)}",
        "name": data['name'],
        "company": data['company'],
        "phone": data['phone'],
        "type": data['type'],
        "detail": data['detail']
    })
    return jsonify({"message": "Supplier added"})


@app.route('/api/suppliers')
def get_suppliers():
    return jsonify(suppliers)

@app.route('/api/bill/<id>')
def generate_bill(id):
    client = request.args.get('client', 'Valued Customer')
    phone = request.args.get('phone', '0000000000')
    invoice_no = request.args.get('invoice', id)
    gst_rate = float(request.args.get('rate', 18))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM quotes WHERE id=%s", (id,))
    q = cur.fetchone()
    cur.close()

    if not q:
        return "Invoice Not Found"

    base_amount = 1000
    gst_amount = base_amount * gst_rate / 100
    total_amount = base_amount + gst_amount

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("<b>PriyaElectrical</b>", styles['Title']))
    elements.append(Paragraph("GSTIN: 29ABCDE1234F1Z5", styles['Normal']))
    elements.append(Paragraph("Address: Bengaluru, Electronic City Phase 1", styles['Normal']))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(f"<b>Invoice No:</b> {invoice_no}", styles['Normal']))
    elements.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d-%m-%Y')}", styles['Normal']))
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("<b>Bill To:</b>", styles['Heading3']))
    elements.append(Paragraph(f"Customer: {q[1]}", styles['Normal']))
    elements.append(Paragraph(f"Phone: {q[2]}", styles['Normal']))
    elements.append(Paragraph(f"Product: {q[3]}", styles['Normal']))
    elements.append(Spacer(1, 20))

    data = [
        ["Description", "Amount (₹)"],
        ["Product Amount", f"{base_amount:.2f}"],
        [f"GST ({gst_rate}%)", f"{gst_amount:.2f}"],
        ["Grand Total", f"{total_amount:.2f}"]
    ]

    table = Table(data, colWidths=[350, 120])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
        ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Thank you for your business!", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Invoice_{invoice_no}.pdf",
        mimetype='application/pdf'
    )
@app.route('/api/track', methods=['POST'])
def track_quote():
    data = request.json
    quote_id = data.get('quote_id')
    phone = data.get('phone')

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT * FROM quotes 
        WHERE id=%s AND phone=%s
    """, (quote_id, phone))

    row = cur.fetchone()
    cur.close()

    if row:
        result = {
            "id": row[0],
            "name": row[1],
            "phone": row[2],
            "item": row[3],
            "detail": row[4],
            "status": row[5],
            "address": row[6],
            "latitude": row[7],
            "longitude": row[8]
        }
        return jsonify(result)
    else:
        return jsonify({"error": "No matching record found"})

from flask import session, redirect, url_for, render_template
from werkzeug.security import check_password_hash, generate_password_hash

ADMIN_EMAIL = "admin@priya.com"
ADMIN_PASSWORD_HASH = generate_password_hash("Admin@123")
login_attempts = {}

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        ip = request.remote_addr

        if ip not in login_attempts:
            login_attempts[ip] = 0

        if login_attempts[ip] >= 5:
            return "Too many failed attempts. Try again later."

        if email == ADMIN_EMAIL and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin'] = True
            login_attempts[ip] = 0
            return redirect('/secure-control-panel')
        else:
            login_attempts[ip] += 1
            return "Invalid credentials"

    return render_template('admin.html')


@app.route('/secure-control-panel')
def secure_admin_panel():
    if not session.get('admin'):
        return redirect('/admin-login')

    return redirect('/?admin=true')



@app.route('/admin-logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)