import email
import base64
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_properties_from_messages(messages, client):
    results = set()
    for message in messages:
        email_data = client.gmail_service.users().messages().get(userId='me', id=message['id'], format='full').execute()
        email_raw = client.gmail_service.users().messages().get(userId='me', id=message['id'], format='raw').execute()
        headers = email_data["payload"]["headers"]
        subject = None
        for header in headers:
            if header["name"] == "Subject":
                subject = header["value"]

        if "southern superpolygon" not in subject.lower():
            logger.info(f"Skipping email {subject}")
            continue
        else:
            logger.info(f"Found new email {subject}")

        raw = email_raw["raw"]
        bytes_raw = base64.urlsafe_b64decode(raw)
        msg = email.message_from_bytes(bytes_raw)
        htmls = []
        if msg.is_multipart():                         # True for Rightmove alerts
            for part in msg.walk():                    # depth-first traversal
                ctype = part.get_content_type()        # e.g. text/html
                if ctype == "text/html":
                    html_bytes = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    htmls.append(html_bytes.decode(charset, "replace"))
                else:
                    logger.warning(f"Warning: {ctype}")
        else:
            logger.warning("Warning: not multipart")

        assert len(htmls) == 1
        html = htmls[0]
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table", cellspacing="0", cellpadding="0")
        found_count = 0
        for table in tables:
            divs = table.find_all("div")
            links = table.find_all("a")
            for div in divs:
                if "pcm" in div.text.lower():
                    price_per_month = div.text
                    # Remove the pound sign from the start, the comma, and pcm, and just get the int
                    price_per_month = int(price_per_month.replace("£", "").replace(",", "").replace("pcm", "").strip())
                else:
                    continue

                curr = div
                while curr.find_all_next("a") == []:
                    curr = curr.parent
                link = curr.find_all_next("a")[0]["href"]

                while curr.find_all_next("tr") == []:
                    curr = curr.parent
                address = curr.find_all_next("tr")[1].text.strip()

                results.add((address, price_per_month, link))
    
    return results
