import argparse
import pickle
from Location import Location
from GoogleApi import GoogleApi
from EmailClient import EmailClient
from email_extractor import extract_properties_from_messages
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os
import logging
from math import ceil
from LocationConstraint import LocationConstraint

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_last_run_date():
    if os.path.exists("last_run_date.pickle"):
        with open("last_run_date.pickle", "rb") as f:
            return pickle.load(f)
    else:
        # If last_run_date.pickle was deleted, run retrospectively for 3 days.
        return datetime.now() - timedelta(days=3)

def exit_if_not_run_recently(time_since_last_run, run_interval_hours):
    if time_since_last_run < timedelta(hours=run_interval_hours):
        hours_since_last_run = time_since_last_run.seconds // (60 * 60)
        logger.info(f"Ran {hours_since_last_run} hours ago, skipping.")
        exit(0)
    else:
        logger.info(f"Hasn't run for {time_since_last_run}, running again.")

def get_gmail_date_filter(time_since_last_run):
    hours_since_last_run = ceil(time_since_last_run.seconds / (60 * 60))
    return f"{hours_since_last_run}h"

def scout_and_email_locations(api, location_constraints, run_interval_hours, args):
    last_run_date = get_last_run_date()
    time_since_last_run = datetime.now() - last_run_date # 3 days if last_run_date.pickle was deleted

    if not args.force_run:
        exit_if_not_run_recently(time_since_last_run, run_interval_hours)
        gmail_date_filter = get_gmail_date_filter(time_since_last_run)
    else:
        gmail_date_filter = f"{run_interval_hours}h"

    client = EmailClient("otto.white.apps@gmail.com")
    logger.info(f"Retrieving emails with gmail time filter: {gmail_date_filter}")
    messages = client.get_recent_messages(gmail_date_filter)
    properties = extract_properties_from_messages(messages, client)
    scouted_locations = Location.scout_locations(api, location_constraints, properties)

    if args.print_only:
        for location in scouted_locations:
            print(location)
    else:
        todays_date = datetime.now().strftime("%Y/%m/%d %H:%M")

        if len(scouted_locations) == 0:
            logger.info(f"No new properties found in the last {gmail_date_filter}.")
        else:
            all_locations_str = Location.to_big_string(scouted_locations)
            client.send_email_multiple_recipients(
                ["otto.white20@imperial.ac.uk", "charlie.lidbury@icloud.com", "robbiesbuxton@gmail.com"],
                f"Potential new houses ({todays_date})",
                all_locations_str)

        # Only prevent more runs if we have already sent an email
        with open("last_run_date.pickle", "wb") as f:
            pickle.dump(datetime.now(), f)


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

    location_constraints = [
        LocationConstraint(
            person_name="Robbie",
            max_transport_minutes=40,
            transport_mode="TRANSIT",
            target_name="PDT",
            target_address="119, 121 Cannon St, London EC4N 5AT"
        ),
        LocationConstraint(
            person_name="Otto",
            max_transport_minutes=37,
            transport_mode="BICYCLE",
            target_name="Imperial",
            target_address="Exhibition Rd, South Kensington, London SW7 2AZ"
        ),
        LocationConstraint(
            person_name="Otto",
            max_transport_minutes=40,
            transport_mode="TRANSIT",
            target_name="Imperial",
            target_address="Exhibition Rd, South Kensington, London SW7 2AZ"
        ),
        LocationConstraint(
            person_name="Otto",
            max_transport_minutes=37,
            transport_mode="BICYCLE",
            target_name="Lauren's house",
            target_address="45 Flowersmead, London"
        ),
        LocationConstraint(
            person_name="Otto",
            max_transport_minutes=40,
            transport_mode="TRANSIT",
            target_name="Lauren's house",
            target_address="45 Flowersmead, London"
        ),
        LocationConstraint(
            person_name="Charlie",
            max_transport_minutes=45,
            transport_mode="BICYCLE",
            target_name="Symbolica",
            target_address="66 City Rd, London EC1Y 1BD"
        ),
        LocationConstraint(
            person_name="Charlie",
            max_transport_minutes=45,
            transport_mode="TRANSIT",
            target_name="Symbolica",
            target_address="66 City Rd, London EC1Y 1BD"
        )
    ]

    if args.specific_address:
        location = Location(api, args.specific_address, -1, "???")
        location.scout(location_constraints)
        logger.info(location)
    else:
        run_interval_hours = 4
        scout_and_email_locations(api, location_constraints, run_interval_hours, args)


if __name__ == "__main__":
    main()