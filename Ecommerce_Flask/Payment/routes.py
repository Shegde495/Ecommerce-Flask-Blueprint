from flask import Blueprint
from flask import request
from flask_jwt_extended import get_jwt_identity,jwt_required
from dotenv import load_dotenv
import os 
from flask_restx import Resource,fields,Namespace
from flask_jwt_extended.exceptions import JWTDecodeError,InvalidHeaderError,NoAuthorizationError
from Ecommerce_Flask import api,db,login,mail,app,migrate
from Ecommerce_Flask.models import User,Products,Cart,Order
load_dotenv()


payment=Blueprint('payment',__name__)


payment_ns=Namespace('payment', description='payment operations')
payment_redirect_ns=Namespace('payment_redirect',description='payment redirect path')

error_model = api.model('ErrorModel',{
    "Error": fields.String(example='An error occurred')
})

quantity_parser=api.parser()
quantity_parser.add_argument('quantity',type=int,default=1)

    

#    checkout

import paypalrestsdk


paypalrestsdk.configure({
  "mode": "sandbox", # sandbox or live
  "client_id": os.getenv('client_id'),
  "client_secret": os.getenv('client_secret') })

payment_model=api.model("Payment",{
    'Success':fields.String(example="Link to Paypal payment")
})

@payment_ns.route("/cartpayment", methods=["GET"])
class create_payment(Resource):
    @api.doc(security='Bearer Auth',authorizations={
                 'Bearer Auth': {
                     'type': 'apiKey',
                     'in': 'header',
                     'name': 'Authorization'
                 }
             })
    @jwt_required()
    @api.response(200,'success',payment_model)
    @api.response(400,'invalid',error_model)
    def get(self):
        user_id=get_jwt_identity()
        cart_items=Cart.query.filter_by(user_id=user_id).all()
        if cart_items:
            items=[]
            total=0
            for i in cart_items:
                if i.quantity >i.product.quantity:
                    if i.product.quantity==0:
                        return (f"Item {i.product.product_name} is out of stock ! Please remove the item from the cart and continue...")
                    else:
                        return (f"Item {i.product.product_name} has {i.display_cart_quantity} ....")
                total+=i.product.product_price*i.quantity
                items.append({"name":i.product.product_name, "price":i.product.product_price, "quantity":i.quantity,"sku":str(i.product.id),"currency":"USD"})
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "transactions": [
                    {
                        "amount": {
                            "total": total,
                            "currency": "USD"
                        },
                        "custom": user_id,
                        "description": "Payment for Flask API",
                        "item_list": {
                        "items": items
                    }
                    }
                ],
                "redirect_urls": {
                    "return_url": "http://127.0.0.1:5000/payment_redirect/cartexecute",
                    "cancel_url": "http://127.0.0.1:5000/payment/execute"
                }
            })

            if payment.create():
                for link in payment.links:
                    if link.method == "REDIRECT":
                        return (link.href),200
            else:
                return ({"error": payment.error}), 400
        else:
            return ({"error":"No items are available in cart"}), 400

@payment_redirect_ns.route("/cartexecute", methods=["GET"])
class execute_payment(Resource):
    @api.doc(security=[])
    @api.response(200,'success',payment_model)
    @api.response(404,'Not found',error_model)
    @api.response(400,'invalid',error_model)
    def get(self):
        payment_id = request.args.get('paymentId')
        payer_id = request.args.get('PayerID')
        payment = paypalrestsdk.Payment.find(payment_id)
        if payment.execute({"payer_id": payer_id}):
            for transaction in payment.transactions:
                for i in transaction['item_list']['items']:
                    order=Order(payer_id=payer_id, payment_id=payment_id,user_id=payment.transactions[0].custom,product_id=i['sku'],quantity=i['quantity'],total_price=float(i['price'])*int(i['quantity']))
                    db.session.add(order)
                    db.session.commit()
            #cart=Cart.query.filter_by(user_id=payment.transactions[0].custom).all()
            db.session.query(Cart).filter_by(user_id=payment.transactions[0].custom).delete()
            db.session.commit()
            return ({"success": "payment success"}), 200
        else:
            return ({"error": "payment failed"}), 400
    
    
@payment_ns.route("/productpayment/<int:id>", methods=["POST"])
class create_payment_product(Resource):
    @jwt_required()
    @api.doc(security='Bearer Auth',authorizations={
                 'Bearer Auth': {
                     'type': 'apiKey',
                     'in': 'header',
                     'name': 'Authorization'
                 }
             },
            params={'id':{'type': 'integer', 'in': 'path', 'description': 'id of product'}})
    @api.response(200,'success',payment_model)
    @api.response(400,'invalid',error_model)
    @api.response(404,'Not found',error_model)
    @api.expect(quantity_parser)
    def post(self,id):
        data=quantity_parser.parse_args()
        quantity=data['quantity']
        user_id=get_jwt_identity()
        product=Products.query.filter_by(id=id).first()
        if product:
            if product.quantity==0:
                return ("Item out of Stock"), 400
            if product.quantity<quantity:
                return (f'Only {product.quantity} items are left.'), 400
            if product:
                total=product.product_price*quantity
                items = [
                {
                    "name": product.product_name,
                    "price": str(product.product_price),
                    "currency": "USD",
                    "sku": product.id,
                    "quantity": quantity
                }
            ]
                payment = paypalrestsdk.Payment({
                    "intent": "sale",
                    "payer": {
                        "payment_method": "paypal"
                    },
                    "transactions": [
                        {
                            "amount": {
                                "total":total,
                                "currency": "USD"
                            },
                            "item_list": {
                            "items": items
                        },
                            "custom": user_id,
                            "description": "Payment for Flask API",
                        }
                    ],
                    "redirect_urls": {
                        "return_url": "http://127.0.0.1:5000/payment_redirect/productexecute",
                        "cancel_url": "http://127.0.0.1:5000/payment/execute"
                    }
                })

            if payment.create():
                for link in payment.links:
                    if link.method == "REDIRECT":
                        return (link.href),200
            else:
                return ({"error": payment.error}), 400
        else:
            return ({"error":"No products available"}), 400
        
        
@payment_redirect_ns.route("/productexecute", methods=["GET"])
class productexecute(Resource):
    @api.doc(security=[])
    @api.response(200,'success')
    @api.response(404,'Not found')
    @api.response(400,'invalid')
    def get(self):
        payment_id = request.args.get('paymentId')
        payer_id = request.args.get('PayerID')
        payment = paypalrestsdk.Payment.find(payment_id)
        if payment.execute({"payer_id": payer_id}):
            for transaction in payment.transactions:
                for i in transaction['item_list']['items']:
                    order=Order(payer_id=payer_id, payment_id=payment_id,user_id=payment.transactions[0].custom,product_id=i['sku'],quantity=i['quantity'],total_price=float(i['price'])*int(i['quantity']))
                    db.session.add(order)
                    db.session.commit()
            product=Products.query.filter_by(id=int(payment.transactions[0].item_list.items[0].sku)).first()
            value=product.quantity-int(payment.transactions[0].item_list.items[0].quantity)
            product.quantity=value
            db.session.commit()
            return ({"success": "payment success"}), 200
        else:
            return ({"error": "payment failed"}), 400
    



api.add_namespace(payment_ns)
api.add_namespace(payment_redirect_ns)