# mandi_tool.py

import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variables
AGMARKNET_API_KEY = os.getenv("AGMARKNET_API_KEY", "579b464db66ec23bdd000001ce8cce7242164a315a8d3069bbb48a27")
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
BASE_URL = "https://api.data.gov.in/resource/"

def get_mandi_prices_today(state: str, district: str) -> dict:
    """
    Fetches mandi price data for the current date for a given state and district.
    Returns a dictionary containing a summary and the data.
    """
    if not AGMARKNET_API_KEY:
        return {"error": "AGMARKNET_API_KEY not found in environment variables."}

    # Automatically get today's date in the required format
    today_str = datetime.now().strftime("%d/%m/%Y")
    
    url = f"{BASE_URL}{RESOURCE_ID}"
    params = {
        "api-key": AGMARKNET_API_KEY,
        "format": "json",
        "limit": 1000, # Fetch a large number of records for the district
        "filters[state]": state,
        "filters[district]": district,
        "filters[arrival_date]": today_str,
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        
        resp_json = response.json()
        data = resp_json.get("records", [])

        if not data:
            return {
                "summary": f"No mandi price data found for {district}, {state} on {today_str}.",
                "data": []
            }

        df = pd.DataFrame(data)
        
        # Clean and rename columns
        df = df.rename(columns={
            "market": "Market",
            "commodity": "Commodity",
            "variety": "Variety",
            "arrival_date": "Date",
            "min_price": "MinPrice",
            "max_price": "MaxPrice",
            "modal_price": "ModalPrice"
        })

        # Select and reorder essential columns
        df = df[["Market", "Commodity", "Variety", "Date", "MinPrice", "MaxPrice", "ModalPrice"]]
        
        # Convert price columns to numeric, coercing errors
        for col in ["MinPrice", "MaxPrice", "ModalPrice"]:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Create a summary for the LLM
        summary = (
            f"Found {len(df)} records for {district}, {state} on {today_str}. "
            f"Prices range from ₹{df['MinPrice'].min()} to ₹{df['MaxPrice'].max()}. "
            f"Data covers {df['Market'].nunique()} markets and {df['Commodity'].nunique()} commodities."
        )

        return {
            "summary": summary,
            "data": df.to_dict(orient="records")
        }

    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}