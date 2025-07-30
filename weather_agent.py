import requests

API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"

def get_weather(city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()

        weather_info = data.get("weather", [{}])[0]
        main_info = data.get("main", {})

        return {
            "description": weather_info.get("description", "No description available"),
            "temperature": main_info.get("temp", "N/A"),
            "feels_like": main_info.get("feels_like", "N/A"),
            "humidity": main_info.get("humidity", "N/A")
        }

    except Exception as e:
        return {
            "description": f"Error fetching weather: {e}",
            "temperature": "N/A",
            "feels_like": "N/A",
            "humidity": "N/A"
        }
