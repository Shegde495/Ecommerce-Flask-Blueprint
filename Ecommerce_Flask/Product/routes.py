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


product=Blueprint('product',__name__)


products_ns=Namespace('products', description='products operations')

parser_obj=api.parser()
parser_obj.add_argument('product_name',type=str,required=True)
parser_obj.add_argument('product_image',location='files', type=FileStorage, required=False)
parser_obj.add_argument('product_des',type=str,required=True)
parser_obj.add_argument('product_price',type=int,required=True)
parser_obj.add_argument('product_quantity',type=int,required=True)

error_model = api.model('ErrorModel',{
    "Error": fields.String(example='An error occurred')
})

product_model = api.model('Product', {
    'product_id': fields.String(example="ID of the Product"),
    'product_name': fields.String(example="Product Name"),
    'product_des': fields.String(example="Product Description"),
    'product_image': fields.String(example="Product Image "),
    'product_price': fields.String(example="Product Price"),
    'quantity': fields.String(example="Product quantity")
})

product_upload=api.model('Productupload', {
    "uploaded":fields.String(example="Product Uploaded successfully")}
)


@products_ns.route('/products',methods=['GET','POST'])
class products(Resource):
    @api.doc(security=[])
    @api.expect(parser_obj)
    @api.response(201,'uploaded',product_upload)
    @api.response(400,'invalid',error_model)
    def post(self):
        data=parser_obj.parse_args()
        product_name=data['product_name']
        product_image=data['product_image']
        product_des=data['product_des']
        product_price=data['product_price']
        product_quantity=data['product_quantity']
        try:
            if product_image:
                _, file_ext = os.path.splitext(product_image.filename)
                random_hex = secrets.token_hex(8)
                new_name = random_hex + file_ext
                path = os.path.join(app.root_path, 'static/product_images', new_name)
                product_image.save(path)
                product = Products(product_name=product_name, product_des=product_des, product_price=product_price, quantity=product_quantity, product_image=new_name)
            else:
                product = Products(product_name=product_name, product_des=product_des, product_price=product_price, quantity=product_quantity)
            db.session.add(product)
            db.session.commit()
            return ({'uploaded':'Product uploaded successfully!'}), 201
        except:
               return ({'Error':'Error in uploading product.'}), 400
           
           
    @api.doc(security=[])
    @api.response(200, 'Success', product_model)
    def get(self):
        data=[]
        for i in Products.query.all():
            data.append({"product_id":i.id,"product name":i.product_name,"product_image":i.product_image,"product_des":i.product_des,"Product_price":i.product_price,"quantity":i.display_quantity})
        return ({"Products":data}),200

api.add_namespace(products_ns)