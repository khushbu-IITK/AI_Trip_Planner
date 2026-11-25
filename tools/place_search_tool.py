import os
import logging
from typing import List

from dotenv import load_dotenv
from langchain_core.tools import tool

from utils.place_info_search import GooglePlaceSearchTool, TavilyPlaceSearchTool

logger = logging.getLogger(__name__)


class PlaceSearchTool:
    """
    Place search with optional providers:
    - Google Places key only  -> Google
    - Tavily key only         -> Tavily
    - Both keys               -> Google first, Tavily as fallback
    - No keys                 -> tools still load, and return a clear message
    """

    # category -> (Google method name, Tavily method name, label for the answer)
    CATEGORIES = {
        "attractions":    ("google_search_attractions",    "tavily_search_attractions",    "attractions"),
        "restaurants":    ("google_search_restaurants",    "tavily_search_restaurants",    "restaurants"),
        "activities":     ("google_search_activity",       "tavily_search_activity",       "activities"),
        "transportation": ("google_search_transportation", "tavily_search_transportation", "transport options"),
    }

    def __init__(self):
        load_dotenv()
        self.google = self._init_google(os.getenv("GPLACES_API_KEY"))
        self.tavily = self._init_tavily(os.getenv("TAVILY_API_KEY"))

        if not self.google and not self.tavily:
            logger.warning("No place search provider configured. Set GPLACES_API_KEY or TAVILY_API_KEY.")

        self.place_search_tool_list = self._setup_tools()

    # ---------- provider setup: only create a client if its key exists ----------

    @staticmethod
    def _init_google(api_key):
        if not api_key:
            logger.info("GPLACES_API_KEY not set: Google Places disabled.")
            return None
        try:
            return GooglePlaceSearchTool(api_key)
        except Exception as e:
            logger.warning("Google Places setup failed (%s): disabled.", type(e).__name__)
            return None

    @staticmethod
    def _init_tavily(api_key):
        if not api_key:
            logger.info("TAVILY_API_KEY not set: Tavily disabled.")
            return None
        return TavilyPlaceSearchTool()  # langchain_tavily reads TAVILY_API_KEY itself

    # ---------- one search routine shared by all 4 tools ----------

    def _search(self, category: str, place: str) -> str:
        google_method, tavily_method, label = self.CATEGORIES[category]

        # 1. Google first, if available
        if self.google:
            try:
                result = getattr(self.google, google_method)(place)
                if result:
                    return f"{label.capitalize()} in {place} (source: Google Places):\n{result}"
                logger.info("Google returned nothing for %s in %s; trying Tavily.", category, place)
            except Exception as e:
                logger.warning("Google failed for %s in %s (%s); trying Tavily.", category, place, type(e).__name__)

        # 2. Tavily: the only provider, or the fallback
        if self.tavily:
            try:
                result = getattr(self.tavily, tavily_method)(place)
                if result:
                    return f"{label.capitalize()} in {place} (source: web search):\n{result}"
            except Exception as e:
                logger.warning("Tavily failed for %s in %s (%s).", category, place, type(e).__name__)

        # 3. Nothing worked: always return a string, never None
        return (f"Could not find {label} for {place} right now. "
                f"Do not invent them; tell the user this information is unavailable.")

    # ---------- the tools the LLM sees ----------

    def _setup_tools(self) -> List:
        @tool
        def search_attractions(place: str) -> str:
            """Find top tourist attractions and sightseeing spots in a place.

            Args:
                place: city or region name, e.g. "Goa" or "Kyoto"
            """
            return self._search("attractions", place)

        @tool
        def search_restaurants(place: str) -> str:
            """Find popular restaurants and places to eat in a place.

            Args:
                place: city or region name, e.g. "Goa" or "Kyoto"
            """
            return self._search("restaurants", place)

        @tool
        def search_activities(place: str) -> str:
            """Find things to do and activities (tours, adventure, nightlife) in a place.

            Args:
                place: city or region name, e.g. "Goa" or "Kyoto"
            """
            return self._search("activities", place)

        @tool
        def search_transportation(place: str) -> str:
            """Find local transport options (metro, buses, taxis, rentals) within a place.

            Args:
                place: city or region name, e.g. "Goa" or "Kyoto"
            """
            return self._search("transportation", place)

        return [search_attractions, search_restaurants, search_activities, search_transportation]