import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(to_email):
    smtp_server = "smtp.gmail.com"
    port = 587  # Use port 587 for TLS/STARTTLS
    sender_email = "rania.fds.spring24@gmail.com"
    password = "eybm yiws ygfu qmcn"
    subject = 'Fall Detected!'
    message = 'A fall has been detected. Please check the fall detection system.'

    try:
        context = ssl.create_default_context()

        server = smtplib.SMTP(smtp_server, port)
        server.starttls(context=context)  # Start TLS encryption
        server.login(sender_email, password)

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(message, 'plain'))

        server.send_message(msg)  

    except Exception as e:
        print(e)

    finally:
        server.quit() 


to_email = 'to_email@example.com'
# user will input their email 

send_email(to_email)
