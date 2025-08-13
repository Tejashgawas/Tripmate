from app.core.llm_client import get_ai_completion
from app.schemas.itineraries.itinerary import ItineraryDayPreview, ActivityPreview,ItineraryPreviewResponse
from datetime import date, timedelta, datetime
from typing import List
import json
from app.core.logger import logger
import re

def build_prompt(location: str, days: int, start_date: date) -> str:
    return (
        f"Plan a {days}-day travel itinerary for a {location} trip, starting from {start_date}.\n"
        f"For each day, provide 3-4 activities. Each activity should include:\n"
        f"- A specific time in HH:MM format (optional, but include if logical).\n"
        f"- A concise title.\n"
        f"- A short description.\n\n"
        
        f"Output the entire itinerary as a single **JSON array**, where each element represents a day. "
        f"Each day object must include:\n"
        f"- 'day_number': Integer (e.g., 1, 2...)\n"
        f"- 'title': Title for the day\n"
        f"- 'description': Summary of the day\n"
        f"- 'date': Date in YYYY-MM-DD format\n"
        f"- 'Activity': A list of activity objects, each containing:\n"
        f"   - 'time': in 'HH:MM' format (optional)\n"
        f"   - 'title': string\n"
        f"   - 'description': string\n\n"

        f"Sample activity object:\n"
        f"{{\n"
        f'  "time": "09:30",\n'
        f'  "title": "Visit Eiffel Tower",\n'
        f'  "description": "Explore the iconic landmark and enjoy city views."\n'
        f"}}\n\n"

        f"Sample day object:\n"
        f"{{\n"
        f'  "day_number": 1,\n'
        f'  "title": "Arrival & Exploring Landmarks",\n'
        f'  "description": "Kickstart your trip with sightseeing and local cuisine.",\n'
        f'  "date": "{start_date}",\n'
        f'  "Activity": [\n'
        f"    {{\n"
        f'      "time": "09:30",\n'
        f'      "title": "Breakfast at Café de Flore",\n'
        f'      "description": "Enjoy a French breakfast in a classic Parisian café."\n'
        f"    }},\n"
        f"    {{\n"
        f'      "time": "11:00",\n'
        f'      "title": "Louvre Museum Tour",\n'
        f'      "description": "Explore famous artworks including the Mona Lisa."\n'
        f"    }}\n"
        f"  ]\n"
        f"}}\n\n"
    )

def extract_json_string(raw_text: str):
    # Remove markdown-style code block
    if raw_text.strip().startswith("```json"):
        cleaned = re.sub(r"^```json", "", raw_text.strip())
        cleaned = re.sub(r"```$", "", cleaned.strip())
        return cleaned.strip()
    return raw_text.strip()

def parse_ai_response(response: str, start_date: date) -> List[ItineraryDayPreview]:
    try:
        json_str = extract_json_string(response)
        parsed = json.loads(json_str)
    except json.JSONDecodeError:
        raise ValueError("❌ LLM returned an invalid JSON.")
    
    # logger.info(f"✅ Parsed JSON successfully: {parsed}")


    result = []

    for day in parsed:
        activities = []
        for act in day.get("Activity", []):
            act_time = None
            if act.get("time"):
                try:
                    act_time = datetime.strptime(act["time"], "%H:%M").time()
                except ValueError:
                    pass  # If time is invalid, keep it None

            activities.append(ActivityPreview(
                time=act_time,
                title=act.get("title", "").strip(),
                description=act.get("description", "").strip()
            ))

        result.append(ItineraryDayPreview(
            day_number=day["day_number"],
            title=day["title"],
            description=day.get("description", ""),
            date=datetime.strptime(day["date"], "%Y-%m-%d").date(),
            activities=activities
        ))

    return result