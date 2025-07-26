from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os
from dotenv import load_dotenv
import markdown
from place_extract import extract_candidate_places, validate_places_with_maps_api


load_dotenv()


api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")
genai.configure(api_key=api_key)


model = genai.GenerativeModel("gemini-1.5-flash")

app = Flask(__name__)
app.config["GEMINI_API_KEY"] = api_key
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", plan=None, city=None, places=[], api_key=app.config['GEMINI_API_KEY'])

@app.route("/generate-plan", methods=["POST"])
def generate_plan():
    if request.is_json:
        data = request.get_json()
        city = data.get("city")
        date = data.get("date")
        budget= data.get("budget")
        preferences = data.get("preferences", [])
    else:
        city = request.form.get("city")
        date = request.form.get("date")
        budget = request.form.get("budget", "medium")

        preferences = request.form.getlist("preferences")  

    preference_text = ", ".join(preferences) if preferences else "general sightseeing"

    prompt = f"""
    Give me a detailed 1-day travel itinerary for {city} on {date} considering a {budget} budget.
    Include:
    - Timings
    - Places to visit
    - Local food recommendations
    - Estimated cost of each activity (entry tickets, meals, transport)
    Also add a total estimated cost at the end.
    """

    response = model.generate_content(prompt)
    plan = response.text
    raw_places = extract_candidate_places(plan)
    places = validate_places_with_maps_api(raw_places, city)
    html_plan = markdown.markdown(plan, extensions=["extra", "nl2br"])

    if request.is_json:
        return jsonify({"plan": html_plan}) 
    else:
        return render_template("index.html", plan=html_plan, city=city, places=places or [], api_key=app.config['GEMINI_API_KEY'])


if __name__ == "__main__":
    app.run(debug=True)
