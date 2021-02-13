"""
Sends email notifications to selected users or mailing lists.
Adapted from:
https://docs.aws.amazon.com/ses/latest/DeveloperGuide/examples-send-using-smtp.html
"""

import settings
import smtplib
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = settings.setup_logger(__name__)

# Replace sender@example.com with your "From" address.
# This address must be verified.
# SENDER = 'mpetermangis@gmail.com'
SENDER = 'updates@marinepollution.ca'
SENDERNAME = 'Notification Service - marinepollution.ca'

# Replace recipient@example.com with a "To" address. If your account
# is still in the sandbox, this address must be verified.
RECIPIENTS = ['mpetermangis@gmail.com', 'Nicholas.Benoy@dfo-mpo.gc.ca']

# Replace smtp_username with your Amazon SES SMTP user name.
USERNAME_SMTP = settings.smtp_user

# Replace smtp_password with your Amazon SES SMTP password.
PASSWORD_SMTP = settings.smtp_pass

# (Optional) the name of a configuration set to use for this message.
# If you comment out this line, you also need to remove or comment out
# the "X-SES-CONFIGURATION-SET:" header below.
# CONFIGURATION_SET = "ConfigSet"

# If you're using Amazon SES in an AWS Region other than US West (Oregon),
# replace email-smtp.us-west-2.amazonaws.com with the Amazon SES SMTP
# endpoint in the appropriate region.
# List of SMTP endpoints is here:
# https://docs.aws.amazon.com/general/latest/gr/ses.html
# Must use the list of SMTP Endpoints, ***NOT*** the list of SES endpoints,
# which is just above that.  SES endpoints will not work, and will timeout after ~5 mins.
# The STMP server is defined in: settings.smtp_server
# The STMP PORT is defined in: settings.smtp_port

# The subject line of the email.
SUBJECT = 'Updated Spill Report - { Report Title }'

# The email body for recipients with non-HTML email clients.
BODY_TEXT = ("Amazon SES Test\r\n"
             "This email was sent through the Amazon SES SMTP "
             "Interface using the Python smtplib package."
            )

# The HTML body of the email.
BODY_HTML = """<html>
<head></head>
<body>
  <h1>Amazon SES SMTP Email Test</h1>
  <p>This email was sent with Amazon SES using the
    <a href='https://www.python.org/'>Python</a>
    <a href='https://docs.python.org/3/library/smtplib.html'>
    smtplib</a> library.</p>
</body>
</html>
            """

# Create message container - the correct MIME type is multipart/alternative.
msg = MIMEMultipart('alternative')
msg['Subject'] = SUBJECT
msg['From'] = email.utils.formataddr((SENDERNAME, SENDER))
msg['To'] = ', '.join(RECIPIENTS)
# Comment or delete the next line if you are not using a configuration set
# msg.add_header('X-SES-CONFIGURATION-SET',CONFIGURATION_SET)

# Record the MIME types of both parts - text/plain and text/html.
part1 = MIMEText(BODY_TEXT, 'plain')
part2 = MIMEText(BODY_HTML, 'html')

# Attach parts into message container.
# According to RFC 2046, the last part of a multipart message, in this case
# the HTML message, is best and preferred.
msg.attach(part1)
msg.attach(part2)


def main():
    # Try to send the message.
    try:
        logger.info('Connecting to SMTP server...')
        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
        server.ehlo()
        server.starttls()
        # stmplib docs recommend calling ehlo() before & after starttls()
        server.ehlo()
        logger.info('Connected. Sending email...')
        server.login(USERNAME_SMTP, PASSWORD_SMTP)
        server.sendmail(SENDER, RECIPIENTS, msg.as_string())
        server.close()
    # Display an error message if something goes wrong.
    except Exception as e:
        logger.error("Error: ", e)
    else:
        logger.info("Email sent!")


if __name__ == '__main__':
    main()
