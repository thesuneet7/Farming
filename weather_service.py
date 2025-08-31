# weather_service.py

import os
import requests
import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()
OWM_API_KEY = os.getenv("OWM_API_KEY")

def _get_coords(district_name: str) -> tuple[float, float]:
    """Helper to get coordinates from district name using OpenWeatherMap Geocoding API."""
    if not OWM_API_KEY:
        raise ValueError("OpenWeatherMap API key (OWM_API_KEY) is not set.")

    url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {"q": district_name, "limit": 1, "appid": OWM_API_KEY}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        results = resp.json()
        if not results:
            raise ValueError(f"No coordinates found for '{district_name}'")
        return results[0]["lat"], results[0]["lon"]
    except requests.RequestException as e:
        raise ConnectionError(f"API request failed for geocoding: {e}") from e

def _classify_agri_flags(row: pd.Series) -> dict:
    """Helper to classify weather conditions into general agronomic flags."""
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

def get_weather_data(district: str) -> pd.DataFrame:
    """
    Fetches and processes a 16-day weather forecast for a given district.
    This function is crop-agnostic.
    """
    lat, lon = _get_coords(district)

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
        raise ConnectionError(f"Failed to fetch weather data from API: {e}") from e

    df = pd.DataFrame({
        'date': daily_data.get('time', []),
        'temp_max': daily_data.get('temperature_2m_max', []),
        'temp_min': daily_data.get('temperature_2m_min', []),
        'precip_mm': daily_data.get('precipitation_sum', []),
        'wind_speed': daily_data.get('wind_speed_10m_max', []),
        'wind_gusts': daily_data.get('wind_gusts_10m_max', []),
    })

    if df.empty:
        raise ValueError("Could not construct DataFrame from weather API response.")

    df_humidity = pd.DataFrame({'time': hourly_data.get('time', []), 'humidity': hourly_data.get('relative_humidity_2m', [])})
    df_humidity["date"] = pd.to_datetime(df_humidity["time"]).dt.strftime("%Y-%m-%d")
    humidity_daily = df_humidity.groupby("date", as_index=False)["humidity"].mean()
    df = df.merge(humidity_daily, on="date", how="left")
    df['humidity'] = df['humidity'].fillna(method='ffill').fillna(method='bfill')

    df["temp"] = (df["temp_min"] + df["temp_max"]) / 2
    df["et0"] = 0.0023 * (df["temp_max"] - df["temp_min"])**0.5 * (df["temp"] + 17.8)
    df["aridity_index"] = df["precip_mm"] / (df["et0"] + 0.01)
    df["flags"] = df.apply(_classify_agri_flags, axis=1)

    return df
