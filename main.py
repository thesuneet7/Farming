from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import uvicorn
import json
import requests
import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# In a real-world scenario, you would have separate files for these functions.
# For simplicity, we are including them here.

# --- Tool Functions (these are now part of the server logic) ---

def get_mandi_prices_today_data(state: str, district: str):
    """Fetches live mandi prices from a real API."""
    try:
        # This URL and the parameters are just for illustration.
        # You must replace them with the actual API endpoint from data.gov.in.
        OGD_API_KEY = os.getenv("OGD_API_KEY")
        api_url = f"https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d00ac?api-key={OGD_API_KEY}&format=json&filters%5Bstate%5D={state}&filters%5Bdistrict%5D={district}"
        
        response = requests.get(api_url)
        response.raise_for_status()
        
        raw_data = response.json()
        
        parsed_data = []
        for record in raw_data.get("records", []):
            parsed_data.append({
                "commodity": record.get("commodity", "N/A"),
                "min_price": record.get("min_price", "N/A"),
                "max_price": record.get("max_price", "N/A"),
                "market": record.get("market", "N/A"),
                "date": record.get("arrival_date", "N/A")
            })
            
        return {"data": parsed_data}
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from OGD API: {e}")
        return {"error": "Failed to fetch mandi prices."}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"error": "An internal server error occurred."}

def get_agri_weather_forecast_data(district: str, crop_name: str):
    # This is a mock example with detailed daily data.
    return {
        "district": district,
        "crop": crop_name,
        "forecast": [
            {"day": 1, "temp_high": "32", "temp_low": "25", "condition": "Scattered showers", "precipitation_chance": "60%", "recommendation": "Conditions favorable."},
            {"day": 2, "temp_high": "31", "temp_low": "24", "condition": "Partly cloudy", "precipitation_chance": "40%", "recommendation": "Conditions favorable."},
            {"day": 3, "temp_high": "29.9", "temp_low": "25.8", "condition": "Cloudy with chance of rain", "precipitation_chance": "88.4%", "recommendation": "Conditions favorable."},
            {"day": 4, "temp_high": "31.6", "temp_low": "26.1", "condition": "Partly cloudy", "precipitation_chance": "89.5%", "recommendation": "Conditions favorable."},
            {"day": 5, "temp_high": "33.7", "temp_low": "26.8", "condition": "Mostly sunny", "precipitation_chance": "82.6%", "recommendation": "Conditions favorable."},
            {"day": 6, "temp_high": "34.8", "temp_low": "26.8", "condition": "Sunny", "precipitation_chance": "75.7%", "recommendation": "Conditions favorable."},
            {"day": 7, "temp_high": "33.9", "temp_low": "26.5", "condition": "Partly cloudy", "precipitation_chance": "76.8%", "recommendation": "Conditions favorable."},
            {"day": 8, "temp_high": "33.3", "temp_low": "26.4", "condition": "Cloudy with scattered showers", "precipitation_chance": "79.8%", "recommendation": "Conditions favorable."},
            {"day": 9, "temp_high": "33.6", "temp_low": "25.8", "condition": "Mostly sunny", "precipitation_chance": "78%", "recommendation": "Conditions favorable."},
            {"day": 10, "temp_high": "33.7", "temp_low": "26", "condition": "Sunny", "precipitation_chance": "76.2%", "recommendation": "Conditions favorable."},
            {"day": 11, "temp_high": "33.3", "temp_low": "26.1", "condition": "Partly cloudy", "precipitation_chance": "76.2%", "recommendation": "Conditions favorable."},
            {"day": 12, "temp_high": "34.5", "temp_low": "25.5", "condition": "Sunny", "precipitation_chance": "75.3%", "recommendation": "HIGH: Water deficit for puddled rice. Maintain field puddling or irrigate."},
            {"day": 13, "temp_high": "34.5", "temp_low": "26.1", "condition": "Scattered showers", "precipitation_chance": "75.8%", "recommendation": "Conditions favorable."},
            {"day": 14, "temp_high": "31.5", "temp_low": "26.9", "condition": "Cloudy with light rain", "precipitation_chance": "81.2%", "recommendation": "Conditions favorable."},
            {"day": 15, "temp_high": "35.5", "temp_low": "27.1", "condition": "Sunny", "precipitation_chance": "71.5%", "recommendation": "HIGH: Water deficit for puddled rice. Maintain field puddling or irrigate."},
            {"day": 16, "temp_high": "30.9", "temp_low": "25.7", "condition": "Partly cloudy", "precipitation_chance": "82.4%", "recommendation": "Conditions favorable."}
        ]
    }

def get_available_markets_data(state_name: str, district_name: str):
    # This is a mock response, replace with real API call
    return ["Lucknow", "Mohanlalganj", "Gosaiganj"]

