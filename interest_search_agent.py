import os
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
client = TavilyClient(api_key=TAVILY_API_KEY)

def search_interests(query: str ,city: str, preferences: list, date: str = "") -> list:
    """
    Builds a query from user preferences and searches using Tavily.
    """
    if not city:
        return []


    try:
        response = client.search(query)
        results = response.get("results", [])[:5]
        return [{
            "title": r.get("title", ""),
            "snippet": r.get("content", "").strip(),
            "url": r.get("url", "")
        } for r in results]
    except Exception as e:
        print(f"[InterestSearchAgent] Search failed: {e}")
        return []
