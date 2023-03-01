from flask import Blueprint
from flask import request,abort,make_response
from validate_email import validate_email
from flask_login import login_user
from flask_jwt_extended import create_access_token,create_refresh_token,get_jwt_identity,jwt_required
import bcrypt
import os 
import secrets
from flask_mail import Message
from flask_restx import Resource,fields,Namespace
from werkzeug.datastructures import FileStorage
from flask_jwt_extended.exceptions import JWTDecodeError,InvalidHeaderError,NoAuthorizationError
from Ecommerce_Flask import api,db,login,mail,app,migrate
from Ecommerce_Flask.models import User,Products,Cart,Order


cart=Blueprint('cart',__name__)

cart_ns=Namespace('cart', description='cart operations')

quantity_parser=api.parser()
quantity_parser.add_argument('quantity',type=int,default=1)

addtocart_model=api.model('addtocart',{
    "uploaded":fields.String(example='Item successfully added to cart'),
})

error_model = api.model('ErrorModel',{
    "Error": fields.String(example='An error occurred')
})

getaddtocart_model=api.model('add',{
    'Item':fields.String(example='Name of the item in the cart'),
    'Price':fields.String(example='Price of the item'),
    'Quantity':fields.String(example='Total number of quantity')
    
})

@cart_ns.route('/addtocart/<int:id>',methods=['GET','POST'])
#@jwt_required()
class addtocart(Resource): 
    @api.doc(params={'id':{'description':'ID of product','type':'integer','required': True}
                     ,'quantity':{'description':'Enter the quantity','type':'integer','default':1}},

             security='Bearer Auth',
             authorizations={
                 'Bearer Auth': {
                     'type': 'apiKey',
                     'in': 'header',
                     'name': 'Authorization'
                 }
             })
    @api.response(201,'uploaded',addtocart_model)
    @api.response(400,'invalid',error_model)
    @api.response(404,'not found',error_model)
    @api.expect(quantity_parser)
    @jwt_required()
    def post(self,id):    
        user_id=get_jwt_identity()
        data=quantity_parser.parse_args()
        product=Products.query.filter_by(id=id).first()   
        print(product)
        if product:
            if product.quantity==0:
                return({"Error":"Item out of stock."}), 400
            if Cart.query.filter_by(user_id=user_id,product_id=product.id).first() is not None:
                return({"Error":f'Item {product.product_name} already exist in cart'}),400
            else:
                
                if product.quantity< data['quantity']:
                    return({'Error':f'Sorry only {product.quantity} items left '})
                cart=Cart(user_id=user_id,product_id=product.id,quantity=data['quantity'])
                db.session.add(cart)
                db.session.commit()
                return({"success":f'Item {product.product_name} successfully added to the cart'}),201
        else:
            return ({"Error":"Item not found"}),404
       
    @api.doc(security=[],params={'id':{'description':'id in path','type':'integer'}})
    @api.response(200,'success',getaddtocart_model)
    @api.response(404,'invalid',error_model) 
    def get(self,id):
        product=Products.query.filter_by(id=id).first()
        if product:
            return ({"Item":product.product_name,"Price":product.product_price,"quantity":product.display_quantity}),200
        else:
             return ({'Error':'Item not found'}),404
         

cart_model = api.model('Cart', {
    'Total items': fields.String(example='Total items in the cart'),
    'Total cost': fields.String(example='Total cost of the cart'),
    'Cart items': fields.List(fields.String(example='Items in the cart'))
},doc=False)

