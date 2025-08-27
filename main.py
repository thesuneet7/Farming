# main.py

from fastapi import FastAPI, HTTPException
from agri_tool import get_agri_weather_forecast

# Create a FastAPI app instance
app = FastAPI(
    title="AI Farming Agent Tools",
    description="An MCP-compatible server providing tools for agricultural analysis.",
    version="1.0.0",
)

@app.get("/get_agri_weather_forecast", tags=["Farming Tools"])
def agri_weather_endpoint(district: str, crop_name: str):
    """
    Provides a 16-day agricultural forecast for a given district and crop.
    This includes weather data, stress flags, and actionable recommendations.
    """
    try:
        result = get_agri_weather_forecast(district=district, crop_name=crop_name)
        if "error" in result:
            # Handle errors that occurred within the tool function
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        # Handle unexpected server-side errors
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

# A simple root endpoint to check if the server is running
@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "AI Farming Agent Tools Server is running."}