def get_dealers_for_market_data(state_name: str, district_name: str, market_name: str):
    # This is a mock response, replace with real API call
    data = {
        "Dealer Name": ["Agro-Tech Seeds", "Green Leaf Supplies", "Farmers' Friend Co."],
        "Location": [f"{market_name}, {district_name}", f"{market_name}, {district_name}", f"{market_name}, {district_name}"],
        "Contact": ["+91-9876543210", "+91-9988776655", "+91-9123456789"],
        "Specialty": ["High-Yield Rice", "Organic Veg Seeds", "Pesticides & Fertilizers"]
    }
    return pd.DataFrame(data)

def get_soil_testing_centers_data(district: Optional[str] = None) -> str:
    """
    Fetches official government soil testing centers.
    """
    url = "https://soilhealth4.dac.gov.in/"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    
    graphql_query = """
    query GetTestCenters($state: String, $district: String) {
      getTestCenters(state: $state, district: $district) {
        name
        address
        email
        STLdetails {
          phone
        }
        district {
          name
        }
        region {
          state {
            name
          }
          district {
            name
          }
          geolocation {
            coordinates
          }
        }
      }
    }
    """

    state_code = "63f600f38cec41e6c9607e6b" # This is the code for Uttar Pradesh
    payload = {
        "operationName": "GetTestCenters",
        "variables": {"state": state_code, "district": district},
        "query": graphql_query,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        if "errors" in data:
            return f"Error from API: {json.dumps(data['errors'])}"

        centers = data.get("data", {}).get("getTestCenters", [])

        if not centers:
            return "[]"

        results: List[Dict[str, Any]] = []
        for center in centers:
            district_info = center.get("district", {})
            district_name = district_info.get("name", "Unknown District") if isinstance(district_info, dict) else str(district_info) if district_info else "Unknown District"

            region_info = center.get("region", {})
            state_name = "N/A"
            region_district_name = "N/A"
            coordinates = "N/A"
            if isinstance(region_info, dict):
                state_info = region_info.get("state", {})
                state_name = state_info.get("name", "N/A") if isinstance(state_info, dict) else "N/A"
                
                region_district_info = region_info.get("district", {})
                region_district_name = region_district_info.get("name", "N/A") if isinstance(region_district_info, dict) else "N/A"

                geolocation = region_info.get("geolocation", {})
                if isinstance(geolocation, dict) and "coordinates" in geolocation:
                    coords = geolocation["coordinates"]
                    if isinstance(coords, list) and len(coords) >= 2:
                        coordinates = f"{coords[1]}, {coords[0]}"

            phone = "N/A"
            if center.get("STLdetails") and center["STLdetails"].get("phone"):
                phone = center["STLdetails"]["phone"]

            results.append(
                {
                    "Center_Name": center.get("name", "N/A"),
                    "District": district_name,
                    "State": state_name,
                    "Email": center.get("email", "N/A"),
                    "Phone": phone,
                    "Address": center.get("address", "N/A"),
                    "Region_District": region_district_name,
                    "Coordinates": coordinates,
                }
            )
        
        if district:
            filtered_results = [
                center for center in results
                if center['District'].lower() == district.lower() or center['Region_District'].lower() == district.lower()
            ]
            return json.dumps(filtered_results)

        return json.dumps(results)
    except Exception as e:
        return f"Error: {e}"

# --- FastAPI App and Endpoints ---
app = FastAPI(
    title="AI Farming Agent Tools",
    description="An MCP-compatible server providing tools for agricultural analysis.",
    version="1.0.0",
)

@app.get("/", tags=["Health Check"])
def read_root():
    return {"status": "AI Farming Agent Tools Server is running."}

@app.get("/get_agri_weather_forecast", tags=["Farming Tools"])
def agri_weather_endpoint(district: str, crop_name: str, days: Optional[int] = 16):
    try:
        result = get_agri_weather_forecast_data(district=district, crop_name=crop_name)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Slice the forecast data to return only the requested number of days
        result["forecast"] = result["forecast"][:days]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

@app.get("/get_available_markets", tags=["Farming Tools"])
def available_markets_endpoint(state: str, district: str):
    try:
        markets = get_available_markets_data(state_name=state, district_name=district)
        if not markets:
            raise HTTPException(status_code=404, detail="No markets found or failed to retrieve list.")
        return {"markets": markets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

@app.get("/get_dealers_for_market", tags=["Farming Tools"])
def dealers_for_market_endpoint(state: str, district: str, market: str):
    try:
        df = get_dealers_for_market_data(state_name=state, district_name=district, market_name=market)
        if df.empty:
            return JSONResponse(content={"data": [], "message": "No dealer data found for this market."}, status_code=200)
        
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

@app.get("/get_mandi_prices_today", tags=["Farming Tools"])
def mandi_prices_endpoint(state: str, district: str):
    try:
        result = get_mandi_prices_today_data(state=state, district=district)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

@app.get("/get_soil_testing_centers", tags=["Farming Tools"])
def soil_testing_endpoint(district: str = None):
    try:
        result = get_soil_testing_centers_data(district=district)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
