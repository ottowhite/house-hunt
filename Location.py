import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Location:
    def __init__(self, google_api, address, price_per_month, property_link):
        self.google_api = google_api
        self.address = address
        self.price_per_month = price_per_month
        self.property_link = property_link

    def scout(self, work_locations):
        self.scout_commutes(work_locations)
        self.scout_nearest_shops()

    def scout_commutes(self, work_locations):
        self.commutes = []
        self.total_commute_time = 0

        for destination_location, transport_mode, name, maximum_transport_time in work_locations:
            minutes_to_travel, _ = self.google_api.get_travel_time_and_distance(self.address, destination_location, transport_mode)

            self.commutes.append((name, transport_mode, minutes_to_travel, maximum_transport_time))
            self.total_commute_time += minutes_to_travel

    def scout_nearest_shops(self):
        places = self.google_api.get_places(f"Shops and supermarkets near {self.address}")

        self.shops = []
        for shop in places[:5]:
            minutes_to_walk, distance_km = self.google_api.get_travel_time_and_distance(self.address, shop["formattedAddress"], "WALK")
            self.shops.append((shop['displayName']['text'], minutes_to_walk, distance_km))

        self.shops.sort(key=lambda x: x[1])

    def violates_criteria(self):
        for name, transport_mode, minutes_to_travel, maximum_transport_time in self.commutes:
            if minutes_to_travel > maximum_transport_time:
                return True

        return False

    def __str__(self):
        string = ""
        string += "-------------- ADDRESS ------------------\n"
        string += "\n"
        string += self.address + "\n"
        string += "\n"
        string += "-------------- GOOGLE MAPS ------------------\n"
        string += "\n"
        string += self.get_google_maps_link() + "\n"
        string += "\n"
        string += "-------------- RIGHTMOVE ------------------\n"
        string += "\n"
        string += self.property_link + "\n"
        string += "\n"
        string += "-------------- PRICE PER MONTH ------------------\n"
        string += "\n"
        string += "£" + str(self.price_per_month) + "\n"
        string += "\n"
        string += self.get_commutes_string()
        string += "\n"
        string += self.get_nearest_shops_string()

        return string

    def get_google_maps_link(self):
        return f'https://www.google.com/maps/search/{self.address.replace(" ", "+")}'

    @staticmethod
    def pad_string(string, length):
        return string + " " * (length - len(string)) if len(string) < length else string
    
    def get_commutes_string(self):
        string = "--------------- COMMUTES -----------------\n"
        transport_mode_pretty = {"BICYCLE": "cycle", "DRIVE": "drive", "WALK": "walk", "TRANSIT": "public transport"}

        for name, transport_mode, minutes_to_travel, maximum_transport_time in self.commutes:

            padded_person_name = self.pad_string(f"{name}:", 9)
            padded_transport_mode = self.pad_string(f"({transport_mode_pretty[transport_mode]}):", 20)

            string += f"{padded_person_name}Home -> Work {padded_transport_mode} {minutes_to_travel} minutes\n"

        return string

    def get_nearest_shops_string(self):
        string = "--------------- NEAREST SHOPS -----------------\n"
        max_shop_name_length = max(len(shop[0]) for shop in self.shops)

        for shop_name, minutes_to_walk, distance_km in self.shops:
            padded_shop_name = self.pad_string(shop_name + ":", max_shop_name_length + 1)
            string += f"{padded_shop_name}{minutes_to_walk:>3} minutes ({distance_km:.1f}km)\n"

        return string
    
    @staticmethod
    def scout_locations(google_api, work_locations, properties):
        scouted_locations = []
        seen_addresses = set()

        for address, price_per_month, link in properties:
            if address in seen_addresses:
                logger.info(f"Skipping {address} because it has already been processed.")
                continue
            seen_addresses.add(address)
            location = Location(google_api, address, price_per_month, link)
            location.scout(work_locations)
            if not location.violates_criteria():
                logger.info(f"Adding {location.address} to scouted locations")
                scouted_locations.append(location)
            else:
                logger.info(f"Skipping {location.address} because it violates criteria")

        return scouted_locations

    @staticmethod
    def to_big_string(scouted_locations):
        scouted_locations.sort(key=lambda x: x.total_commute_time)
        location_strs = []
        for location in scouted_locations:
            location_strs.append(str(location))

        return "\n\n\n".join(location_strs)


