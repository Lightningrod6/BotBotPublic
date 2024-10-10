import requests
import dotenv
import os
from urllib.parse import quote

dotenv.load_dotenv()

def get_city(city, state=None, zipcode=None):
    if state:
        request_url = f'https://geocode.maps.co/search?q={quote(city)},{quote(state)}&api_key={os.getenv("GEOMAPS_API_KEY")}'
    elif zipcode:
        request_url = f'https://geocode.maps.co/search?q={quote(zipcode)}&api_key={os.getenv("GEOMAPS_API_KEY")}'
    else:
        request_url = f'https://geocode.maps.co/search?q={quote(city)}&api_key={os.getenv("GEOMAPS_API_KEY")}'
    
    coord = requests.get(request_url)
    coords = coord.json()
    print(coord.url)
    location = "{},{}".format(coords[0]['lat'], coords[0]['lon'])
    return location  # Format the output as a string
