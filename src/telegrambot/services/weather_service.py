import os
import aiohttp
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self, api_key_file: str):
        try:
            with open(api_key_file, 'r') as f:
                self.api_key = f.read().strip()
            logger.debug(f"Initialized WeatherService with API key from {api_key_file}")
        except Exception as e:
            logger.error(f"Failed to read API key from {api_key_file}: {e}")
            self.api_key = None

        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.weather_emoji_map = {
            # Clear
            "01d": "☀️",  # clear sky (day)
            "01n": "🌙",  # clear sky (night)
            # Clouds
            "02d": "⛅️",  # few clouds (day)
            "02n": "☁️",  # few clouds (night)
            "03d": "☁️",  # scattered clouds
            "03n": "☁️",  # scattered clouds (night)
            "04d": "☁️",  # broken clouds
            "04n": "☁️",  # broken clouds (night)
            # Rain
            "09d": "🌧️",  # shower rain
            "09n": "🌧️",  # shower rain (night)
            "10d": "🌦️",  # rain (day)
            "10n": "🌧️",  # rain (night)
            # Thunderstorm
            "11d": "⛈️",  # thunderstorm
            "11n": "⛈️",  # thunderstorm (night)
            # Snow
            "13d": "🌨️",  # snow
            "13n": "🌨️",  # snow (night)
            # Mist/Fog/etc
            "50d": "🌫️",  # mist
            "50n": "🌫️",  # mist (night)
        }
        
        self.wind_speed_emoji = "💨"
        self.humidity_emoji = "💧"
        self.temperature_emoji = "🌡️"
        self.feels_like_emoji = "🤔"
        
        # Add time-based emojis
        self.time_emoji_map = {
            "morning": "🌅",
            "afternoon": "☀️",
            "evening": "🌆",
            "night": "🌙"
        }

    def celsius_to_fahrenheit(self, celsius):
        return (celsius * 9/5) + 32

    def fahrenheit_to_celsius(self, fahrenheit):
        return (fahrenheit - 32) * 5/9

    def get_time_of_day(self, hour: int) -> str:
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    def format_forecast_data(self, data, units="metric"):
        try:
            formatted_days = {}
            
            for item in data['list']:
                # Convert timestamp to datetime
                dt = datetime.fromtimestamp(item['dt'])
                date_key = dt.strftime('%Y-%m-%d')
                hour = dt.hour
                time_of_day = self.get_time_of_day(hour)
                
                if date_key not in formatted_days:
                    formatted_days[date_key] = {
                        "date": dt.strftime('%A, %B %d'),  # e.g., "Monday, December 11"
                        "periods": []
                    }

                temp_c = item['main']['temp']
                temp_f = self.celsius_to_fahrenheit(temp_c) if units == "metric" else temp_c
                
                weather_icon = item['weather'][0]['icon']
                period_data = {
                    "time": dt.strftime('%H:%M'),
                    "time_emoji": self.time_emoji_map[time_of_day],
                    "weather_emoji": self.weather_emoji_map.get(weather_icon, "❓"),
                    "description": item['weather'][0]['description'],
                    "temperature": {
                        "celsius": round(temp_c, 1),
                        "fahrenheit": round(temp_f, 1)
                    },
                    "humidity": item['main']['humidity'],
                    "wind_speed": item['wind']['speed'],
                    "precipitation": item.get('pop', 0) * 100  # Probability of precipitation
                }
                
                formatted_days[date_key]["periods"].append(period_data)
            
            return {
                "city": data['city']['name'],
                "country": data['city']['country'],
                "days": list(formatted_days.values())
            }
            
        except Exception as e:
            logger.error(f"Error formatting forecast data: {e}")
            raise

    async def get_current_weather(self, location: str, units: str = "metric"):
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/weather"
                # Always get metric units first
                params = {
                    "q": location,
                    "appid": self.api_key,
                    "units": "metric"
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        temp_c = data["main"]["temp"]
                        feels_like_c = data["main"]["feels_like"]
                        temp_f = self.celsius_to_fahrenheit(temp_c)
                        feels_like_f = self.celsius_to_fahrenheit(feels_like_c)
                        
                        return {
                            "temperature": {
                                "celsius": round(temp_c, 1),
                                "fahrenheit": round(temp_f, 1)
                            },
                            "feels_like": {
                                "celsius": round(feels_like_c, 1),
                                "fahrenheit": round(feels_like_f, 1)
                            },
                            "humidity": data["main"]["humidity"],
                            "wind_speed": data["wind"]["speed"],
                            "description": data["weather"][0]["description"],
                            "icon": data["weather"][0]["icon"],
                            "emoji": self.weather_emoji_map.get(data["weather"][0]["icon"], "❓"),
                            "condition_emojis": {
                                "temp": self.temperature_emoji,
                                "feels_like": self.feels_like_emoji,
                                "humidity": self.humidity_emoji,
                                "wind": self.wind_speed_emoji
                            }
                        }
                    else:
                        error_data = await response.json()
                        raise Exception(f"Weather API error: {error_data['message']}")
                        
        except Exception as e:
            logger.error(f"Error fetching weather: {e}")
            raise

    async def get_forecast(self, location: str, units: str = "metric"):
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/forecast"
                params = {
                    "q": location,
                    "appid": self.api_key,
                    "units": "metric"  # Always get metric and convert as needed
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self.format_forecast_data(data, units)
                    else:
                        error_data = await response.json()
                        raise Exception(f"Weather API error: {error_data['message']}")
                        
        except Exception as e:
            logger.error(f"Error fetching forecast: {e}")
            raise

    async def get_air_quality(self, location: str):
        try:
            # First get coordinates for the location
            async with aiohttp.ClientSession() as session:
                geo_url = f"{self.base_url}/weather"
                params = {
                    "q": location,
                    "appid": self.api_key
                }
                
                async with session.get(geo_url, params=params) as response:
                    if response.status != 200:
                        error_data = await response.json()
                        raise Exception(f"Weather API error: {error_data['message']}")
                        
                    weather_data = await response.json()
                    lat = weather_data["coord"]["lat"]
                    lon = weather_data["coord"]["lon"]
                
                # Now get air quality using coordinates
                air_url = f"{self.base_url}/air_pollution"
                params = {
                    "lat": lat,
                    "lon": lon,
                    "appid": self.api_key
                }
                
                async with session.get(air_url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_data = await response.json()
                        raise Exception(f"Air quality API error: {error_data['message']}")
                        
        except Exception as e:
            logger.error(f"Error fetching air quality: {e}")
            raise
