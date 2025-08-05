import yagmail
import smtplib
import pickle
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import pathlib
from email_extractor import extract_properties_from_messages

class EmailClient:
    def __init__(self, email):
        load_dotenv()
        print(f"Initialising email sender for {email}")

        self.email = email

        if os.getenv("GMAIL_APP_PASSWORD") is None:
            print("GMAIL_APP_PASSWORD is not set")
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
            print(f"Incorrect gmail app password for {self.email}")
        except Exception as e:
            print(f"Error sending email to {to}: {e}")
    
    def send_email_multiple_recipients(self, recipients, subject, contents):
        for recipient in recipients:
            self.send_email(recipient, subject, contents)
    
    # https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get?utm_source=chatgpt.com
    def get_recent_messages(self, days):
        # Use "to:me" to only get messages received by me (not sent)
        query = f'newer_than:{days}d to:whiteotto4@gmail.com'
        return self.gmail_service.users().messages().list(userId='me', q=query, maxResults=50).execute().get('messages', [])

    def _gmail_authenticate(self):
        google_token_file = pathlib.Path("token.pickle")
        if not google_token_file.exists():
            creds = self.oauth_authenticate()
            with open(google_token_file, 'wb') as token:
                pickle.dump(creds, token)
        else:
            print("Using existing token file")
            with open(google_token_file, 'rb') as token:
                creds = pickle.load(token)
            
            if not creds.valid:
                creds = self.oauth_authenticate()
                with open(google_token_file, 'wb') as token:
                    pickle.dump(creds, token)

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
