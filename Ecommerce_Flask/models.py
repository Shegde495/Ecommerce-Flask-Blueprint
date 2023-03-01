from Ecommerce_Flask import db,app
#from __main__ import app
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask_login import UserMixin


class User(db.Model,UserMixin):
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(20),unique=True,nullable=False)
    email=db.Column(db.String(20),unique=True,nullable=False)
    image=db.Column(db.String(20),nullable=True,default="default.jpg")
    password=db.Column(db.String(20),nullable=False)
    order_in_cart=db.relationship('Cart',backref='user',lazy=True)
    order_by_user=db.relationship('Order',backref="user_purchase",lazy=True)
    
    def __repr__(self):
        return f"user('{self.username},{self.email},{self.image}')"
    
    
    def reset_password(self):
        s=Serializer(app.config['SECRET_KEY'])
        user_id={"user_id":self.id}
        token=s.dumps(user_id)
        return token 
    
    @staticmethod
    def check_token(token):
        s=Serializer(app.config['SECRET_KEY'])
        try:
            user_id=s.loads(token)["user_id"]
        except:
            return None
        return User.query.get(user_id)
        
    
class Products(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    product_name=db.Column(db.String(20),nullable=False)
    product_image=db.Column(db.String(20),nullable=True,default="product.jpg")
    product_des=db.Column(db.Text,nullable=True)
    product_price=db.Column(db.Integer,nullable=False)
    quantity = db.Column(db.Integer, nullable=False,default=1)
    product_in_cart=db.relationship('Cart',backref='product',lazy=True)
    product_ordered=db.relationship('Order',backref='product_orders',lazy=True)
   
    @property
    def display_quantity(self):
       if self.quantity >0:
           return self.quantity
       else:
           return "Out of stock"
    
    
    def __repr__(self):
        return f"products('{self.id},{self.product_name},{self.product_price},{self.quantity}')"
    
class Cart(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id',ondelete='CASCADE'),nullable=False)
    product_id=db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'),nullable=False)
    quantity=db.Column(db.Integer,nullable=False,default=1)
    
    @property
    def display_cart_quantity(self):
        if self.product.quantity > 0:
            if self.product.quantity < self.quantity:
                 return f'only {self.product.quantity} is available'
            else:
                return self.quantity
        else:
            return "Out of stock"
    
    def __repr__(self):
        return f"Cart_items('{self.id},{self.user_id},{self.product_id}')"
    

class Order(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    payer_id=db.Column(db.String(25),nullable=False)
    payment_id=db.Column(db.String(20),nullable=False)
    quantity=db.Column(db.Integer,nullable=False,default=1)
    total_price=db.Column(db.Integer,nullable=False)
    ordered_date=db.Column(db.DateTime,nullable=False,default=datetime.utcnow())
    product_id=db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'),nullable=False)
    user_id=db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'),nullable=False)
   
    def __repr__(self):
        return f"Order_items('{self.id},{self.user_id},{self.product_id}')"