"""
Sends email notifications to selected users or mailing lists.
Adapted from:
https://docs.aws.amazon.com/ses/latest/DeveloperGuide/examples-send-using-smtp.html
"""

import json
import smtplib
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import jinja2

import settings

# For rendering HTML templates
try:
    templateLoader = jinja2.FileSystemLoader(searchpath='./app/templates')
    env = jinja2.Environment(loader=templateLoader)
    email_template = env.get_template('report_email.html')
except:
    pass

logger = settings.setup_logger(__name__)

# Replace sender@example.com with your "From" address.
# This address must be verified.
SENDER = 'updates@marinepollution.ca'
SENDERNAME = 'Notification Service - marinepollution.ca'

# Replace recipient@example.com with a "To" address. If your account
# is still in the sandbox, this address must be verified.
# RECIPIENTS = ['mpetermangis@gmail.com', 'Nicholas.Benoy@dfo-mpo.gc.ca']
# RECIPIENTS = ['mpetermangis@gmail.com']
# RECIPIENTS = settings.DEFAULT_UPDATE_LIST

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


"""
Utility functions for loading/saving mailing lists
"""
def load_mailing_list():
    with open(settings.MAILING_LIST_FILE) as f:
        data = json.load(f)
    return data.get('lists')


def save_mailing_list(list_name, emails):
    mail_lists = load_mailing_list()

    # List of mailing lists
    mail_lists_updated = []

    for ml in mail_lists:

        if ml.get('name') == list_name:
            ml['emails'] = emails
        mail_lists_updated.append(ml)

    # # Set mailing list emails
    data = {'lists': mail_lists_updated}

    with open(settings.MAILING_LIST_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_maillist_by_name(list_name):
    recipients = None
    mail_lists = load_mailing_list()
    for ml in mail_lists:
        if ml.get('name') == list_name:
            recipients = ml.get('emails')
            logger.info('Mailing list: %s, sending to: %s' % (
                list_name, recipients))

    # If mail list not found, use default
    if not recipients:
        recipients = ','.join(settings.DEFAULT_UPDATE_LIST)
        logger.warning('Mailing list %s not found: using default: %s' % (
            list_name, recipients))
    return recipients


def notify_report(msg_content, msg_subject, recipients):
    """
    Sends an HTML formatted email notification
    :param msg_content: email content
    :param msg_subject: subject line
    :param recipients: comma-separated list of recipients
    :return:
    """

    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = msg_subject
    msg['From'] = email.utils.formataddr((SENDERNAME, SENDER))
    msg['To'] = recipients

    # Record the MIME types of both parts - text/plain and text/html.
    # part1 = MIMEText(BODY_TEXT, 'plain')
    part_html = MIMEText(msg_content, 'html')

    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    # msg.attach(part1)
    msg.attach(part_html)

    if not settings.NOTIFY_EMAILS:
        logger.warning('Email notifications disabled for testing!')
    else:
        send_message(msg)


def send_message(msg):
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
        server.sendmail(SENDER, msg.get('To'), msg.as_string())
        server.close()
    # Display an error message if something goes wrong.
    except Exception as e:
        logger.error("Error: ", e)
    else:
        logger.info("Email sent!")


def test_notify_report(report_num, report_name):
    logger.info('Sending email update for: %s' % report_num)
    # The subject line of the email.
    SUBJECT = 'Updated Spill Report - %s (%s)' % (report_name, report_num)

    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = """
    Pollution Report Update - %s

    The following pollution report was updated:
    %s, %s

    For details, please see the report page: 
    https://marinepollution.ca/report/%s

    This notification was automatically sent from the DFO/CCG Spill Tracker at https://marinepollution.ca. Do not reply to this message. 
    """ % (report_num, report_name, report_num, report_num)

    # The HTML body of the email.
    BODY_HTML = email_template.render(report_title=report_name, report_num=report_num)

    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = SUBJECT
    msg['From'] = email.utils.formataddr((SENDERNAME, SENDER))
    msg['To'] = ', '.join(settings.DEFAULT_UPDATE_LIST)
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

    send_message(msg)


def main():
    test_notify_report(123, 'title')


if __name__ == '__main__':
    main()
