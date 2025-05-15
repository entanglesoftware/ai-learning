import aiohttp
import os
import httpx
from typing import Any
from mcp.server.fastmcp import FastMCP
import asyncio
from dotenv import load_dotenv


load_dotenv()

OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
IPSTACK_API_KEY = os.getenv("IPSTACK_API_KEY")

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
OPENWEATHERMAP_API_BASE = "https://api.openweathermap.org/data/2.5"
USER_AGENT = "weather-app/1.0"

# Helper functions
async def make_openweather_request(url: str) -> dict[str, Any] | None:
    """Make a request to the OpenWeatherMap API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
    }
    url = f"{url}&appid={OPENWEATHERMAP_API_KEY}"  # Append API key to the URL
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            print(f"Response received from {url}: {response.status_code}") 
            return response.json()
        except Exception as e:
            print(f"Error fetching data from {url}: {str(e)}") 
            return None

# Tool: get_weather
@mcp.tool()
async def get_weather(city: str) -> str:
    """Get current weather information for a specific city"""
    url = f"{OPENWEATHERMAP_API_BASE}/weather?q={city}&units=metric"  # Correct endpoint
    data = await make_openweather_request(url)

    if not data:
        return "Unable to fetch weather data for this location."

    main = data.get("main", {})
    weather = data.get("weather", [{}])[0]
    description = weather.get("description", "No description available")
    temperature = main.get("temp", "Unknown")
    humidity = main.get("humidity", "Unknown")
    wind_speed = data.get("wind", {}).get("speed", "Unknown")

    weather_info = f"""
Weather for {city}:
Description: {description}
Temperature: {temperature}°C
Humidity: {humidity}%
Wind Speed: {wind_speed} m/s
"""
    return weather_info

# Tool: get_forecast
@mcp.tool()
async def get_forecast(city: str) -> str:
    """Get 5-day weather forecast for a city."""
    url = f"{OPENWEATHERMAP_API_BASE}/forecast?q={city}&units=metric"  # Correct endpoint
    data = await make_openweather_request(url)

    if not data:
        return "Unable to fetch forecast data for this location."

    forecast_data = []
    for period in data.get("list", [])[:5]:  # Show the next 5 forecast periods
        dt = period.get("dt_txt", "Unknown time")
        temperature = period["main"].get("temp", "Unknown")
        description = period["weather"][0].get("description", "No description available")
        wind_speed = period.get("wind", {}).get("speed", "Unknown")

        forecast = f"""
{dt}:
Description: {description}
Temperature: {temperature}°C
Wind Speed: {wind_speed} m/s
"""
        forecast_data.append(forecast)

    return "\n---\n".join(forecast_data)



# Function to get location data from IP address using ipstack API
async def get_location_from_ip(ip: str) -> dict[str, Any] | None:
    """Get location (latitude, longitude, city, region, country) from IP address."""
    url = f"http://api.ipstack.com/{ip}?access_key={IPSTACK_API_KEY}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching location for IP {ip}: {str(e)}")
            return None

@mcp.tool()
async def get_weather_by_ip(ip: str) -> str:
    """Get weather for a location based on IP address."""
    location_data = await get_location_from_ip(ip)
    if not location_data:
        return "Unable to get location from IP address."

    latitude = location_data.get("latitude")
    longitude = location_data.get("longitude")
    city = location_data.get("city", "Unknown City")
    region = location_data.get("region_name", "")
    country = location_data.get("country_name", "")

    if not latitude or not longitude:
        return "Location information is incomplete."

    # Get weather data
    url = f"{OPENWEATHERMAP_API_BASE}/weather?lat={latitude}&lon={longitude}&units=metric"
    data = await make_openweather_request(url)

    if not data:
        return "Unable to fetch weather data for this location."

    main = data.get("main", {})
    weather = data.get("weather", [{}])[0]
    description = weather.get("description", "No description available")
    temperature = main.get("temp", "Unknown")
    humidity = main.get("humidity", "Unknown")
    wind_speed = data.get("wind", {}).get("speed", "Unknown")

    weather_info = f"""
📍 Weather for {city}, {region}, {country} (IP: {ip}):
🌤️ Description: {description}
🌡️ Temperature: {temperature}°C
💧 Humidity: {humidity}%
💨 Wind Speed: {wind_speed} m/s
"""
    return weather_info


async def make_wine_request(url: str) -> dict:
    """Make an asynchronous request to the Wine API."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()  # Parse the JSON response
    except Exception as e:
        print(f"Error fetching wine data: {e}")
        return None

# Tool: get_wine_info
@mcp.tool()
async def get_wine_info(wine_name: str) -> str:
    """
    Fetch wine details based on the wine name from Crust Aging API.
    """
    url = f"https://uk.crustaging.com/live-markets/api_buyBid/autosuggestionsearch/search?q={wine_name}"

    data = await make_wine_request(url)

    if not data or not isinstance(data, list) or len(data) == 0:
        return "No wine found for the given name."

    wine = data[0]  # Pick the first matching wine suggestion

    name = wine.get("name", "Unknown")
    wine_type = wine.get("type", "Unknown")
    region = wine.get("region", "Unknown")
    price = wine.get("price", "Unknown")
    vintage = wine.get("vintage", "Unknown")
    rating = wine.get("rating", "Not available")

    wine_info = f"""
🍷 Wine Name: {name}
Type: {wine_type}
Region: {region}
Vintage: {vintage}
Price: {price}
Rating: {rating}
"""

    return wine_info

# Start the server
if __name__ == "__main__":
    mcp.run(transport='stdio')

