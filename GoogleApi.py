import requests
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

    def make_request(self, url, field_mask, data):
        response = requests.post(url, headers=self.headers(field_mask), json=data)
        return response.json()

    def get_places(self, query):
        data = {
            "textQuery": query
        }
        field_mask = "places.displayName,places.formattedAddress"

        return self.make_request(self.places_url, field_mask, data)["places"]

    def get_travel_time_and_distance(self, origin_address, destination_address, transport_mode):
        # Transit is public transport
        assert transport_mode in ["BICYCLE", "DRIVE", "WALK", "TRANSIT"], "Invalid transport mode"

        next_monday_datetime = datetime.now() + timedelta(days=(7 - datetime.now().weekday()))
        next_monday_datetime = next_monday_datetime.replace(hour=8, minute=0, second=0, microsecond=0)
        departure_time = next_monday_datetime.isoformat() + "Z"

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
        field_mask = "routes.duration,routes.distanceMeters"

        response = self.make_request(self.routes_url, field_mask, data)
        seconds_str = response["routes"][0]["duration"]
        distance_meters_str = response["routes"][0]["distanceMeters"]
        # Remove the s from the end and parse to int
        seconds = int(seconds_str[:-1])
        minutes = seconds // 60
        distance_km = int(distance_meters_str) / 1000

        return minutes, distance_km