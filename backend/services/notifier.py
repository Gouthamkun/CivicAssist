import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client

from dotenv import load_dotenv

# Load environment variables from .env file
# Check for .env in current dir or parent (backend/)
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger("civicassist.notifier")

# --- Configuration ---
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM_NUMBER")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

def send_delay_email(target_email, user_name, grievance_draft):
    """Sends the grievance draft directly to the user's email."""
    if "YOUR_GMAIL" in SMTP_USER:
        logger.error("SMTP Credentials not set. Email not sent.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = target_email
        msg['Subject'] = "🚨 CivicAssist Action Required: Passport Delay Detected"

        body = f"""
        <html>
            <body>
                <h3>Hello {user_name},</h3>
                <p>Our monitoring system has detected that your passport process has exceeded the standard timeline (30+ days).</p>
                <p>We have drafted a formal grievance letter for you. You can find it below and in your CivicAssist dashboard.</p>
                <hr>
                <div style="background: #f3f4f6; padding: 15px; border-radius: 5px; font-family: monospace;">
                    {grievance_draft.replace('\n', '<br>')}
                </div>
                <hr>
                <p>Regards,<br>Team CivicAssist</p>
            </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        logger.info(f"Delay email sent to {target_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def trigger_voice_call(target_phone, user_name):
    """Triggers a Twilio voice call notifying the user of the delay."""
    if "YOUR_TWILIO" in TWILIO_SID:
        logger.error("Twilio Credentials not set. Call not triggered.")
        return False

    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        
        # TwiML instructions for the call
        twiml_msg = f"""
        <Response>
            <Say voice="alice">Hello {user_name}, this is an automated alert from CivicAssist. Your passport application appears to be delayed beyond the 30-day processing period. We have drafted a formal grievance letter and sent it to your registered email address. Please review it in your CivicAssist dashboard to take action. Thank you.</Say>
        </Response>
        """
        
        call = client.calls.create(
            twiml=twiml_msg,
            to=target_phone,
            from_=TWILIO_FROM
        )
        logger.info(f"Twilio call initiated to {target_phone}. Call SID: {call.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to trigger Twilio call: {e}")
        return False
