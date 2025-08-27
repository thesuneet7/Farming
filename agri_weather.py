# agri_weather.py

import os
import requests
import numpy as np
import pandas as pd
import json
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()
OWM_API_KEY = os.getenv("OWM_API_KEY")

def get_agri_weather_forecast(district: str, crop_name: str) -> List[Dict[str, Any]]:
    """
    Provides a 16-day agricultural weather forecast, analysis, and crop-specific recommendations.
    """
    if not OWM_API_KEY:
        raise ValueError("OpenWeatherMap API key (OWM_API_KEY) is not set in environment variables.")

    # --- Internal Helper Functions ---

    def get_coords(district_name: str) -> tuple[float, float]:
        url = "http://api.openweathermap.org/geo/1.0/direct"
        params = {"q": district_name, "limit": 1, "appid": OWM_API_KEY}
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        results = resp.json()
        if not results:
            raise ValueError(f"No coordinates found for '{district_name}'")
        return results[0]["lat"], results[0]["lon"]

    def classify_flags(row: pd.Series) -> dict:
        flags = {}
        if row["temp_max"] > 38: flags["heat"] = "🔴 Red (Heat stress)"
        elif row["temp_max"] > 32: flags["heat"] = "🟡 Yellow (Mild stress)"
        else: flags["heat"] = "🟢 Green (Safe)"

        if row["temp_min"] < 5: flags["cold"] = "🔴 Red (Frost risk)"
        elif row["temp_min"] < 10: flags["cold"] = "🟡 Yellow (Chill stress)"
        else: flags["cold"] = "🟢 Green (Safe)"

        if row["aridity_index"] < 0.5: flags["water"] = "🔴 Red (Irrigation needed)"
        elif row["aridity_index"] < 1: flags["water"] = "🟡 Yellow (Monitor)"
        else: flags["water"] = "🟢 Green (Sufficient)"

        if row["wind_gusts"] > 60: flags["wind"] = "🔴 Red (Lodging risk)"
        elif row["wind_gusts"] > 40: flags["wind"] = "🟡 Yellow (Caution)"
        else: flags["wind"] = "🟢 Green (Safe)"
        return flags

    def crop_recommendation(row: pd.Series, crop_rules: dict) -> str:
        recs = []
        rules = crop_rules.get(crop_name.lower())
        if not rules: return f"No knowledge base for '{crop_name}'."

        for rule in rules:
            try:
                if eval(rule["when"], {}, row.to_dict()):
                    recs.append(f"[{rule['severity'].upper()}] {rule['advisory']}")
            except Exception:
                continue
        return " | ".join(recs) if recs else "Conditions favorable."

    # --- Main Logic ---

    try:
        lat, lon = get_coords(district)
    except (requests.RequestException, ValueError) as e:
        return [{"error": str(e)}]

    # Fetch weather data
    url_daily = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                 "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,wind_gusts_10m_max"
                 "&timezone=Asia/Kolkata&forecast_days=16")
    url_hourly = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                  "&hourly=relative_humidity_2m&timezone=Asia/Kolkata&forecast_days=16")

    try:
        daily_resp = requests.get(url_daily, timeout=15)
        daily_resp.raise_for_status()
        daily_data = daily_resp.json().get("daily", {})

        hourly_resp = requests.get(url_hourly, timeout=15)
        hourly_resp.raise_for_status()
        hourly_data = hourly_resp.json().get("hourly", {})
    except requests.RequestException as e:
        return [{"error": f"Failed to fetch weather data: {e}"}]

    # Create DataFrame
    df = pd.DataFrame({
        'date': daily_data.get('time', []),
        'temp_max': daily_data.get('temperature_2m_max', []),
        'temp_min': daily_data.get('temperature_2m_min', []),
        'precip_mm': daily_data.get('precipitation_sum', []),
        'wind_speed': daily_data.get('wind_speed_10m_max', []),
        'wind_gusts': daily_data.get('wind_gusts_10m_max', []),
    })

    if df.empty:
        return [{"error": "Could not construct DataFrame from weather API response."}]

    df2 = pd.DataFrame({'date': hourly_data.get('time', []), 'humidity': hourly_data.get('relative_humidity_2m', [])})
    df2["date"] = pd.to_datetime(df2["date"]).dt.strftime("%Y-%m-%d")
    humidity_daily = df2.groupby("date", as_index=False)["humidity"].mean()
    df = df.merge(humidity_daily, on="date", how="left")
    df['humidity'] = df['humidity'].fillna(method='ffill').fillna(method='bfill')

    # Agricultural Analysis & Recommendations
    df["temp"] = (df["temp_min"] + df["temp_max"]) / 2
    df["et0"] = 0.0023 * (df["temp_max"] - df["temp_min"])**0.5 * (df["temp"] + 17.8)
    df["aridity_index"] = df["precip_mm"] / (df["et0"] + 0.01)
    df["flags"] = df.apply(classify_flags, axis=1)

    # Load crop knowledge base
    try:
        with open("crop_knowledgebase.json", "r", encoding="utf-8") as f:
            kb = json.load(f)
        CROP_RULES = {c["name"]: c["rules"] for c in kb["crops"]}
        for c in kb["crops"]:
            for alias in c.get("aliases", []): CROP_RULES[alias] = c["rules"]
    except FileNotFoundError:
        return [{"error": "crop_knowledgebase.json not found."}]

    df["recommendations"] = df.apply(lambda row: crop_recommendation(row, CROP_RULES), axis=1)

    # --- Final Output Preparation ---
    # This is the key change: we return a clean, focused list of data.
    
    # 1. Select only the most useful columns for the agent
    essential_columns = [
        "date",
        "temp_max",
        "temp_min",
        "precip_mm",
        "humidity",
        "wind_speed",
        "recommendations"
    ]
    # Ensure all essential columns exist before selecting
    existing_cols = [col for col in essential_columns if col in df.columns]
    df_essential = df[existing_cols].copy()

    # 2. Round the numeric values to keep the output clean
    numeric_cols = df_essential.select_dtypes(include=np.number).columns
    df_essential[numeric_cols] = df_essential[numeric_cols].round(1)
    
    # 3. Return the clean data directly as a list of dictionaries
    return df_essential.to_dict(orient='records')