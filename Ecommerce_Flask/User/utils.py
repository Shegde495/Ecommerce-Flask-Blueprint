from flask_mail import Message
from Ecommerce_Flask import mail,app

def send_email(user,value):
    msg = Message(
        subject='Reset Password',
        recipients=[user.email],
        sender=app.config['MAIL_USERNAME'],
        body=f'Your reset link is ' + value
    )
    mail.send(msg)
    
