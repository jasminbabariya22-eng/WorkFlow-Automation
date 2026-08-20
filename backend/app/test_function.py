import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_test_email(
    email_to: str,
    email_cc: str,
    email_from: str,
    outgoing_server_type: str,
    outgoing_server_ip: str,
    outgoing_email_user: str,
    outgoing_email_password: str,
    outgoing_email_port: int,
    subject: str = "Test Email",
    body: str = "<h3>Email Configuration Test Successful</h3>"
):

    try:

        msg = MIMEMultipart()

        msg["From"] = email_from
        msg["To"] = email_to
        msg["Cc"] = email_cc or ""
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "html"))

        to_list = [x.strip() for x in email_to.split(",")] if email_to else []
        cc_list = [x.strip() for x in email_cc.split(",")] if email_cc else []

        recipients = to_list + cc_list

        smtp = smtplib.SMTP(
            outgoing_server_ip,
            outgoing_email_port
        )

        # TLS
        if outgoing_server_type and outgoing_server_type.upper() == "TLS":
            smtp.starttls()

        smtp.login(
            outgoing_email_user,
            outgoing_email_password
        )

        smtp.sendmail(
            email_from,
            recipients,
            msg.as_string()
        )

        smtp.quit()

        return True, "Email sent successfully"

    except Exception as e:
        return False, str(e)
    
    
### call the function
success, message = send_test_email(
    email_to="jasminbabariya22@gmail.com",
    email_cc="jasminbabariya7@gmail.com",
    email_from="jasmin.babariya@alethelabs.co.in",
    outgoing_server_type="SMTP",
    outgoing_server_ip="mail.alethelabs.co.in",
    outgoing_email_user="jasmin.babariya@alethelabs.co.in",
    outgoing_email_password="*********",
    outgoing_email_port=587
)

print(success)
print(message)