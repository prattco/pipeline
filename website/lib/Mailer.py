# Mailer.py

import smtplib
from email.mime.text import MIMEText


def send_email(subject, body, to_email):
    # SMTP server configuration
    smtp_server = 'smtp.office365.com'
    smtp_port = 587  # Update with the appropriate port for your SMTP server
    smtp_username = 'autodonotreply@prattco.com'
    smtp_password = 'DNot@0414'
    
    # Create a MIMEText object to represent the email body
    message = MIMEText(body)
    message['From'] = 'autodonotreply@prattco.com'
    message['To'] = to_email
    # Test email to
    # message['To'] = 'danny.yun@chicagolandcfs.com'
    message['Subject'] = subject

    # Connect to the SMTP server
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()  # Enable TLS encryption
        server.login(smtp_username, smtp_password)  # Login to the SMTP server
        server.sendmail(message['From'], [to_email], message.as_string())  # Send the email

