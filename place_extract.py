import re
import requests
import os
from dotenv import load_dotenv
load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GCP_API_KEY")

def extract_candidate_places(plan_text):
    """
    Extracts potential place names from the travel plan using heuristics.
    """
    candidates = set()
    lines = plan_text.split("\n")

    for line in lines:
        if any(kw in line.lower() for kw in ["visit", "explore", "reach", "head to", "stop at", "at", "see", ]):
            found = re.findall(r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)', line)
            for name in found:
                cleaned = name.strip()
                if len(cleaned) > 2:
                    candidates.add(cleaned)

    return list(candidates)

def validate_places_with_maps_api(place_list, city):
    """
    Validates the extracted places using Google Maps Text Search API.
    """
    if not GOOGLE_MAPS_API_KEY:
        raise EnvironmentError("Missing GOOGLE_MAPS_API_KEY in environment.")

    valid_places = []
    for place in place_list:
        query = f"{place}, {city}"
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": query,
            "key": GOOGLE_MAPS_API_KEY
        }

        try:
            response = requests.get(url, params=params)
            data = response.json()
            if data.get("status") == "OK" and data.get("results"):
                valid_places.append(place)
        except Exception as e:
            print(f"Error validating '{place}': {e}")

    return valid_places
