from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os
from dotenv import load_dotenv
import markdown
from place_extract import hybrid_validate_places
from weather_agent import get_weather
from event_agent import fetch_nearby_events
from interest_search_agent import search_interests
import time
import logging
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

gcp_api_key = os.getenv("GCP_API_KEY")
gemini_api_key = os.getenv("GEMINI_API_KEY")
weather_api_key = os.getenv("WEATHER_API_KEY")
ticketmaster_api_key = os.getenv("TICKETMASTER_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

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

    preference_text = ", ".join(preferences) if preferences else "general sightseeing"
    query = f"Things to do in {city} related to {', '.join(preferences)}" if preferences else f"Interesting places to visit in {city}"

    logging.info(f"[Start] Data Received - City: {city}, Date: {date}, Budget: {budget}, Preferences: {preference_text}, Pace: {pace}")

    def fetch_weather():
        t0 = time.time()
        weather = get_weather(city)
        logging.info(f"Weather fetch time: {time.time() - t0:.2f} seconds")
        if weather:
            return (
                f"\nThe weather forecast for {city} is as follows:\n"
                f"- Condition: {weather['description']}\n"
                f"- Temperature: {weather['temperature']}°C (feels like {weather['feels_like']}°C)\n"
                f"- Humidity: {weather['humidity']}%\n\n"
            )
        return ""

    def fetch_events():
        t0 = time.time()
        events = fetch_nearby_events(city, date, date)
        logging.info(f"Events fetch time: {time.time() - t0:.2f} seconds")
        if events:
            summary = "\nNearby events on your date:\n"
            for ev in events[:5]:
                summary += f"- {ev['name']} at {ev['venue']} on {ev['date']}\n"
            return summary + "\n"
        return "\nNo specific events found for this date. Searching interesting things to explore...\n"

    def fetch_interests():
        t0 = time.time()
        results = search_interests(query, city, preferences, date)
        logging.info(f"Interest fetch time: {time.time() - t0:.2f} seconds")
        if results:
            summary = "\nHere are some interesting places or things to explore:\n"
            for r in results[:5]:
                summary += f"- {r}\n"
            return summary
        return ""

    with ThreadPoolExecutor() as executor:
        weather_future = executor.submit(fetch_weather)
        events_future = executor.submit(fetch_events)
        interests_future = executor.submit(fetch_interests)

        weather_summary = weather_future.result()
        event_summary = events_future.result()
        interest_summary = interests_future.result()

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
    logging.info(f"LLM Generation Time: {llm_gen_end - llm_gen_start:.2f} seconds")

    plan = response.text
    html_plan = markdown.markdown(plan, extensions=["extra", "nl2br"])

    map_validate_start = time.time()
    places, raw_places = hybrid_validate_places(plan, city, return_all=True)
    map_validate_end = time.time()
    logging.info(f"Maps validation time: {map_validate_end - map_validate_start:.2f} seconds")

    valid_count = len(places)
    total_count = len(raw_places)
    maps_accuracy = (valid_count / total_count * 100) if total_count else 0
    logging.info(f"Maps API Accuracy for {city}: {maps_accuracy:.2f}% ({valid_count}/{total_count})")

    route_end = time.time()
    logging.info(f"Total Flask Route Response Time: {route_end - route_start:.2f} seconds")

    if request.is_json:
        return jsonify({"plan": html_plan})
    else:
        return render_template("index.html", plan=html_plan, city=city, places=places or [], api_key=app.config["GCP_API_KEY"])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
