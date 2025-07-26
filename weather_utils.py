import requests
import os

def get_weather(city):
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        raise ValueError("WEATHER_API_KEY not set")

    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        return None

    data = response.json()
    weather = {
        "description": data["weather"][0]["description"].capitalize(),
        "temperature": data["main"]["temp"],
        "feels_like": data["main"]["feels_like"],
        "humidity": data["main"]["humidity"]
    }
    return weather
