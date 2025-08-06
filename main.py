import argparse
from Location import Location
from GoogleApi import GoogleApi
from EmailClient import EmailClient
from email_extractor import extract_properties_from_messages
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
    
def main():
    # add argument for new address
    parser = argparse.ArgumentParser()
    parser.add_argument("--specific-address", type=str, required=False)
    parser.add_argument("--print-only", action="store_true", required=False)
    parser.add_argument("--force-run", action="store_true", required=False)
    args = parser.parse_args()

    load_dotenv()
    api_key = os.getenv("GOOGLE_HOUSE_HUNT_API_KEY")
    assert api_key is not None, "GOOGLE_HOUSE_HUNT_API_KEY is not set"
    api = GoogleApi(api_key)

    pdt_address = "119, 121 Cannon St, London EC4N 5AT"
    imperial_address = "Exhibition Rd, South Kensington, London SW7 2AZ"
    symbolica_address = "66 City Rd, London EC1Y 1BD"

    work_locations = [
        (pdt_address, "TRANSIT", "Robbie", 40),
        (imperial_address, "BICYCLE", "Otto", 36),
        (imperial_address, "TRANSIT", "Otto", 36),
        (symbolica_address, "BICYCLE", "Charlie", 45),
        (symbolica_address, "TRANSIT", "Charlie", 45)
    ]

    if args.specific_address:
        location = Location(api, args.specific_address, -1, "???")
        location.scout(work_locations)
        logger.info(location)
    else:
        if not args.force_run:
            with open("last_run_date.txt", "r") as f:
                last_run_date_str = f.readlines()[0].strip()
        
            last_run_date = datetime.strptime(last_run_date_str, "%Y-%m-%d")
            time_since_last_run = datetime.now().date() - last_run_date.date()
            if time_since_last_run < timedelta(days=1):
                logger.info("Already ran today, skipping.")
                exit(0)
            logger.info("Hasn't run for a day, running again.")

        # Retrieve the last day of emails from the email client
        client = EmailClient("otto.white.apps@gmail.com")
        messages = client.get_recent_messages(1)
        properties = extract_properties_from_messages(messages, client)
        scouted_locations = Location.scout_locations(api, work_locations, properties)

        if args.print_only:
            for location in scouted_locations:
                print(location)
        else:
            todays_date = datetime.now().strftime("%Y/%m/%d")
            if len(scouted_locations) == 0:
                logger.info("No new houses found")
            else:
                all_locations_str = Location.to_big_string(scouted_locations)
                client.send_email_multiple_recipients(
                    ["otto.white20@imperial.ac.uk", "charlie.lidbury@icloud.com"],
                    f"Potential new houses {todays_date}",
                    all_locations_str)

            # Only prevent more runs if we have already sent an email
            with open("last_run_date.txt", "w") as f:
                f.write(datetime.now().strftime("%Y-%m-%d"))


if __name__ == "__main__":
    main()