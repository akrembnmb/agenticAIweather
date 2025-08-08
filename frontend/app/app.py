import os
import requests
from dash import Dash, html, dcc, Input, Output, callback
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Dash app
app = Dash(__name__, assets_folder='assets')

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Layout
app.layout = html.Div([
    html.H1("Weather Agent", className="header"),
    html.Div([
        dcc.Input(
            id="weather-query",
            type="text",
            placeholder="Enter your weather query (e.g., 'Weather in Paris tomorrow')",
            className="input-box",
            debounce=True
        ),
        html.Button("Get Weather", id="submit-button", n_clicks=0, className="submit-button")
    ], className="input-container"),
    html.Div(id="weather-output", className="output-container")
])

@callback(
    Output("weather-output", "children"),
    Input("submit-button", "n_clicks"),
    Input("weather-query", "value")
)
def update_weather(n_clicks, query):
    """Fetch weather data from backend and display it."""
    if n_clicks == 0 or not query:
        return html.P("Enter a query and click 'Get Weather' to see the forecast.", className="info-text")
    
    logger.info(f"Sending query to backend: {query}")
    try:
        response = requests.post(f"{BACKEND_URL}/weather", json={"query": query}, timeout=50)
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                return html.Div([
                    html.H3(f"Weather for {data['location']} ({data['start_date']} to {data['end_date']})"),
                    html.P(data["summary"], className="summary-text"),
                    html.Ul([
                        html.Li(f"{day['date']}: High {day['max_temp']}°C, Low {day['min_temp']}°C, "
                                f"Precipitation {day['precipitation']}mm, Wind {day['wind_speed']}km/h")
                        for day in data["weather_data"]
                    ], className="weather-list")
                ], className="weather-data")
            else:
                return html.P(f"Error: {data.get('error', 'Unknown error')}", className="error-text")
        else:
            return html.P(f"Failed to fetch weather data, your request may not contain a valid location or date", className="error-text")
    except Exception as e:
        logger.error(f"Error fetching weather: {str(e)}")
        return html.P(f"Error: {str(e)}", className="error-text")

if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=True)