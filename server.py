import os
from flask import Flask, render_template
from datetime import datetime
from dotenv import load_dotenv
import stripe
import json

app = Flask(__name__)
load_dotenv()
stripe.api_key = os.getenv('STRIPE_PKEY')
@app.route('/stripeData/<product_id>')
def stripeData(product_id):
    try:
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
    try:
        data = json.loads(request.data)
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': data['name'],
                        'description': data['description'],
                    },
                    'unit_amount': data['price'],
                },
                'quantity': data['quantity'],
            }],
            mode='payment',
            success_url='http://localhost:5000/confirmation',
            cancel_url='http://localhost:5000/payment',
        )
        return jsonify(session)
    except Exception as e:
        return str(e)