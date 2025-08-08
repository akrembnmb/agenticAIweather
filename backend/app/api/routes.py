from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from ..agent.weather_agent import WeatherAgent
from ..agent.models import WeatherRequest, WeatherResponse

router = APIRouter()

def get_weather_agent():
    from ..main import weather_agent
    if not weather_agent:
        raise HTTPException(status_code=503, detail="Weather agent not initialized")
    return weather_agent

@router.get("/")
async def root():
    """Root endpoint with server information."""
    from ..main import weather_agent
    return {
        "name": "Weather Agent MCP Server",
        "version": "1.0.0",
        "description": "Natural language weather forecasting service",
        "capabilities": ["weather_forecast", "location_search", "date_parsing"],
        "available_tools": [tool.name for tool in weather_agent.tools] if weather_agent else []
    }

@router.get("/tools")
async def list_tools(agent: WeatherAgent = Depends(get_weather_agent)):
    """List available MCP tools."""
    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description
            } for tool in agent.tools
        ]
    }

@router.post("/weather", response_model=WeatherResponse)
async def get_weather_forecast(request: WeatherRequest, agent: WeatherAgent = Depends(get_weather_agent)):
    """Get weather forecast using natural language query."""
    try:
        return await agent.process_weather_request(request.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/coordinates")
async def get_location_coordinates(place: str, agent: WeatherAgent = Depends(get_weather_agent)):
    """Get coordinates for a location."""
    try:
        lat, lon = await agent.get_coordinates(place)
        return {
            "place": place,
            "latitude": lat,
            "longitude": lon,
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/parse-date")
async def parse_date_expression(expression: str, agent: WeatherAgent = Depends(get_weather_agent)):
    """Parse a natural language date expression."""
    try:
        iso_date = agent.resolve_relative_date(expression)
        return {
            "expression": expression,
            "iso_date": iso_date,
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    from ..main import weather_agent
    return {
        "status": "healthy",
        "agent_ready": weather_agent is not None,
        "timestamp": datetime.now().isoformat()
    }