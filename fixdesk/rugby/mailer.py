import os
import smtplib, ssl
from email.message import EmailMessage

from dotenv import load_dotenv
load_dotenv()

from django.template.loader import render_to_string

def send_mail(subject, to_email, context, type, action):
    port = 587
    smtp_server =os.getenv('SMTP_SERVER')
    username=os.getenv('EMAIL_USER')
    password =os.getenv('EMAIL_PASSWORD')
    
    html_content = render_to_string(f'rugby/{type}/{action}.html', context)

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f"HelpDesk <rugby@fixdesk.ng>"
    msg['To'] = to_email
    msg.set_content(html_content, subtype='html')
    
    try:
        if port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
                server.login(username, password)
                server.send_message(msg)
        elif port == 587:
            with smtplib.SMTP(smtp_server, port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
        else:
            print ("use 465 / 587 as port value")
            exit()
        return True
    except Exception as e:
        print (e)
        return False
