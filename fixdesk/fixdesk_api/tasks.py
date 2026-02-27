import os

from celery import shared_task
import smtplib, ssl
from email.message import EmailMessage

from dotenv import load_dotenv
load_dotenv()

from django.template.loader import render_to_string

@shared_task
def send_mail(subject, to_email, context, type):
    port = 587
    smtp_server =os.getenv('SMTP_SERVER')
    username=os.getenv('EMAIL_USER')
    password =os.getenv('EMAIL_PASSWORD')
    
    if type == "admin":
        html_content = render_to_string('admin_notification.html', context)
    elif type == "user":
        html_content = render_to_string('user_notification.html', context)
    elif type == "verify":
        html_content = render_to_string('user_verification.html', context)
    elif type == "activate":
        html_content = render_to_string('user_activation.html', context)
    elif type == "message":
        html_content = render_to_string('message_notification.html', context)
    elif type == "issue_status":
        html_content = render_to_string('issue_status_notification.html', context)
    elif type == "task":
        html_content = render_to_string('task_notification.html', context)
    elif type == "task_status":
        html_content = render_to_string('task_status_notification.html', context)
    elif type == "comment":
        html_content = render_to_string('comment_notification.html', context)

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f"HelpDesk <{context.get('organization')}@fixdesk.ng>"
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
