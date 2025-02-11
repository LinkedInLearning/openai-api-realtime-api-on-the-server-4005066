"""
Functions to help get weather information from the Open Meteo API

Functions:
    get_weather_data(lat, lon, location_name, send_callback) - Get weather data from the Open Meteo API

See:
    https://open-meteo.com/
    https://open-meteo.com/en/docs/geocoding-api
"""
import json
from typing import Optional, Any, Callable
import aiohttp
import sys
import os

# Add the server directory to the Python path
server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(server_dir)

# Change from relative to absolute imports
from app.config.settings import (
    DEFAULT_INSTRUCTIONS,
    WEATHER_INSTRUCTIONS
)

async def get_weather_data(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    location_name: Optional[str] = None,
    send_callback: Optional[Callable[[dict], None]] = None
) -> None:
    """
    Get weather information from the Open Meteo API.

    Args:
        lat: The latitude of the location
        lon: The longitude of the location
        location_name: Optional location name to search for instead of coordinates
        send_callback: Callback function to send data back to the API

    Returns:
        None
    """
    print(f"Function called: get_weather_data lat: {lat}, lon: {lon}, location_name: {location_name}")
    
    if send_callback is None:
        print("No callback provided to send data back to API")
        return
        
    try:
        async with aiohttp.ClientSession() as session:
            # If location_name is provided, use geocoding API to get coordinates
            if location_name:
                async with session.get(
                    f"https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": location_name, "count": 1}
                ) as response:
                    geocoding_data = await response.json()

                    if not geocoding_data.get("results"):
                        error_msg = f"Location '{location_name}' not found"
                        print(error_msg)
                        # Create error response event
                        error_event = {
                            "type": "conversation.item.create",
                            "item": {
                                "type": "message",
                                "role": "user",
                                "content": [{
                                    "type": "input_text",
                                    "text": f"Error: {error_msg}"
                                }]
                            }
                        }
                        await send_callback(error_event)
                        return

                    # Override lat and lon even if they are provided
                    location = geocoding_data["results"][0]
                    lat = location["latitude"]
                    lon = location["longitude"]
                    location_name = location.get("name", location_name)

            if lat is None or lon is None:
                error_msg = "Both latitude and longitude are required"
                print(error_msg)
                # Create error response event
                error_event = {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "user",
                        "content": [{
                            "type": "input_text",
                            "text": f"Error: {error_msg}"
                        }]
                    }
                }
                await send_callback(error_event)
                return

            # Get weather data using the coordinates
            async with session.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current_weather": "true",
                    "temperature_unit": "celsius",
                    "timezone": "auto"
                }
            ) as response:
                weather_data = await response.json()
                
                # Add location name to weather data if available
                if location_name:
                    weather_data["location_name"] = location_name

                # Create weather data response event
                weather_event = {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "user",
                        "content": [{
                            "type": "input_text",
                            "text": f"Weather data: {json.dumps(weather_data, indent=2)}"
                        }]
                    }
                }
                await send_callback(weather_event)

                # Request a response with both modalities
                response_event = {
                    "type": "response.create",
                    "response": {
                        "modalities": ["audio", "text"],
                        "instructions": WEATHER_INSTRUCTIONS
                    }
                }
                await send_callback(response_event)

    except Exception as error:
        error_msg = f'Error fetching weather data: {str(error)}'
        print(error_msg)
        # Create error response event
        error_event = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": f"Error: {error_msg}"
                }]
            }
        }
        await send_callback(error_event) 