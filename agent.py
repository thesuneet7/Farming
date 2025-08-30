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

# Load all environment variables from .env file
load_dotenv()

# The base URL of your running MCP Server (FastAPI app)
SERVER_URL = "http://127.0.0.1:8000"


# --- Tool Functions with Descriptions in Docstrings ---

def get_agri_weather_forecast(district: str, crop_name: str) -> str:
    """Use this tool to get a detailed 16-day agricultural weather forecast for a specific district in India. It provides daily temperature, precipitation, humidity, and crop-specific stress warnings. Do NOT use this for current, real-time weather or historical data."""
    try:
        response = requests.get(f"{SERVER_URL}/get_agri_weather_forecast", params={"district": district, "crop_name": crop_name})
        response.raise_for_status()
        return json.dumps(response.json())
    except Exception as e:
        return f"Error: {e}"

def get_mandi_prices_today(state: str, district: str) -> str:
    """Use this tool ONLY for getting official mandi (agricultural market) prices for the CURRENT DAY from government sources in India. It returns a list of commodities with their prices for a given state and district. Do NOT use this for historical prices or future price predictions."""
    try:
        response = requests.get(f"{SERVER_URL}/get_mandi_prices_today", params={"state": state, "district": district})
        response.raise_for_status()
        return json.dumps(response.json())
    except Exception as e:
        return f"Error: {e}"

def get_available_markets(state: str, district: str) -> str:
    """CRITICAL FIRST STEP for finding seed dealers. Use this to get a list of all available markets or areas within a district that have seed dealer information. The user must choose one market from this list before you can use the 'get_dealers_for_market' tool."""
    try:
        response = requests.get(f"{SERVER_URL}/get_available_markets", params={"state": state, "district": district})
        response.raise_for_status()
        return json.dumps(response.json())
    except Exception as e:
        return f"Error: {e}"

def get_dealers_for_market(state: str, district: str, market: str) -> str:
    """FINAL STEP for finding seed dealers. Use this tool ONLY AFTER you have already used 'get_available_markets' and the user has selected a specific market from the list. This retrieves the detailed list of seed dealers for that single, specified market."""
    try:
        response = requests.get(f"{SERVER_URL}/get_dealers_for_market", params={"state": state, "district": district, "market": market})
        response.raise_for_status()
        return json.dumps(response.json())
    except Exception as e:
        return f"Error: {e}"


# In your agent.py file, replace the whole function with this one.

def get_soil_testing_centers(state_code: str = "63f600f38cec41e6c9607e6b", district: Optional[str] = None) -> str:
    """
    Use this tool to find official government soil testing centers or laboratories in a specific district.
    This tool is pre-configured for Uttar Pradesh. You must provide the district name.
    For example, if the user asks for "soil testing labs in Bahraich", you should call this tool with district='Bahraich'.

    Args:
        district (str): The name of the district in Uttar Pradesh to search for.
    """
    url = "https://soilhealth4.dac.gov.in/"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    
    # Corrected GraphQL query to properly request nested fields
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

    payload = {
        "operationName": "GetTestCenters",
        # Pass the 'district' variable from the function argument
        "variables": {"state": state_code, "district": district},
        "query": graphql_query,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        # Check for GraphQL errors in the response
        if "errors" in data:
            return f"Error from API: {json.dumps(data['errors'])}"

        centers = data.get("data", {}).get("getTestCenters", [])

        if not centers:
            return "[]" # Return an empty JSON list if no centers are found

        results: List[Dict[str, Any]] = []
        for center in centers:
            district_info = center.get("district", {})
            if isinstance(district_info, dict):
                district_name = district_info.get("name", "Unknown District")
            else:
                district_name = str(district_info) if district_info else "Unknown District"

            region_info = center.get("region", {})
            state_name = "N/A"
            region_district_name = "N/A"
            coordinates = "N/A"
            if isinstance(region_info, dict):
                state_info = region_info.get("state", {})
                if isinstance(state_info, dict):
                    state_name = state_info.get("name", "N/A")
                region_district_info = region_info.get("district", {})
                if isinstance(region_district_info, dict):
                    region_district_name = region_district_info.get("name", "N/A")
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
        
        # The API may return all centers for the state, so we filter them here
        if district:
            filtered_results = [
                center for center in results
                if center['District'].lower() == district.lower() or center['Region_District'].lower() == district.lower()
            ]
            return json.dumps(filtered_results)

        return json.dumps(results)
    except Exception as e:
        return f"Error: {e}"

# --- Tool definitions using the robust StructuredTool class ---
# It automatically infers the name, description, and arguments from the function definitions
tools = [
    StructuredTool.from_function(func=get_agri_weather_forecast),
    StructuredTool.from_function(func=get_mandi_prices_today),
    StructuredTool.from_function(func=get_available_markets),
    StructuredTool.from_function(func=get_dealers_for_market),
    StructuredTool.from_function(func=get_soil_testing_centers),
]

# --- Agent Setup ---
# Prefer API key from environment/.env over ADC to avoid DefaultCredentialsError
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is not set. Add it to your .env or environment.")

# Force REST transport to use API key auth (gRPC often requires ADC)
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash-latest",
    temperature=0,
    google_api_key=GOOGLE_API_KEY,
    transport="rest",
)

# The prompt now includes a placeholder for memory
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful and conversational farming assistant. You are located in Kanpur, Uttar Pradesh, India. Today's date is August 28, 2025. When asked for data from a tool, you must present the relevant data clearly. If a user asks for a list of daily data, provide it in a table format."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# The memory object that stores the conversation history
memory = ConversationBufferWindowMemory(k=5, memory_key="chat_history", return_messages=True)

# Create the agent
agent = create_tool_calling_agent(llm, tools, prompt)

# Create the Agent Executor, which runs the agent and its tools
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True, 
    memory=memory # Pass the memory object to the executor
)

# --- Interactive Chat Loop ---
if __name__ == "__main__":
    print("🤖 Farming Assistant Agent is ready. Type 'quit' or 'exit' to end the session.")
    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ["quit", "exit"]:
            print("🤖 Goodbye!")
            break
            
        result = agent_executor.invoke({"input": user_input})
        
        print(f"🤖 Agent: {result['output']}")