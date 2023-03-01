from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from dotenv import load_dotenv
from flask_restx import Api
import os
load_dotenv()
#from flask_script import Manager

app=Flask(__name__)

api = Api(app, version='1.0', title='Ecommerce API',
          #doc='/doc/',
          security='Bearer Auth',
          authorizations={
              'Bearer Auth': {
                  'type': 'apiKey',
                  'in': 'header',
                  'name': 'Authorization',
                  'valuePrefix': ''
              }
          },ordered=True)

app.config['SECRET_KEY']=os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///ecommerce.db'
app.config['JWT_SECRET_KEY']=os.getenv('JWT_SECRET_KEY')
app.config['JWT_ACCESS_TOKEN_EXPIRES']=3600
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
db=SQLAlchemy(app)
migrate=Migrate(app,db)
login=LoginManager(app)
jwt=JWTManager(app)
mail = Mail(app)

from Ecommerce_Flask.User.routes import users
from Ecommerce_Flask.Cart.routes import cart
from Ecommerce_Flask.Product.routes import product
from Ecommerce_Flask.Payment.routes import payment

app.register_blueprint(users)
app.register_blueprint(cart)
app.register_blueprint(product)
app.register_blueprint(payment)
