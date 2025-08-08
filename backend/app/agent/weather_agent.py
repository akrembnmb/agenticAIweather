import logging
import requests
import json
import re
from typing import Dict, List, Tuple
from fastapi import HTTPException
from datetime import date
from .models import WeatherDay, WeatherResponse
from .tools import MCPTool
from .utils import resolve_relative_date

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"

class WeatherAgent:
    """Weather Agent class that handles weather forecast requests using natural language processing."""
    
    def __init__(self, groq_api_key: str):
        self.groq_api_key = groq_api_key
        self.groq_url = GROQ_URL
        self.nominatim_url = NOMINATIM_URL
        self.weather_api_url = WEATHER_API_URL
        
        # Define tools with method references and input schemas
        self.tools = [
            MCPTool(
                name="process_weather_request",
                description="Get weather forecast for a location and date range using natural language",
                method=self.process_weather_request,
                input_schema={"query": {"type": "string"}}
            ),
            MCPTool(
                name="get_coordinates",
                description="Get latitude and longitude coordinates for a location",
                method=self.get_coordinates,
                input_schema={"place": {"type": "string"}}
            ),
            MCPTool(
                name="parse_date_expression",
                description="Parse natural language date expressions into ISO format",
                method=self.extract_place_and_date,
                input_schema={"user_question": {"type": "string"}}
            )
        ]
        
        logger.info("WeatherAgent initialized successfully with %d tools", len(self.tools))

    async def get_coordinates(self, place: str) -> Tuple[float, float]:
        """Get latitude and longitude coordinates for a given place."""
        logger.info(f"📍 Getting coordinates for: {place}")
        
        try:
            response = requests.get(self.nominatim_url, params={
                "q": place,
                "format": "jsonv2"
            }, headers={
                "User-Agent": "WeatherAgent/1.0 (fastapi-mcp@example.com)"
            }, timeout=50)

            if response.status_code == 200 and response.json():
                data = response.json()[0]
                lat = float(data['lat'])
                lon = float(data['lon'])
                logger.info(f"✅ Coordinates found: lat={lat}, lon={lon}")
                return lat, lon
            else:
                raise Exception(f"No coordinates found for {place}")
                
        except Exception as e:
            logger.error(f"❌ Error getting coordinates: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Could not find coordinates for {place}")

    async def get_weather_data(self, lat: float, lon: float, start_date: str, end_date: str) -> List[WeatherDay]:
        """Fetch weather data from Open-Meteo API."""
        logger.info(f"🌍 Fetching weather for {start_date} to {end_date} at coordinates: lat={lat}, lon={lon}")
        
        try:
            response = requests.get(self.weather_api_url, params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
                "timezone": "auto",
                "start_date": start_date,
                "end_date": end_date
            }, timeout=50)

            if response.status_code == 200:
                data = response.json()["daily"]
                
                weather_days = []
                dates = data.get("time", [])
                
                for i in range(len(dates)):
                    weather_day = WeatherDay(
                        date=dates[i],
                        max_temp=data['temperature_2m_max'][i],
                        min_temp=data['temperature_2m_min'][i],
                        precipitation=data['precipitation_sum'][i],
                        wind_speed=data['windspeed_10m_max'][i]
                    )
                    weather_days.append(weather_day)
                
                logger.info("✅ Weather forecast retrieved successfully")
                return weather_days
            else:
                raise Exception(f"Weather API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Weather API error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch weather data")

    async def query_groq_llm(self, messages: List[Dict[str, str]]) -> str:
        """Send request to Groq LLM and get response."""
        logger.info("🤖 Sending request to Groq LLM")
        
        try:
            response = requests.post(self.groq_url, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.groq_api_key}"
            }, json={
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 2048
            }, timeout=60)

            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                logger.info("✅ LLM Response received")
                return content
            else:
                raise Exception(f"GROQ API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"❌ GROQ LLM error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to process with LLM")

    async def extract_place_and_date(self, user_question: str) -> Tuple[str, str, str]:
        """Extract location and date range from user question using LLM."""
        logger.info("🧠 Extracting location and date expressions using LLM")

        today = date.today()
        messages = [
            {"role": "system", "content": (
                f"You are a date and location extraction assistant. Today's date is {today}. "
                "Extract the location and time information from weather questions. "
                "For date ranges, identify both start and end dates. "
                "Return ONLY a valid JSON object with this exact structure:\n"
                "{\n"
                "  \"place\": \"location name\",\n"
                "  \"start_date_expr\": \"date expression\",\n"
                "  \"end_date_expr\": \"date expression\",\n"
                "  \"is_range\": true/false\n"
                "}\n\n"
                "Rules:\n"
                "- Handle both past and future dates\n"
                "- Max forecasting range is 15 days in the future\n"
                "- Max historical range is 15 days in the past\n"
                "- Do 'month' return empty json  \n "
                "- If only one date/time is mentioned, use it for both start and end\n"
                "- For 'next X days', start = 'today', end = 'in X days'\n"
                "- For 'last X days', start = 'X days ago', end = 'yesterday'\n"
                "- For 'this week', use 'today' to 'next sunday'\n"
                "- For 'last week', use 'last monday' to 'last sunday'\n"
                "- For 'tomorrow', start and end = 'tomorrow'\n"
                "- For 'yesterday', start and end = 'yesterday'\n"
                "- Always include a place, even if you need to infer it\n"
                "- Keep date expressions natural (e.g., '3 days ago', 'yesterday', 'in 2 days')\n"
                "- If the location or date is missing, return an empty JSON\n"
            )},
            {"role": "user", "content": user_question}
        ]

        try:
            reply = await self.query_groq_llm(messages)
            logger.info(f"📤 LLM extracted: {reply}")

            json_match = re.search(r'\{.*\}', reply, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(reply)
            
            place = data.get("place")
            start_expr = data.get("start_date_expr", "today")
            end_expr = data.get("end_date_expr", "today")
            
            if not place:
                raise ValueError("No place extracted")
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to parse LLM response: {e}")
            return "", "", ""
        
        start_date = resolve_relative_date(start_expr)
        end_date = resolve_relative_date(end_expr)
        
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        
        logger.info(f"📅 Resolved dates: {start_date} to {end_date}")
        return place, start_date, end_date

    def _format_weather_summary(self, weather_data: List[WeatherDay]) -> str:
        """Format weather data into a readable summary."""
        if not weather_data:
            return "No weather data available."
        
        if len(weather_data) == 1:
            day = weather_data[0]
            return (f"On {day.date}: High {day.max_temp}°C, Low {day.min_temp}°C, "
                   f"Precipitation {day.precipitation}mm, Wind {day.wind_speed}km/h")
        else:
            summary = f"Weather forecast for {len(weather_data)} days:\n"
            for day in weather_data:
                summary += (f"• {day.date}: {day.max_temp}°C/{day.min_temp}°C, "
                           f"{day.precipitation}mm rain, {day.wind_speed}km/h wind\n")
            return summary.strip()

    async def generate_natural_response(self, user_question: str, place: str, start_date: str, end_date: str, weather_summary: str) -> str:
        """Generate a natural language response using LLM."""
        messages = [
            {"role": "system", "content": (
                "You are a helpful weather assistant. Provide a natural, conversational response "
                "about the weather forecast. Be friendly and include relevant details like whether "
                "it's good weather for outdoor activities, if they should bring an umbrella, etc. "
                "Keep your response concise but informative."
            )},
            {"role": "user", "content": f"User asked: {user_question}"},
            {"role": "assistant", "content": f"Here's the weather forecast for {place} from {start_date} to {end_date}:\n{weather_summary}"},
            {"role": "user", "content": "Please provide a natural, helpful summary of this weather forecast."}
        ]
        
        return await self.query_groq_llm(messages)

    async def process_weather_request(self, query: str) -> WeatherResponse:
        """Main method to process weather requests."""
        logger.info(f"🌤️ Processing weather request: {query}")

        try:
            # Find the appropriate tool
            tool = next((t for t in self.tools if t.name == "parse_date_expression"), None)
            if not tool:
                raise ValueError("No suitable tool found for parsing query")
            
            # Execute parse_date_expression tool
            place, start_date, end_date = await tool.execute(user_question=query)
            logger.info(f"📍 Location: {place}, 📅 Date range: {start_date} to {end_date}")

            # Execute get_coordinates tool
            coord_tool = next((t for t in self.tools if t.name == "get_coordinates"), None)
            if not coord_tool:
                raise ValueError("No suitable tool found for getting coordinates")
            lat, lon = await coord_tool.execute(place=place)

            # Fetch weather data
            weather_data = await self.get_weather_data(lat, lon, start_date, end_date)
            weather_summary = self._format_weather_summary(weather_data)
            natural_summary = await self.generate_natural_response(query, place, start_date, end_date, weather_summary)

            response = WeatherResponse(
                success=True,
                location=place,
                start_date=start_date,
                end_date=end_date,
                weather_data=weather_data,
                summary=natural_summary,
                raw_query=query
            )

            logger.info("✅ Weather request processed successfully")
            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error processing weather request: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to process weather request: {str(e)}")

    async def list_tools(self) -> List[Dict[str, str]]:
        """List available tools and their descriptions."""
        return [{"name": tool.name, "description": tool.description} for tool in self.tools]