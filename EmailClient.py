import yagmail
import smtplib
import pickle
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import pathlib
from email_extractor import extract_properties_from_messages
import logging
from requests import Request

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailClient:
    def __init__(self, email):
        load_dotenv()
        logger.info(f"Initialising email sender for {email}")

        self.email = email

        if os.getenv("GMAIL_APP_PASSWORD") is None:
            logger.error("GMAIL_APP_PASSWORD is not set")
            raise Exception("GMAIL_APP_PASSWORD is not set")

        self.yag = yagmail.SMTP(email, os.getenv("GMAIL_APP_PASSWORD"))

        self.gmail_service = self._gmail_authenticate()
    
    def send_email(self, to, subject, contents):
        try:
            self.yag.send(
                to=to,
                subject=subject,
                contents=contents
            )
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Incorrect gmail app password for {self.email}")
        except Exception as e:
            logger.error(f"Error sending email to {to}: {e}")
    
    # TODO: Use the native multiple recipients functionality so I can see who received it on my own email client
    def send_email_multiple_recipients(self, recipients, subject, contents):
        for recipient in recipients:
            contents_preseved = "<pre>\n" + contents + "\n</pre>"
            self.send_email(recipient, subject, contents_preseved)
    
    # https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get?utm_source=chatgpt.com
    def get_recent_messages(self, age):
        # Use "to:me" to only get messages received by me (not sent)
        query = f'newer_than:{age} to:whiteotto4@gmail.com'
        return self.gmail_service.users().messages().list(userId='me', q=query, maxResults=50).execute().get('messages', [])

    def _gmail_authenticate(self):
        google_token_file = pathlib.Path("token.pickle")
        if not google_token_file.exists():
            logger.info("No gmail token file found, creating new one")
            creds = self.oauth_authenticate()
            with open(google_token_file, 'wb') as token:
                pickle.dump(creds, token)
        else:
            logger.info("Using existing gmail token file")
            with open(google_token_file, 'rb') as token:
                creds = pickle.load(token)
            
            if not creds.valid:
                if creds.expired:
                    logger.info("Gmail token is expired, refreshing...")
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                        logger.warning(f"Error refreshing gmail token: {e}")
                        logger.info("Creating new gmail token...")
                        creds = self.oauth_authenticate()
                else:
                    logger.info("Gmail token is invalid, creating new one...")
                    creds = self.oauth_authenticate()

                with open(google_token_file, 'wb') as token:
                    pickle.dump(creds, token)
        
        if not creds.valid:
            logger.error("Gmail token is still invalid after attempting load, creating new one")

        return build('gmail', 'v1', credentials=creds)
    
    def oauth_authenticate(self):
        SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True, email_client=self, timeout=30)
        return creds

if __name__ == "__main__":
    client = EmailClient("otto.white.apps@gmail.com")
    messages = client.get_recent_messages(7)
    properties = extract_properties_from_messages(messages, client)

    # email_sender.send_email_multiple_recipients(
    #     recipients=["otto.white.apps@gmail.com"],
    #     subject="Another email from Python",
    #     contents="This is the body of the email. You can also include HTML if you want."
    # )