@cart_ns.route('/viewcart',methods=['GET'])
class view(Resource):
    @api.response(200, 'Success', cart_model)
    @api.response(400, 'Bad Request')
    @api.doc(security='Bearer Auth',
             authorizations={
                 'Bearer Auth': {
                     'type': 'apiKey',
                     'in': 'header',
                     'name': 'Authorization'
                 }
             })
    @jwt_required()    
    def get(self):
        user_id=get_jwt_identity()
        cart=Cart.query.filter_by(user_id=user_id).all()
        data=[]
        total_items=0
        summation=0
        for i in cart:
            if i.quantity <= i.product.quantity:
                summation+=i.product.product_price * i.quantity
                total_items+=1
            data.append({"Product name":i.product.product_name,"product price":i.product.product_price,"quantity":i.display_cart_quantity})
        return ({"Total items":total_items,"Total cost":summation,"Cart items":data}),200
    
getupdate_model = api.model('updatecart', {
    'Product_name': fields.String(example='Name of the Item in the cart'),
    'Product_price': fields.String(example='Total  price of the Item '),
    'Quantity': fields.String(example='Quantity of the item')
},doc=False) 

success_model = api.model('success',{
    "Success":fields.String(example='Success response')
})        

delete_model = api.model('delete',{
    "Deleted":fields.String(example='Deletion response')
})
            
@cart_ns.route('/updatecart/<int:id>',methods=['GET','PUT','DELETE'])
class update(Resource):
        @jwt_required()
        @api.doc(security='Bearer Auth',authorizations={
                 'Bearer Auth': {
                     'type': 'apiKey',
                     'in': 'header',
                     'name': 'Authorization'
                 }
             },
            params={'id':{'type': 'integer', 'in': 'path', 'description': 'id of cart item '}})
        @api.response(200,'success',getupdate_model)
        @api.response(404,'Not Found',error_model)
        def get(self,id):
            user_id=get_jwt_identity()
            cart=Cart.query.filter_by(id=id,user_id=user_id).first()
            if cart:
                return ({"Product name":cart.product.product_name,"Product price":cart.product.product_price,
                            "quantity":cart.display_cart_quantity}),200
            else:
                return ({'Error':'No item found'}),404
            
        @jwt_required()   
        @api.doc(security='Bearer Auth',authorizations={
                 'Bearer Auth': {
                     'type': 'apiKey',
                     'in': 'header',
                     'name': 'Authorization'
                 }
             },
            params={'id':{'type': 'integer', 'in': 'path', 'description': 'id of cart item to update'}})
        @api.expect(quantity_parser)
        @api.response(200,'success',success_model)
        @api.response(400,'invalid',error_model)
        @api.response(404,'not found',error_model)
        def put(self,id):
            user_id=get_jwt_identity()
            if user_id:
                cart=Cart.query.filter_by(id=id,user_id=user_id).first()
                if cart:
                    data=quantity_parser.parse_args()
                    quantity=data['quantity']
                    if quantity:
                        if data['quantity']>cart.product.quantity:
                            if cart.product.quantity ==0:
                                return ({'Error':'Product out of stock'}),400
                            return ({'Error':f'only {cart.product.quantity} are available'}),400
                        cart.quantity=data['quantity']
                        db.session.commit()
                        return ({'Success':'Cart updated'}),200
                    else:
                        return ({'Error':'enter the quantity'}),400
                else:
                    return ({'Error':'Not found'}),404
            else:
                return ({'Error':'Authorization required'})
            
        @jwt_required()    
        @api.doc(security='Bearer Auth',authorizations={
                 'Bearer Auth': {
                     'type': 'apiKey',
                     'in': 'header',
                     'name': 'Authorization'
                 }
             },
            params={'id':{'type': 'integer', 'in': 'path', 'description': 'id of cart item to delete'}})  
        @api.response(204,'deleted',delete_model)
        @api.response(404,'not found',error_model)
        def delete(self,id):
            user_id=get_jwt_identity()
            cart=Cart.query.filter_by(id=id,user_id=user_id).first()
            if cart:
                db.session.delete(cart)
                db.session.commit()
                return ({'deleted':'Item deleted from the cart '}),204
            else:
                 return ({'Error':'No item found'}),404
    
    
api.add_namespace(cart_ns)