from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os
from dotenv import load_dotenv
import markdown
from place_extract import extract_candidate_places, validate_places_with_maps_api
from weather_agent import get_weather
from event_agent import fetch_nearby_events
from interest_search_agent import search_interests
import time
import logging

load_dotenv()

gcp_api_key = os.getenv("GCP_API_KEY")
gemini_api_key = os.getenv("GEMINI_API_KEY")
weather_api_key = os.getenv("WEATHER_API_KEY")
ticketmaster_api_key = os.getenv("TICKETMASTER_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

# Validate keys
for key_name, key_val in {
    "GCP_API_KEY": gcp_api_key,
    "GEMINI_API_KEY": gemini_api_key,
    "WEATHER_API_KEY": weather_api_key,
    "TICKETMASTER_API_KEY": ticketmaster_api_key,
    "TAVILY_API_KEY": tavily_api_key
}.items():
    if not key_val:
        raise ValueError(f"{key_name} not found in environment variables.")

genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

app = Flask(__name__)
app.config.update(
    GCP_API_KEY=gcp_api_key,
    GEMINI_API_KEY=gemini_api_key,
    WEATHER_API_KEY=weather_api_key,
    TICKETMASTER_API_KEY=ticketmaster_api_key,
    TAVILY_API_KEY=tavily_api_key
)

logging.basicConfig(filename="metrics.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", plan=None, city=None, places=[], api_key=app.config["GCP_API_KEY"])

@app.route("/generate-plan", methods=["POST"])
def generate_plan():
    route_start = time.time()
    weather_summary = ""
    event_summary = ""
    interest_summary = ""

    data_fetch_start = time.time()
    if request.is_json:
        data = request.get_json()
        city = data.get("city")
        date = data.get("date")
        budget = data.get("budget")
        preferences = data.get("preferences", [])
        pace = data.get("pace")
    else:
        city = request.form.get("city")
        date = request.form.get("date")
        budget = request.form.get("budget", "medium")
        pace = request.form.get("pace", "medium")
        preferences = request.form.getlist("preferences")
    data_fetch_end = time.time()
    logging.info(f"Data fetch time: {data_fetch_end - data_fetch_start:.2f} seconds")

    weather_fetch_start = time.time()
    weather = get_weather(city)
    if weather:
        weather_summary = (
            f"\nThe weather forecast for {city} is as follows:\n"
            f"- Condition: {weather['description']}\n"
            f"- Temperature: {weather['temperature']}°C (feels like {weather['feels_like']}°C)\n"
            f"- Humidity: {weather['humidity']}%\n\n"
        )
    weather_fetch_end = time.time()
    logging.info(f"Weather fetch time: {weather_fetch_end - weather_fetch_start:.2f} seconds")

    event_fetch_start = time.time()
    events = fetch_nearby_events(city, date, date)
    if events:
        event_summary = "\nNearby events on your date:\n"
        for ev in events[:5]:
            event_summary += f"- {ev['name']} at {ev['venue']} on {ev['date']}\n"
        event_summary += "\n"
    else:
        event_summary = "\nNo specific events found for this date. Searching interesting things to explore...\n"
    event_fetch_end = time.time()
    logging.info(f"Event fetch time: {event_fetch_end - event_fetch_start:.2f} seconds")

    interest_fetch_start = time.time()
    if preferences:
        query = f"Things to do in {city} related to {', '.join(preferences)}"
    else:
        query = f"Interesting places to visit in {city}"
    interests = search_interests(query, city, preferences, date)
    if interests:
        interest_summary = "\nHere are some interesting places or things to explore:\n"
        for i in interests[:5]:
            interest_summary += f"- {i}\n"
    interest_fetch_end = time.time()
    logging.info(f"Interest fetch time: {interest_fetch_end - interest_fetch_start:.2f} seconds")

    preference_text = ", ".join(preferences) if preferences else "general sightseeing"
    prompt = f"""
    Plan a 1-day itinerary in **{city}** for **{date}** with:

    - Budget: {budget}
    - Preferences: {preference_text}
    - Pace: {pace}

    Context:
    {weather_summary}
    {event_summary}
    {interest_summary}

    Include:
    - Brief intro with weather
    - Timeline with places to visit
    - Nearby events (if any)
    - Local food suggestions
    - Estimated costs (tickets, food, transport)
    - Total cost at the end
    """



    llm_gen_start = time.time()
    response = model.generate_content(prompt)
    llm_gen_end = time.time()

    plan = response.text
    logging.info(f"LLM Generation Time: {llm_gen_end - llm_gen_start:.2f} seconds")

    place_extract_start = time.time()
    raw_places = extract_candidate_places(plan)
    place_extract_end = time.time()
    logging.info(f"Place extraction time: {place_extract_end - place_extract_start:.2f} seconds")

    validation_start = time.time()
    places = validate_places_with_maps_api(raw_places, city)
    validation_end = time.time()
    logging.info(f"Maps validation time: {validation_end - validation_start:.2f} seconds")

    valid_count = len(places)
    total_count = len(raw_places)
    maps_accuracy = (valid_count / total_count * 100) if total_count else 0
    logging.info(f"Maps API Accuracy for {city}: {maps_accuracy:.2f}% ({valid_count}/{total_count})")

    html_plan = markdown.markdown(plan, extensions=["extra", "nl2br"])

    route_end = time.time()
    logging.info(f"Total Flask Route Response Time: {route_end - route_start:.2f} seconds")

    if request.is_json:
        return jsonify({"plan": html_plan})
    else:
        return render_template("index.html", plan=html_plan, city=city, places=places or [], api_key=app.config["GCP_API_KEY"])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True, use_reloader=False)
