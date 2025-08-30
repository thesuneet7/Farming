# main.py

import sys
sys.dont_write_bytecode = True

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd

# Import tools from all three files
from agri_weather import get_agri_weather_forecast
from dealer_tool import get_available_markets, get_dealers_for_market
from mandi_tool import get_mandi_prices_today

app = FastAPI(
    title="AI Farming Agent Tools",
    description="An MCP-compatible server providing tools for agricultural analysis.",
    version="1.0.0",
)

# --- Health Check Endpoint ---
@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "AI Farming Agent Tools Server is running."}

# --- Weather Tool Endpoint ---
@app.get("/get_agri_weather_forecast", tags=["Farming Tools"])
def agri_weather_endpoint(district: str, crop_name: str):
    # This block MUST be indented
    try:
        result = get_agri_weather_forecast(district=district, crop_name=crop_name)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

# --- Seed Dealer Tool Endpoints ---
@app.get("/get_available_markets", tags=["Farming Tools"])
async def available_markets_endpoint(state: str, district: str):
    # This block MUST be indented
    try:
        markets = await get_available_markets(state_name=state, district_name=district)
        if not markets:
            raise HTTPException(status_code=404, detail="No markets found or failed to retrieve list.")
        return {"markets": markets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")


@app.get("/get_dealers_for_market", tags=["Farming Tools"])
async def dealers_for_market_endpoint(state: str, district: str, market: str):
    # This block MUST be indented
    try:
        df = await get_dealers_for_market(state_name=state, district_name=district, market_name=market)
        if df.empty:
            return JSONResponse(content={"data": [], "message": "No dealer data found for this market."}, status_code=200)
        
        # Convert DataFrame to JSON for the API response
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

# --- Mandi Price Tool Endpoint ---
@app.get("/get_mandi_prices_today", tags=["Farming Tools"])
def mandi_prices_endpoint(state: str, district: str):
    # This block MUST be indented
    try:
        result = get_mandi_prices_today(state=state, district=district)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")