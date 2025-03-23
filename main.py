import os
import stripe
from flask import Flask, render_template,jsonify,request,session,redirect,url_for
from flask_session import Session
from dotenv import load_dotenv
import datetime
import random

receipt= None
LOG_FILE="log.txt"
app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = os.getenv('SECRET_SKEY')
Session(app)
load_dotenv()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/checkout')
def checkout():
    return render_template('checkout.html', public_key=os.getenv('STRIPE_PKEY'))

@app.route('/confirmation')
def confirmation():
    global receipt
    receipt_number = request.args.get("receipt", "000000000")
    timestamp = request.args.get("timestamp", datetime.datetime.now().strftime("%I:%M %p %d/%m/%y"))
    return render_template("confirmation.html", confirmation_receipt=receipt, timestamp=timestamp)


@app.route('/stripeData/<product_id>')
def stripeData(product_id):
    try:
        stripe.api_key = os.getenv('STRIPE_PKEY')
        product = stripe.Product.retrieve(product_id)
        return jsonify({
            'id': product.id,
            'name': product.name,
            'description': product.description,

        })
    except Exception as e:
        return str(e)

@app.route('/checkout-session', methods=['POST'])
def session():

    global receipt

    try:       
        stripe.api_key = os.getenv('STRIPE_SKEY')
        
        receipt = str(random.randint(100000000, 999999999))

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": "price_1R5bboF4Cu6plZwPb9IaeUl6", 
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url="http://localhost:5000/confirmation?confirmation_receipt={receipt}&timestamp="
                        + datetime.datetime.now().strftime("%I:%M %p %d/%m/%y"),
            cancel_url="http://localhost:5000/",
        )
        
        return jsonify({"id": session.id})
    
    except Exception as e:
        return jsonify({"error": str(e)})

def log(operation_id, status,event_type):
    timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    # log_entry = f"{operation_id}\t{status}\t{timestamp}\n
    log_entry = f"{receipt}\t{operation_id}\t{status}\t{timestamp}\t{event_type}\n"

    with open(LOG_FILE, "a") as file:
        file.write(log_entry)

@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature")
    webhook_secret = os.getenv("WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except Exception as e:
        return jsonify({"error": str(e)}),

    event_type = event.get("type", "unknown")
    event_object = event.get("data", {}).get("object", {})
    session_id = event_object.get("id", "unknown") 

    status_mapping = {
        "product.created":"Product Created",
        "price.created":"Price Created",
        "checkout.session.creaated": "Checkout Created",
        "checkout.session.completed": "Checkout Completed",
        "checkout.session.expired": "Checkout Expired",
        "payment_intent.created": "Payment Initialized",
        "charge.succeeded": "Charge Succeded",
        "charge.succeded": "Charge Succeeded",
        "charge.updated": "Charge Updated",
        "payment_intent.succeeded": "Paid",
        "payment_intent.payment_failed": "Payment Fail",
        "refund.created": "Refund Created",
        "refund.updated": "Refund Updated",
        "charge.refunded": "Charge Refunded",
        "charge.refund.updated": "Charge Refund Updated",
    }

    status = status_mapping.get(event_type, "Unknown")

    log(session_id, status,event_type)
    return jsonify({"message": "Event logged"}),

def read_txt():
    with open("log.txt", "r") as file:
        lines = file.readlines()
    
    data = [line.strip().split("\t") for line in lines]
    return data

@app.route("/table", methods=["GET", "POST"])
def get_table():

    if request.method == "POST":
        search_id = request.form.get("id")
        return redirect(url_for("get_table", id=search_id))
    
    search_id = request.args.get("id")
    data = read_txt()
    
    filtered_data = []
    if search_id:
        filtered_data = [
            {"id": row[0], "status": row[2], "timestamp": row[3]}
            for row in data if row[0] == search_id
        ]
    
    if request.headers.get("Accept") == "application/json":
        if not filtered_data:
            return jsonify({"error": "ID not found"}), 404
        return jsonify({"data": filtered_data})
    
    return render_template("table.html", data=filtered_data, search_id=search_id)

if __name__ == "__main__":
    app.run(debug=True)
