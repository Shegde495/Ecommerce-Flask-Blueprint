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
from Ecommerce_Flask.User.utils import send_email


users=Blueprint('users',__name__)





@login.user_loader
def load_user(id):
    return User.query.get(id) 

user_model=api.model('User',{
    'id':fields.Integer,
    'username':fields.String,
    'email':fields.String   
})

success_model = api.model('success',{
    "Success":fields.String(example='Success response')
})  


# parser=reqparse.RequestParser()
# parser.add_argument('username',type=str,help='Enter the Username',required=True)
# parser.add_argument('email',type=str,help='Enter the Username',required=True)
# parser.add_argument('password',type=str,help='Enter the Username',required=True)
# parser.add_argument('confirm_password',type=str,help='Enter the Username',required=True)

users_ns = Namespace('users', description='User operations')




input_model = api.model('InputModel', {
    'username': fields.String(required=True, example='John Doe'),
    'email': fields.String(required=True, example='john.doe@example.com'),
    'password': fields.String(required=True,example='password'),  
    'confirm_password': fields.String(required=True,example='confirm_password')},doc=False)

register_model=api.model('RegisterModel',{
    "success":fields.String(example='User registered successfully')
})

error_model = api.model('ErrorModel',{
    "Error": fields.String(example='An error occurred')
})

@users_ns.route('/register',methods=['POST'])
class register(Resource):
    @api.doc(security=[])
    @api.response(200,'success',register_model)
    @api.response(400,'invalid',error_model)
    @api.expect(input_model,validate=True,doc=False)
    def post(self):
        data=request.json
        # if 'username' not in data or 'email' not in data or 'password' not in data or 'confirm_password' not in data:
        #     return ({"Error":"Username,email,password,confirm_password is required "}),400
        username=data['username']
        email=validate_email(data['email'])
        password=data['password']
        confirm_password=data['confirm_password']
        if User.query.filter_by(username=username).first() is not None:
            return ({"Error":"Username already exist"}),400
        if not email :
            return ({"Error":"Enter valid email address"}),400
        if User.query.filter_by(email=data['email']).first() is not None:
            return ({"Error":"Email already exist"}),400
        if password!=confirm_password:
            return ({"Error":"Password doesnt match"}),400
        password_encrypted=bcrypt.hashpw(password.encode('utf-8'),bcrypt.gensalt())
        user=User(username=username,email=data['email'],password=password_encrypted.decode('utf-8'))
        db.session.add(user)
        db.session.commit()
        response={"success":"User registered successfully"}
        return make_response(response,201)
    
#api.models.pop('InputModel')


login_model = api.model('login', {
    'email': fields.String(required=True, example='john.doe@example.com'),
    'password': fields.String(required=True,example='password'),  
    },doc=False)


login_models=api.model('loginmodel',{
    "success":fields.String(example='Login successfull'),
    "access":fields.String(example='Encrypted access token '),
    "refresh":fields.String(example='Encrypted refresh token ')
    
})
@users_ns.route('/login',methods=['POST'])
class login(Resource):
    @api.doc(security=[])
    @api.expect(login_model,validate=True)
    @api.response(200,'success',login_models)
    @api.response(400,'invalid',error_model)
    def post(self):
        data=request.json
        if 'email' not in data or 'password' not in data:
            return ({"Error":"Email and password is required"}),400
        email=validate_email(data['email'])
        password=data['password']
        if not email:
            return ({"Error":"Enter valid email address"}),400
        user=User.query.filter_by(email=data['email']).first() 
        if user is None:
            return ({"Error":"Email not yet registered "}),400
        if user and bcrypt.checkpw(password.encode('utf-8'),user.password.encode('utf-8')):
            login_user(user)
            access_token=create_access_token(identity=user.id)
            refresh_token=create_refresh_token(identity=user.id)
            # print(current_user)
            # return ({"success":"login successful","access":access_token,"refresh":refresh_token}),200
            response_data = {
            "success": "Login successful",
            "access": access_token,
            "refresh": refresh_token,
               }
            response = make_response(response_data,200)
            return response
        else:
            return ({"Error":"Invalid credentials"}),400
        
        
parser=api.parser()
parser.add_argument('username', type=str, required=True)
parser.add_argument('email', type=str, required=True)
parser.add_argument('file', location='files', type=FileStorage, required=False)  

profile_model=api.model('Profile',{
    "success":fields.String(example="Profile Updated successfully")
})

