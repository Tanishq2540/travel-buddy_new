import re
import requests
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GCP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None

def extract_candidate_places(plan_text):
    """
    Extracts potential place names from the travel plan using heuristics.
    """
    candidates = set()
    lines = plan_text.split("\n")

    for line in lines:
        if any(kw in line.lower() for kw in ["visit", "explore", "reach", "head to", "stop at", "at", "see"]):
            found = re.findall(r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)', line)
            for name in found:
                cleaned = name.strip()
                if len(cleaned) > 2:
                    candidates.add(cleaned)

    return list(candidates)

def validate_places_with_gemini(place_list, city):
    """
    Uses Gemini to pre-filter the places likely to be real in the given city.
    """
    if not model or not place_list:
        return place_list  # fallback to all

    prompt = f"""
    You're a travel assistant. Given the city "{city}" and a list of place names, identify which ones are actual real-world places of interest located in that city.

    City: {city}
    Places: {', '.join(place_list)}

    Respond with only a comma-separated list of valid place names found in the city.
    """

    try:
        response = model.generate_content(prompt)
        text = response.text if hasattr(response, "text") else ""
        filtered = [p.strip() for p in text.split(",") if p.strip()]
        return list(set(filtered))
    except Exception as e:
        print(f"Gemini validation error: {e}")
        return place_list  # fallback

def validate_places_with_maps_api(place_list, city):
    """
    Validates the places using Google Maps Text Search API.
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

def hybrid_validate_places(plan_text, city, return_all=False):
    # 1. Extract potential place names from the plan_text
    raw_places = extract_candidate_places(plan_text)

    # 2. Validate them using Google Maps / other APIs
    valid_places = []
    for place in raw_places:
        if validate_places_with_gemini(place, city):  # assuming this checks with GMaps
            valid_places.append(place)

    if return_all:
        return valid_places, raw_places
    return valid_places

