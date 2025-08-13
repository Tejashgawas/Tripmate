
from typing import Dict, Any, List, Optional
from app.core.logger import logging

# Mapping Functions
class HotelBookingMapper:
    @staticmethod
    def extract_destination_params(raw_response: Dict[str, Any], index: int = 0) -> Dict[str, str]:
        """
        Quick utility to extract dest_id and dest_type for API calls
        Returns the first result by default, or specify index
        """
        try:
            data = raw_response.get("data", [])
            if not data or index >= len(data):
                return {"dest_id": "", "dest_type": ""}
            
            item = data[index]
            return {
                "dest_id": str(item.get("dest_id", "")),
                "dest_type": item.get("dest_type", "")
            }
            
        except Exception as e:
            logging.error(f"Error extracting destination params: {str(e)}")
            return {"dest_id": "", "dest_type": ""}
    
    @staticmethod
    def get_location_options(raw_response: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Returns simplified list of location options for frontend dropdown/selection
        """
        try:
            options = []
            for item in raw_response.get("data", []):
                options.append({
                    "dest_id": str(item.get("dest_id", "")),
                    "dest_type": item.get("dest_type", ""),
                    "display_name": item.get("value", ""),
                    "label": item.get("label", ""),
                    "country": item.get("cc1", "").upper(),
                    "hotels_count": item.get("nr_hotels", 0),
                    "homes_count": item.get("nr_homes", 0)
                })
            return options
            
        except Exception as e:
            logging.error(f"Error getting location options: {str(e)}")
            return []

