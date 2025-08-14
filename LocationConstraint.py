def transport_mode_to_pretty(transport_mode: str):
    return {
        "BICYCLE": "cycle",
        "DRIVE": "drive",
        "WALK": "walk",
        "TRANSIT": "public transport"
    }[transport_mode]

def pad_string(string: str, length: int):
    return string + " " * (length - len(string)) if len(string) < length else string

class LocationConstraint:
    def __init__(self, person_name: str, target_name: str, target_address: str, transport_mode: str, max_transport_minutes: int):
        self.person_name = person_name
        self.target_name = target_name
        self.target_address = target_address
        self.transport_mode = transport_mode
        self.max_transport_minutes = max_transport_minutes
    
    def __str__(self):
        pretty_transport_mode = transport_mode_to_pretty(self.transport_mode)
        return f"{self.person_name} -> {self.target_name} ({pretty_transport_mode}) in {self.max_transport_minutes} minutes"
    
class TravelTime:
    def __init__(self, location_constraint: LocationConstraint, minutes: int):
        self.location_constraint = location_constraint
        self.minutes = minutes
    
    def is_violation(self):
        return self.minutes > self.location_constraint.max_transport_minutes

    def __str__(self):
        pretty_transport_mode = transport_mode_to_pretty(self.location_constraint.transport_mode)
        longest_name = len("Charlie")
        longest_target_name = len("Lauren's house")
        longest_transport_mode = len("(public transport)")

        padded_person_name = pad_string(f"{self.location_constraint.person_name}:", longest_name + 1)
        padded_target_name = pad_string(f"{self.location_constraint.target_name}:", longest_target_name + 1)
        padded_transport_mode = pad_string(f"({pretty_transport_mode}):", longest_transport_mode + 1)

        return f"{padded_person_name} -> {padded_target_name} {padded_transport_mode} {self.minutes} minutes"
