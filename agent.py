# agent.py

import requests
import json
from langchain.agents import Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Load all environment variables
load_dotenv()

# The base URL of your running MCP Server
SERVER_URL = "http://127.0.0.1:8000"

# --- Define the functions that will call your API (No changes here) ---

def get_weather(query: str) -> str:
    """Useful for getting agricultural weather forecasts. The input should be 'district, crop_name'."""
    try:
        district, crop_name = query.split(',')
        district = district.strip()
        crop_name = crop_name.strip()
        response = requests.get(f"{SERVER_URL}/get_agri_weather_forecast", params={"district": district, "crop_name": crop_name})
        response.raise_for_status()
        return json.dumps(response.json())
    except Exception as e:
        return f"Error: {e}"

def get_mandi_prices(query: str) -> str:
    """Useful for getting today's mandi prices. The input should be 'state, district'."""
    try:
        state, district = query.split(',')
        state = state.strip()
        district = district.strip()
        response = requests.get(f"{SERVER_URL}/get_mandi_prices_today", params={"state": state, "district": district})
        response.raise_for_status()
        return json.dumps(response.json())
    except Exception as e:
        return f"Error: {e}"

# --- Create the list of tools for the agent (No changes here) ---

tools = [
    Tool(
        name="get_agri_weather_forecast",
        func=get_weather,
        description="CRITICAL for weather. Use this to get a 16-day agricultural weather forecast, including stress flags and recommendations. Input must be a comma-separated string of 'district, crop_name', for example: 'Kanpur Nagar, Wheat'."
    ),
    Tool(
        name="get_mandi_prices_today",
        func=get_mandi_prices,
        description="CRITICAL for market prices. Use this to get the latest mandi prices for all commodities for the current date. Input must be a comma-separated string of 'state, district', for example: 'Uttar Pradesh, Kanpur Nagar'."
    ),
]

# --- Now, create and run the agent ---

# 1. Agent Setup
# --- THIS IS THE ONLY CHANGE ---
# Switched from "gemini-pro" to "gemini-1.5-flash-latest" for guaranteed free-tier access.
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful farming assistant. You are located in Kanpur, Uttar Pradesh, India."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 2. Run with a user query
if __name__ == "__main__":
    # Make sure your uvicorn server is running first!
    user_input = "What is the price of Mustard in Kanpur today, and are there any weather warnings for sowing it?"
    result = agent_executor.invoke({"input": user_input})
    print("\n--- Final Answer ---")
    print(result["output"])