getprofile_model=api.model('GetProfile',{
    'Username':fields.String(example="username of the user"),
    'Email':fields.String(example="email of the user"),
    'Image':fields.String(example="image of the user"),
    "orders":fields.String(example="[List of orders placed by the user]")

})
  
@users_ns.route('/profile',methods=['GET','POST'])
class profile(Resource):
    @jwt_required()
    @api.doc(
        security='Bearer Auth',
             authorizations={
                 'Bearer Auth': {
                     'type': 'apiKey',
                     'in': 'header',
                     'name': 'Authorization'
                 }
             },
    )
    @api.response(200,'success',profile_model)
    @api.response(400,'invalid',error_model)
    @api.expect(parser)
    def post(self):
        user_id=get_jwt_identity()
        user=User.query.filter_by(id=user_id).first()
        #print(user)
        data=parser.parse_args()
        username=data['username']
        email=data['email']
        image=data['file']
        if image:
            _,file_ext=os.path.splitext(image.filename)
            random_hex=secrets.token_hex(8)
            new_name=random_hex+file_ext
            path=os.path.join(app.root_path,'static/profile_images',new_name)
            image.save(path)
            user.image=new_name
        if username:
            if User.query.filter_by(username=username).first() is not None:
                return ({'Error':'Username already exists'}),400
            user.username=username
        if email:
            if not validate_email(email):
                return ({'Error':'Enter a valid email address'}),400
            if User.query.filter_by(email=email).first() is not None:
                return ({'Error':'Email already exists'})
            user.email=email
        db.session.commit()
        return ({"success":"Profile Updated successfully"}),200
    
    @jwt_required()
    @api.doc(security='Bearer Auth',
             authorizations={
                 'Bearer Auth': {
                     'type': 'apiKey',
                     'in': 'header',
                     'name': 'Authorization',
                     'valuePrefix': ''
                 }
             })
    @api.response(200,'success',getprofile_model)
    @api.response(400,'invalid')
    def get(self):
        user_id=get_jwt_identity()
        user=User.query.filter_by(id=user_id).first()
        order=Order.query.filter_by(user_id=user_id).all()
        orders=[]
        if order:         
            for i in order:
                orders.append({"Product Name":i.product_orders.product_name,"Product quantity":i.quantity,"Total Price":i.total_price})
        return ({"Username":user.username,"Email":user.email,"Image":user.image,"orders":orders}),200

@users_ns.route('/forgotpassword', methods=['POST'])
class resetpassword(Resource):
    @api.doc(security=[],params={'email': {'type':'string','required':True,'description':'Enter the email address you have registered'}})
    @api.response(200,'success',success_model)
    @api.response(404,'Not found',error_model)
    @api.response(400,'invalid',error_model)
    def post(self):
        email = request.args.get('email')
        if not validate_email(email):
            return ({"Error":"Enter a valid email address"}),400
        user=User.query.filter_by(email=email).first()
        if user is None:
            return ({"Error":"Email not yet registered"}),400
        link="http://127.0.0.1:5000/resetpassword/"+user.reset_password()
        print(link)
        send_email(user,link)
        return ({"Success":"A link has been sent to your registered email address to reset your password"}),200

password_model=api.model('Password',{
    'password':fields.String(required=True,description="Enter new password"),
    'confirm_password':fields.String(required=True,description="Confirm new password")
},doc=False
)

@users_ns.route('/resetpassword/<token>', methods=['POST'])
class reset(Resource):
    @api.doc(security=[],params={'token':{
        'type':'string','required':True,'description':'Enter the token','in':'path'
    }})
    @api.expect(password_model)
    @api.response(200,'success')
    @api.response(404,'Not found')
    @api.response(400,'invalid')
    def post(self,token):
        data=request.json
        pass1=data['password']
        pass2=data['confirm_password']
        if pass1==pass2:
            user=User.check_token(token)
            if user is None:
                return ({"Error":"Token maybe expired, please try again"}),400
            else:
                password=bcrypt.hashpw(pass1.encode('utf-8'), bcrypt.gensalt())
                user.password = password.decode('utf-8')
                db.session.commit()
                return ({"Success":"Your password has been changed successfully"}),200    
        else:
            return ({"Error":"Passwords do not match"}),400
        
@api.errorhandler
def handle_auth_error(error):
    if isinstance(error, JWTDecodeError):
        return ({}),401
    elif isinstance(error, InvalidHeaderError):
       return ({}),401
    elif isinstance(error, NoAuthorizationError):
        return ({}),401
    else:
       return ({}),401
        
api.add_namespace(users_ns)