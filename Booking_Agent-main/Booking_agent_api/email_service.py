"""
Email Service for sending calendar event notifications
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending email notifications"""
    
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_user = os.getenv("EMAIL_USER")
        self.email_password = os.getenv("EMAIL_PASSWORD")
        
    def send_cancellation_email(self, event_details: Dict[str, Any], attendee_emails: List[str]) -> bool:
        """Send cancellation email to attendees"""
        if not self.email_user or not self.email_password:
            logger.warning("Email credentials not configured. Skipping email notification.")
            return False
            
        if not attendee_emails:
            logger.info("No attendees to notify")
            return True
            
        try:
            subject = f"Meeting Cancelled: {event_details.get('summary', 'Meeting')}"
            
            # Create email content
            body = f"""
            Hello,
            
            The following meeting has been cancelled:
            
            Meeting: {event_details.get('summary', 'Meeting')}
            Date: {event_details.get('start', {}).get('dateTime', 'Unknown')}
            
            This meeting has been removed from your calendar.
            
            Best regards,
            Calendar System
            """
            
            # Send to each attendee
            for email in attendee_emails:
                if email and '@' in email:
                    self._send_email(email, subject, body)
                    
            logger.info(f"Sent cancellation emails to {len(attendee_emails)} attendees")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send cancellation emails: {e}")
            return False
    
    def send_reschedule_email(self, event_details: Dict[str, Any], attendee_emails: List[str], new_time: str) -> bool:
        """Send reschedule email to attendees"""
        if not self.email_user or not self.email_password:
            logger.warning("Email credentials not configured. Skipping email notification.")
            return False
            
        if not attendee_emails:
            logger.info("No attendees to notify")
            return True
            
        try:
            subject = f"Meeting Rescheduled: {event_details.get('summary', 'Meeting')}"
            
            # Create email content
            body = f"""
            Hello,
            
            The following meeting has been rescheduled:
            
            Meeting: {event_details.get('summary', 'Meeting')}
            New Time: {new_time}
            
            Please check your calendar for the updated meeting time.
            
            Best regards,
            Calendar System
            """
            
            # Send to each attendee
            for email in attendee_emails:
                if email and '@' in email:
                    self._send_email(email, subject, body)
                    
            logger.info(f"Sent reschedule emails to {len(attendee_emails)} attendees")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send reschedule emails: {e}")
            return False
    
    def _send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send a single email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Create SMTP session
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            
            # Send email
            text = msg.as_string()
            server.sendmail(self.email_user, to_email, text)
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

# Global email service instance
email_service = EmailService()
