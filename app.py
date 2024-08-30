import secrets
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import requests
import os

# Initialize Flask app and configure database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tdk_records.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = secrets.token_hex(24)  # Replace with a real secret key

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# User model for storing user information
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Transaction model for storing transaction data
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(150), nullable=False)
    date = db.Column(db.String(150), nullable=False)
    metal_received = db.Column(db.Float, nullable=False)
    metal_used = db.Column(db.Float, nullable=False)
    hallmark_charges = db.Column(db.Float, nullable=False)
    packing_charges = db.Column(db.Float, nullable=False)
    labour_charges = db.Column(db.Float, nullable=False)
    no_of_pieces = db.Column(db.Integer, nullable=False)
    metal_pending = db.Column(db.String(10), nullable=False)
    total_cash_received = db.Column(db.Float, nullable=False)
    gold_price = db.Column(db.Float, nullable=False)

# Function to get the current gold price
def get_gold_price():
    api_key = "goldapi-kk2hsm01z6p5g-io"  # Replace with your GoldAPI key
    url = "https://www.goldapi.io/api/XAU/INR"
    headers = {"x-access-token": api_key}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        return data['price']
    except requests.RequestException as e:
        print(f"Error fetching gold price: {e}")
        return None

# Route to display the form
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        customer_name = request.form['customer_name']
        date = request.form['date']
        metal_received = float(request.form['metal_received'])
        metal_used = float(request.form['metal_used'])
        hallmark_charges = float(request.form['hallmark_charges'])
        packing_charges = float(request.form['packing_charges'])
        labour_charges = float(request.form['labour_charges'])
        no_of_pieces = int(request.form['no_of_pieces'])
        metal_pending = request.form['metal_pending']
        total_cash_received = float(request.form['total_cash_received'])

        gold_price = get_gold_price()
        if gold_price:
            new_transaction = Transaction(
                customer_name=customer_name,
                date=date,
                metal_received=metal_received,
                metal_used=metal_used,
                hallmark_charges=hallmark_charges,
                packing_charges=packing_charges,
                labour_charges=labour_charges,
                no_of_pieces=no_of_pieces,
                metal_pending=metal_pending,
                total_cash_received=total_cash_received,
                gold_price=gold_price
            )
            db.session.add(new_transaction)
            db.session.commit()
            flash('Transaction added successfully!', 'success')
            return redirect(url_for('index'))

    return render_template('index.html')

# Route to display end-of-day summary
@app.route('/summary', methods=['GET'])
def summary():
    customer_name = request.args.get('customer_name', '').strip()

    if customer_name:
        transactions = Transaction.query.filter(Transaction.customer_name.ilike(f"%{customer_name}%")).all()
    else:
        transactions = Transaction.query.all()

    total_metal_received = sum(t.metal_received for t in transactions)
    total_metal_used = sum(t.metal_used for t in transactions)
    total_money_received = sum(t.total_cash_received for t in transactions)
    total_metal_pending = sum(t.metal_received - t.metal_used for t in transactions if t.metal_pending.lower() == 'yes')

    all_transactions = Transaction.query.all()
    overall_metal_received = sum(t.metal_received for t in all_transactions)
    overall_metal_used = sum(t.metal_used for t in all_transactions)
    overall_money_received = sum(t.total_cash_received for t in all_transactions)
    overall_metal_pending = sum(t.metal_received - t.metal_used for t in all_transactions if t.metal_pending.lower() == 'yes')

    summary_data = {
        "total_metal_received": total_metal_received,
        "total_metal_used": total_metal_used,
        "total_money_received": total_money_received,
        "total_metal_pending": total_metal_pending,
        "customer_name": customer_name if customer_name else "All Customers",
        "overall_metal_received": overall_metal_received,
        "overall_metal_used": overall_metal_used,
        "overall_money_received": overall_money_received,
        "overall_metal_pending": overall_metal_pending
    }

    return render_template('summary.html', summary=summary_data, customer_name=customer_name, transactions=transactions)


@app.route('/update_summary', methods=['GET', 'POST'])
def update_summary():
    customer_name = request.args.get('customer_name', '').strip()

    if request.method == 'POST':
        # Get the updated data from the form
        new_metal_received = float(request.form['metal_received'])
        new_metal_used = float(request.form['metal_used'])
        new_total_cash_received = float(request.form['total_cash_received'])

        # Find the transactions for the customer
        transactions = Transaction.query.filter_by(customer_name=customer_name).all()

        # Update each transaction
        for transaction in transactions:
            transaction.metal_received = new_metal_received
            transaction.metal_used = new_metal_used
            transaction.total_cash_received = new_total_cash_received
            db.session.commit()

        flash('Summary updated successfully!', 'success')
        return redirect(url_for('summary', customer_name=customer_name))

    # Retrieve the current summary data for the customer
    transactions = Transaction.query.filter_by(customer_name=customer_name).all()
    summary_data = {
        "total_metal_received": sum(t.metal_received for t in transactions),
        "total_metal_used": sum(t.metal_used for t in transactions),
        "total_money_received": sum(t.total_cash_received for t in transactions),
        "total_metal_pending": sum(t.metal_received - t.metal_used for t in transactions if t.metal_pending.lower() == 'yes')
    }

    return render_template('update_summary.html', summary=summary_data, customer_name=customer_name)





if __name__ == '__main__':
    # Ensure that the database and tables are created within the application context
    with app.app_context():
        if not os.path.exists('tdk_records.db'):
            db.create_all()
    app.run(debug=True)
