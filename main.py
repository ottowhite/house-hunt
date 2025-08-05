import requests
import argparse
from EmailClient import EmailClient
from email_extractor import extract_properties_from_messages
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os

class GoogleApi:
    def __init__(self, api_key):
        self.api_key = api_key
        self.places_url = "https://places.googleapis.com/v1/places:searchText"
        self.routes_url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        self.headers = lambda field_mask: {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask
        }
    
    def get_places(self, text_query):
        data = {
            "textQuery": text_query
        }

        response = requests.post(self.places_url, headers=self.headers("places.displayName,places.formattedAddress"), json=data)
        return response.json()["places"]

    def get_travel_time_and_distance(self, origin_address, destination_address, transport_mode):
        # Transit is public transport
        assert transport_mode in ["BICYCLE", "DRIVE", "WALK", "TRANSIT"], "Invalid transport mode"

        next_monday_morning = datetime.now() + timedelta(days=(1 - datetime.now().weekday()) % 7)
        next_monday_morning = next_monday_morning.replace(hour=8, minute=0, second=0, microsecond=0)
        departure_time = next_monday_morning.isoformat() + "Z"

        data = {
            "origin": {
                "address": origin_address,
            },
            "destination": {
                "address": destination_address,
            },
            "travelMode": transport_mode,
            "departureTime": departure_time
        }

        response = requests.post(self.routes_url, headers=self.headers("routes.duration,routes.distanceMeters"), json=data)
        seconds_str = response.json()["routes"][0]["duration"]
        distance_meters_str = response.json()["routes"][0]["distanceMeters"]
        # Remove the s from the end and parse to int
        seconds = int(seconds_str[:-1])
        minutes = seconds // 60
        distance_km = int(distance_meters_str) / 1000

        return minutes, distance_km
    
    def get_commutes_string(self, home_address, work_locations):
        string = "--------------- COMMUTES -----------------\n"
        transport_mode_pretty = {"BICYCLE": "cycle", "DRIVE": "drive", "WALK": "walk", "TRANSIT": "public transport"}
        for destination_location, transport_mode, name, maximum_transport_time in work_locations:
            minutes_to_travel, _ = self.get_travel_time_and_distance(home_address, destination_location, transport_mode)

            padded_person_name = self.pad_string(f"{name}:", 9)
            padded_transport_mode = self.pad_string(f"({transport_mode_pretty[transport_mode]}):", 20)

            if minutes_to_travel <= maximum_transport_time:
                string += f"{padded_person_name}Home -> Work {padded_transport_mode} {minutes_to_travel} minutes\n"
            else:
                extra_minutes = minutes_to_travel - maximum_transport_time
                transport_mode_verb = {"BICYCLE": "cycling", "DRIVE": "driving", "WALK": "walking", "TRANSIT": "on public transport"}
                string += f"{padded_person_name}Home -> Work {padded_transport_mode} {minutes_to_travel} minutes ({extra_minutes} extra minutes {transport_mode_verb[transport_mode]})\n"
            
        string += "\n"
        
        return string
    
    def get_nearest_shops_string(self, home_address):
        string = "--------------- NEAREST SHOPS -----------------\n"
        shops = self.get_places(f"Shops and supermarkets near {home_address}")
        max_shop_name_length = max(len(shop['displayName']['text']) for shop in shops[:5])

        shops_to_print = []
        for shop in shops[:5]:
            minutes_to_walk, distance_km = self.get_travel_time_and_distance(home_address, shop["formattedAddress"], "WALK")
            shops_to_print.append((shop['displayName']['text'], minutes_to_walk, distance_km))

        shops_to_print.sort(key=lambda x: x[1])

        for shop_name, minutes_to_walk, distance_km in shops_to_print:
            padded_shop_name = self.pad_string(shop_name + ":", max_shop_name_length + 1)
            string += f"{padded_shop_name}{minutes_to_walk:>3} minutes ({distance_km:.1f}km)\n"
        
        string += "\n"

        return string
    
    def get_google_maps_link(self, address):
        address = address.replace(" ", "+")
        return f"https://www.google.com/maps/search/{address}"
    
    def scout_location(self, new_house_address, work_locations, price_per_month, link):
        string = ""
        string += "-------------- ADDRESS ------------------\n"
        string += new_house_address + "\n"
        string += "\n"
        string += "Google Maps: " + self.get_google_maps_link(new_house_address) + "\n"
        string += "Rightmove: " + link + "\n"
        string += "\n"
        string += "-------------- PRICE PER MONTH ------------------\n"
        string += "Price per month: " + str(price_per_month) + "\n"
        string += "\n"
        string += self.get_commutes_string(new_house_address, work_locations)
        string += self.get_nearest_shops_string(new_house_address)
        string += "\n"
        string += "\n"
        return string
    
    @staticmethod
    def pad_string(string, length):
        return string + " " * (length - len(string)) if len(string) < length else string

def main():
    # add argument for new address
    parser = argparse.ArgumentParser()
    parser.add_argument("--specific-address", type=str, required=False)
    args = parser.parse_args()

    load_dotenv()
    api_key = os.getenv("GOOGLE_HOUSE_HUNT_API_KEY")
    assert api_key is not None, "GOOGLE_HOUSE_HUNT_API_KEY is not set"
    api = GoogleApi(api_key)

    pdt_address = "119, 121 Cannon St, London EC4N 5AT"
    imperial_address = "Exhibition Rd, South Kensington, London SW7 2AZ"
    symbolica_address = "66 City Rd, London EC1Y 1BD"

    work_locations = [
        (pdt_address, "TRANSIT", "Robbie", 30),
        (imperial_address, "BICYCLE", "Otto", 30),
        (imperial_address, "TRANSIT", "Otto", 30),
        (symbolica_address, "BICYCLE", "Charlie", 30),
        (symbolica_address, "TRANSIT", "Charlie", 30)
    ]

    if args.specific_address:
        scouted_location = api.scout_location(args.specific_address, work_locations, -1, "???")
        print(scouted_location)
    else:
        # Retrieve the last day of emails from the email client
        client = EmailClient("otto.white.apps@gmail.com")
        messages = client.get_recent_messages(1)
        properties = extract_properties_from_messages(messages, client)
        seen_addresses = set()

		# Scout each location on a rightmove email
        scouted_locations = ""
        for address, price_per_month, link in properties:
            if address in seen_addresses:
                continue
            seen_addresses.add(address)

            scouted_locations += api.scout_location(address, work_locations, price_per_month, link)

        todays_date = datetime.now().strftime("%m/%d")
        client.send_email_multiple_recipients(
            ["otto.white20@imperial.ac.uk", "charlie.lidbury@icloud.com"],
            f"Potential new houses {todays_date}",
            scouted_locations)


if __name__ == "__main__":
    main()