from datetime import date
from backend.models.auth_models import PassportTracking

def is_passport_delayed(record: PassportTracking) -> bool:
    today = date.today()
    delta = (today - record.application_date).days

    buffer = 0
    if record.police_verification == "Pending":
        buffer = 15

    if record.application_type == "Tatkaal":
        return delta > (10 + buffer)
    else:
        return delta > (30 + buffer)

def generate_delay_email_html(record: PassportTracking, name: str) -> str:
    return f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; max-width: 600px; margin: auto;">
                <h2 style="color: #1e293b;"><span style="color: #e43137;">⚠</span> Your Passport May Be Delayed</h2>
                <p>Dear {name},</p>
                <p>Based on your application date (<strong>{record.application_date.strftime('%d %B %Y')}</strong>), your passport has crossed the expected processing period.</p>
                <p>This does not necessarily mean rejection, but we highly recommend you check the status of your application.</p>
                
                <h3 style="color: #1e293b;">Recommended Actions:</h3>
                <ol>
                    <li>
                        <strong>Check Live Status:</strong> Visit the official portal<br>
                        <a href="https://www.passportindia.gov.in/AppOnlineProject/statusTracker/trackStatusInpNew" style="color: #3b82f6;">Track Status Here</a>
                    </li>
                    <li>
                        <strong>File a Grievance:</strong> If status shows no movement, you can file an official grievance.<br>
                        <a href="https://portal2.passportindia.gov.in/AppOnlineProject/online/epayInit" style="color: #3b82f6;">Official Grievance Portal</a>
                    </li>
                </ol>

                <p style="background: #f8fafc; padding: 12px; border-left: 4px solid #94a3b8; font-size: 0.9em;">
                    <em>Disclaimer: CivicAssist is an independent tool and is not affiliated with Passport Seva or the Government of India. This is an automated civic alert based on typical SLA timelines.</em>
                </p>
                
                <p>Regards,<br><strong>CivicAssist Alert Engine</strong></p>
            </div>
        </body>
    </html>
    """
