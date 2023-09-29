from geopy.geocoders import Nominatim
from src.utils import cached


class OpenStreetAPI():
    def __init__(self, *args, **kwargs):
        self._tool = Nominatim(user_agent="EventAnalizer-GPT")

    @cached(key_func_name="geocode")
    def whereis(self, location: str) -> str:
        """Run query through OpenStreetAPI geocode.
           Return: City, Region, State, County, Zip, Country
        """
        location = self._tool.geocode(location, country_codes="es", exactly_one=True)
        if location:
            return str(location)
        else:
            return "NOT FOUND"
