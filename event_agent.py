import os
import requests
from datetime import datetime

TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY")

def fetch_nearby_events(city, start_date, end_date, size=5):
    """
    Fetch top events near the specified city within the date range.
    
    :param city: string, name of the city
    :param start_date: 'YYYY-MM-DD'
    :param end_date: 'YYYY-MM-DD'
    :param size: number of events to return
    :return: list of event dictionaries
    """

    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        "apikey": TICKETMASTER_API_KEY,
        "city": city,
        "startDateTime": f"{start_date}T00:00:00Z",
        "endDateTime": f"{end_date}T23:59:59Z",
        "size": size,
        "sort": "date,asc",
    }

    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        data = res.json()

        events = []
        for event in data.get('_embedded', {}).get('events', []):
            events.append({
                "name": event['name'],
                "url": event['url'],
                "start_time": event['dates']['start'].get('dateTime', 'N/A'),
                "venue": event['_embedded']['venues'][0]['name'],
                "location": event['_embedded']['venues'][0]['city']['name'],
            })

        return events

    except Exception as e:
        print(f"[EventAgent] Error fetching events: {e}")
        return []