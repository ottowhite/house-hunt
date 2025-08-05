import email
import base64
from bs4 import BeautifulSoup

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
            continue

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
                    print(f"Warning: {ctype}")
        else:
            print("Warning: not multipart")

        assert len(htmls) == 1
        html = htmls[0]
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table", cellspacing="0", cellpadding="0")
        found_count = 0
        for table in tables:
            spans = table.find_all("span")
            links = table.find_all("a")
            for span in spans:
                if "pcm" in span.text.lower():
                    price_per_month = span.text
                    # Remove the pound sign from the start, the comma, and pcm, and just get the int
                    price_per_month = int(price_per_month.replace("£", "").replace(",", "").replace("pcm", "").strip())
                else:
                    continue
                
                curr = span
                while curr.find_all_next("a") == []:
                    curr = curr.parent
                link = curr.find_all_next("a")[0]["href"]

                while curr.find_all_next("div") == []:
                    curr = curr.parent
                address = curr.find_all_next("div")[1].text

                results.add((address, price_per_month, link))
    
    return results
