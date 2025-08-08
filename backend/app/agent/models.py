from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class WeatherRequest(BaseModel):
    query: str
    user_id: Optional[str] = None

class WeatherDay(BaseModel):
    date: str
    max_temp: float
    min_temp: float
    precipitation: float
    wind_speed: float

class WeatherResponse(BaseModel):
    success: bool
    location: str
    start_date: str
    end_date: str
    weather_data: List[WeatherDay]
    summary: str
    raw_query: str

class ErrorResponse(BaseModel):
    success: bool
    error: str
    details: Optional[str] = None


class ToolSchema(BaseModel):
    parameters: Dict[str, Any]
