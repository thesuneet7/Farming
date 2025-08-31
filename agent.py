# agent.py

import requests
import os
import json
from langchain.tools import StructuredTool
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from dotenv import load_dotenv
from langchain.memory import ConversationBufferWindowMemory
from typing import Optional
import sys
import re

# Load all environment variables from .env file
load_dotenv()

# Get the API key from the environment variables
api_key = os.getenv("GROQ_API_KEY")

# Check if the key was found. If not, print an error and exit.
if not api_key:
    print("❌ Error: GOOGLE_API_KEY not found. Stopping the script.")
      # <--- This is the command to stop the script

# This part of the code will ONLY run if the API key was found
print("✅ API Key loaded successfully. Continuing with the script...")
print(f"The loaded API key is: {api_key}")



# The base URL of your running MCP Server (FastAPI app)
SERVER_URL = "http://127.0.0.1:8000"


# --- Tool Functions with Descriptions in Docstrings ---

# <-- 1. UPDATED THE FUNCTION SIGNATURE AND DOCSTRING -->
def get_agri_weather_forecast(district: str, crop_name: Optional[str] = None) -> str:
    """
    Use this tool to get a 16-day agricultural weather forecast. Providing just a 'district' returns a general weather outlook. Adding the optional 'crop_name' provides detailed, crop-specific advice and stress warnings. Always inform the user that this is a forecast and not guaranteed to be 100% accurate. Always generate the full data and then analyze and return what the user wants. For example they could ask for 10 days forecast - just  generate the whole df and then read the json file and return only the required data
    """
    try:
        params = {"district": district}
        if crop_name:
            params["crop_name"] = crop_name

        response = requests.get(f"{SERVER_URL}/get_agri_weather_forecast", params=params)
        response.raise_for_status()
        return json.dumps(response.json())
    except Exception as e:
        return f"Error: {e}"

def get_mandi_prices_today(state: str, district: str) -> str:
    """Use this tool ONLY for getting official mandi (agricultural market) prices for the CURRENT DAY from government sources in India. It returns a list of commodities with their prices for a given state and district."""
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
    

def _parse_number(value: str, default: float = 0.0) -> float:
    """Extract first number from string, return default if none."""
    if value is None:
        return default
    match = re.search(r"[\d.]+", str(value))
    return float(match.group()) if match else default

def get_personalised_schemes(age: str, gender: Optional[str] = None, land: Optional[str] = None, income: Optional[str] = None) -> str:
    """
    Use this tool to find personalised government schemes for farmers.
    Inputs may include text like '1.5 hectares' or '200000 INR', which will be parsed into numbers.
    """
    try:
        age_num = int(_parse_number(age))
        land_num = _parse_number(land)
        income_num = _parse_number(income)
        gender_clean = gender.lower() if gender else None

        params = {"age": age_num, "gender": gender_clean, "land": land_num, "income": income_num}
        response = requests.get(f"{SERVER_URL}/get_personalised_schemes", params=params)
        response.raise_for_status()
        return json.dumps(response.json(), ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"

# --- Tool definitions using the robust StructuredTool class ---
# It automatically infers the name, description, and arguments from the function definitions
tools = [
    StructuredTool.from_function(func=get_agri_weather_forecast),
    StructuredTool.from_function(func=get_mandi_prices_today),
    StructuredTool.from_function(func=get_available_markets),
    StructuredTool.from_function(func=get_dealers_for_market),
    StructuredTool.from_function(func=get_personalised_schemes),
]

# --- Agent Setup ---
# --- Agent Setup ---
# --- Agent Setup ---
llm = ChatGroq(   # keep key in .env
    model="meta-llama/llama-4-scout-17b-16e-instruct",              # Groq model name for Llama 4 Scout
    temperature=0
)


# The prompt now includes a placeholder for memory
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful and conversational farming assistant. When asked for data from a tool, you must present the relevant data clearly. If a user asks for a list of daily data, provide it in a table format, with a short summary explanation. The user might also not always give inputs in that case just chat normally with it."),
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