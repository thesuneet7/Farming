# agent.py

import requests
import json
import os
from typing import Optional, List, Dict, Any
from langchain.tools import StructuredTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from dotenv import load_dotenv
from langchain.memory import ConversationBufferWindowMemory
import datetime

# Load all environment variables from .env file
load_dotenv()

# The base URL of your running MCP Server (FastAPI app)
SERVER_URL = "http://127.0.0.1:8000"


# --- Tool Functions with Descriptions in Docstrings ---

def get_agri_weather_forecast(district: str, crop_name: str) -> str:
    """Use this tool to get a detailed 16-day agricultural weather forecast for a specific district in India. It provides daily temperature, precipitation, humidity, and crop-specific stress warnings. Do NOT use this for current, real-time weather or historical data."""
    try:
        print(f"DEBUG: Calling weather tool for {district}, {crop_name}")
        response = requests.get(f"{SERVER_URL}/get_agri_weather_forecast", params={"district": district, "crop_name": crop_name})
        response.raise_for_status()
        data = response.json()
        
        print(f"DEBUG: Weather response type: {type(data)}")
        
        # Handle the response format properly
        if isinstance(data, list):
            # Weather data comes as a list of daily forecasts
            result = {
                "district": district,
                "crop": crop_name,
                "forecast": data
            }
            print(f"DEBUG: Weather returning dict with {len(data)} forecast items")
            return json.dumps(result)
        elif isinstance(data, dict):
            if "error" in data:
                return json.dumps({"error": data["error"]})
            else:
                return json.dumps(data)
        else:
            return json.dumps({"error": "Unexpected response format"})
    except Exception as e:
        print(f"DEBUG: Weather tool error: {e}")
        return json.dumps({"error": f"Error: {e}"})

def get_mandi_prices_today(state: str, district: str) -> str:
    """Use this tool ONLY for getting official mandi (agricultural market) prices for the CURRENT DAY from government sources in India. It returns a list of commodities with their prices for a given state and district. Do NOT use this for historical prices or future price predictions."""
    try:
        response = requests.get(f"{SERVER_URL}/get_mandi_prices_today", params={"state": state, "district": district})
        response.raise_for_status()
        data = response.json()
        
        # Handle the response format properly
        if isinstance(data, dict):
            if "error" in data:
                return json.dumps({"error": data["error"]})
            elif "data" in data and "summary" in data:
                # Return the data in a format the agent can understand
                return json.dumps({
                    "summary": data["summary"],
                    "prices": data["data"]
                })
            else:
                return json.dumps(data)
        else:
            return json.dumps({"error": "Unexpected response format"})
    except Exception as e:
        return json.dumps({"error": f"Error: {e}"})

def get_available_markets(state: str, district: str) -> str:
    """CRITICAL FIRST STEP for finding seed dealers. Use this to get a list of all available markets or areas within a district that have seed dealer information. The user must choose one market from this list before you can use the 'get_dealers_for_market' tool."""
    try:
        response = requests.get(f"{SERVER_URL}/get_available_markets", params={"state": state, "district": district})
        response.raise_for_status()
        data = response.json()
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Error: {e}"})

def get_dealers_for_market(state: str, district: str, market: str) -> str:
    """FINAL STEP for finding seed dealers. Use this tool ONLY AFTER you have already used 'get_available_markets' and the user has selected a specific market from the list. This retrieves the detailed list of seed dealers for that single, specified market."""
    try:
        response = requests.get(f"{SERVER_URL}/get_dealers_for_market", params={"state": state, "district": district, "market": market})
        response.raise_for_status()
        data = response.json()
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Error: {e}"})

def get_soil_testing_centers(district: str) -> str:
    """Use this tool to find official government soil testing centers or laboratories in a specific district in Uttar Pradesh. For example, if the user asks for 'soil testing labs in Bahraich', you should call this tool with district='Bahraich'."""
    try:
        response = requests.get(f"{SERVER_URL}/get_soil_testing_centers", params={"district": district})
        response.raise_for_status()
        data = response.json()
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Error: {e}"})

# --- Tool definitions using the robust StructuredTool class ---
tools = [
    StructuredTool.from_function(func=get_agri_weather_forecast),
    StructuredTool.from_function(func=get_mandi_prices_today),
    StructuredTool.from_function(func=get_available_markets),
    StructuredTool.from_function(func=get_dealers_for_market),
    StructuredTool.from_function(func=get_soil_testing_centers),
]

# --- Agent Setup ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is not set. Add it to your .env or environment.")

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash-latest",
    temperature=0,
    google_api_key=GOOGLE_API_KEY,
    transport="rest",
)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful farming assistant. When users ask for mandi prices, use the get_mandi_prices_today tool with state="Uttar Pradesh" and the district name. Present the data in a table format."""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

memory = ConversationBufferWindowMemory(
    k=5, 
    memory_key="chat_history", 
    return_messages=True
)

agent = create_tool_calling_agent(llm, tools, prompt)

agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=False, 
    memory=memory
)

if __name__ == "__main__":
    print("🤖 Farming Assistant Agent is ready. Type 'quit' or 'exit' to end the session.")
    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ["quit", "exit"]:
            print("🤖 Goodbye!")
            break
            
        current_date = datetime.date.today().strftime("%B %d, %Y")
        
        # We are no longer using a separate current_date variable in the invoke call.
        # Instead, we are embedding it directly into the user's input string.
        # This prevents the memory-related ValueError.
        try:
            result = agent_executor.invoke({
                "input": f"Current date is {current_date}. User query: {user_input}",
            })
            print(f"🤖 Agent: {result['output']}")
        except Exception as e:
            print(f"🤖 Agent: I encountered an error while processing your request. Please try again.")
            print(f"🤖 Error details: {str(e)}")
            print(f"🤖 Error type: {type(e)}")
            # Continue the loop to allow the user to try again
        