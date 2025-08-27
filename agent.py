# agent.py

import requests
import json
from langchain.tools import StructuredTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder # <-- CHANGE #1: New Import
from dotenv import load_dotenv
from langchain.memory import ConversationBufferMemory # <-- CHANGE #2: New Import

load_dotenv()
SERVER_URL = "http://127.0.0.1:8000"

# --- Tool Functions with CORRECTED Signatures ---
# --- CHANGE #3: Functions now accept arguments directly, not as a Pydantic object ---

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
    """CRITICAL FIRST STEP for finding seed dealers. Use this tool to get a list of all available markets or areas within a district that have seed dealer information. The user must choose one market from this list before you can use the 'get_dealers_for_market' tool."""
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

# --- Tool definitions ---
# Now we can remove the explicit `args_schema` as it's inferred from the function's type hints
tools = [
    StructuredTool.from_function(func=get_agri_weather_forecast),
    StructuredTool.from_function(func=get_mandi_prices_today),
    StructuredTool.from_function(func=get_available_markets),
    StructuredTool.from_function(func=get_dealers_for_market),
]

# --- Agent Setup ---
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0)

# --- CHANGE #4: Update the prompt to include a placeholder for chat history ---
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful and conversational farming assistant. You are located in Kanpur, Uttar Pradesh, India. Today's date is August 27, 2025. Be polite and ask for clarifying information if you need it."),
    MessagesPlaceholder(variable_name="chat_history"), # This is where the memory will be injected
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# --- CHANGE #5: Create the memory object ---
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

agent = create_tool_calling_agent(llm, tools, prompt)

# --- CHANGE #6: Initialize the AgentExecutor with memory ---
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True, 
    memory=memory # Add the memory object here
)

# --- CHANGE #7: Update the chat loop to handle history ---
if __name__ == "__main__":
    print("🤖 Farming Assistant Agent is ready. Type 'quit' or 'exit' to end the session.")
    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ["quit", "exit"]:
            print("🤖 Goodbye!")
            break
        
        # The invoke call now implicitly uses the memory object to get history
        result = agent_executor.invoke({"input": user_input})
        
        print(f"🤖 Agent: {result['output']}")