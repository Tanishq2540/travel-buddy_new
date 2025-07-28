from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os
from dotenv import load_dotenv
import markdown
from place_extract import extract_candidate_places, validate_places_with_maps_api
from weather_utils import get_weather


load_dotenv()


gcp_api_key = os.getenv("GCP_API_KEY")
gemini_api_key = os.getenv("GEMINI_API_KEY")
weather_api_key = os.getenv("WEATHER_API_KEY")

if not gcp_api_key:
    raise ValueError("GCP_API_KEY not found.")
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY not found.")
if not weather_api_key:
    raise ValueError("WEATHER_API_KEY not found.")

genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

app = Flask(__name__)
app.config["GCP_API_KEY"] = gcp_api_key
app.config["GEMINI_API_KEY"] = gemini_api_key
app.config["WEATHER_API_KEY"] = weather_api_key
@app.route("/", methods=["GET"])
def index():
    
    return render_template("index.html", plan=None, city=None, places=[], api_key=app.config['GCP_API_KEY'])

@app.route("/generate-plan", methods=["POST"])
def generate_plan():
    weather_summary = ""
    if request.is_json:
        data = request.get_json()
        city = data.get("city")
        date = data.get("date")
        budget= data.get("budget")
        preferences = data.get("preferences", [])
        pace= data.get("pace")
        weather = get_weather(city)
        if weather:
            weather_summary = (
                f"\nThe weather forecast for {city} is as follows:\n"
                f"- Condition: {weather['description']}\n"
                f"- Temperature: {weather['temperature']}°C (feels like {weather['feels_like']}°C)\n"
                f"- Humidity: {weather['humidity']}%\n\n"
            )
    else:
        city = request.form.get("city")
        date = request.form.get("date")
        budget = request.form.get("budget", "medium")
        pace = request.form.get("pace", "medium")

        preferences = request.form.getlist("preferences")  

    preference_text = ", ".join(preferences) if preferences else "general sightseeing"

    prompt = f"""
    You're an AI travel planner.

    Create a **detailed 1-day itinerary** for a trip to **{city}** on **{date}**, keeping in mind:
    - **Budget**: {budget}
    - **User preferences**: {", ".join(preferences) if preferences else "general sightseeing"}
    - **Preferred pace**: {pace} day (e.g., relaxing, medium, or hectic)

    {weather_summary}

    Your response must include:
    - A short introduction and projected weather summary
    - Timings for each activity
    - Recommended places to visit (historical, cultural, nature, etc.)
    - Local food/restaurant suggestions (preferably near the attractions)
    - Approximate cost estimates for:
        - Entry tickets
        - Meals
        - Local transport
    - A total estimated cost at the end

    Make sure all activities align with the **weather**, **budget**, and **day pace**.
    Avoid overly generic suggestions. Prioritize realistic, local experiences.
    """



    response = model.generate_content(prompt)
    plan = response.text
    raw_places = extract_candidate_places(plan)
    places = validate_places_with_maps_api(raw_places, city)
    html_plan = markdown.markdown(plan, extensions=["extra", "nl2br"])

    if request.is_json:
        return jsonify({"plan": html_plan}) 
    else:
        print(f"DEBUG: Key being used is: {app.config['GCP_API_KEY']}") 
        return render_template("index.html", plan=html_plan, city=city, places=places or [], api_key=app.config['GCP_API_KEY'])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
