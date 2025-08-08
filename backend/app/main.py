import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.agent.weather_agent import WeatherAgent
from app.api.routes import router as api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Global agent instance
weather_agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan event handler."""
    global weather_agent
    # Startup
    logger.info("🚀 Starting Weather Agent MCP Server")
    weather_agent = WeatherAgent(GROQ_API_KEY)
    logger.info("✅ Weather Agent initialized")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Weather Agent MCP Server")

# FastAPI app
app = FastAPI(
    title="Weather Agent MCP Server",
    description="A Model Context Protocol server for weather forecasting using natural language",
    version="1.0.0",
    lifespan=lifespan
)

# Include API routes
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 







    