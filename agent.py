# agent.py
# --- Imports ---
# Use the tools agent constructor
from langchain.agents import AgentExecutor, create_openai_tools_agent
# Prompting utilities might change slightly
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
# Import the Azure LLM class
from langchain_openai import AzureChatOpenAI


import config
from typing import List, Dict, Any

from tools.tools import get_context_tools


# --- LLM Initialization (remains the same) ---
def get_llm():
    """Initializes and returns the Langchain AzureChatOpenAI instance based on config."""
    if not all([config.AZURE_OPENAI_API_KEY, config.AZURE_OPENAI_ENDPOINT, config.AZURE_OPENAI_DEPLOYMENT_NAME, config.AZURE_OPENAI_API_VERSION]):
         raise ValueError("Azure OpenAI environment variables are missing.")
    # Ensure the deployment used supports tool/function calling
    return AzureChatOpenAI(
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
        api_key=config.AZURE_OPENAI_API_KEY,
        azure_deployment=config.AZURE_OPENAI_DEPLOYMENT_NAME, # MUST support tool calling
        openai_api_version=config.AZURE_OPENAI_API_VERSION,
        temperature=0,
        max_retries=2,
    )


# --- AGENT RUNNER (CONTEXT VERSION) ---
def run_agent_with_context(user_query: str, chat_history: List[Dict[str, str]]) -> str:
    """
    Sets up and runs the Asgardeo agent, relying on context variables for API key and org name.
    """
    print(f"\n--- Setting up Agent (Context Aware) ---")

    llm = get_llm()
    tools = get_context_tools() # Get tools that use context

    # --- Define the Agent Prompt ---
    system_prompt = """You are a helpful assistant designed to manage Asgardeo resources for a specific organization context.
You have access to tools application management.
Determine the correct tool and arguments based on the user's request."""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"), # Just the user query now
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    # --- Create the Agent and Executor ---
    agent = create_openai_tools_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
    )

    # --- Prepare history and input ---
    formatted_history = []
    for msg in chat_history:
        if msg["role"] == "user": formatted_history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "agent": formatted_history.append(AIMessage(content=msg["content"]))

    # Input is now just the user query, as key/org are handled by context
    agent_input = {
        "input": user_query,
        "chat_history": formatted_history,
    }

    # --- Invoke the executor ---
    print(f"--- Invoking Agent (Context Aware) ---")
    try:
        response = agent_executor.invoke(agent_input)
        final_answer = response.get("output", "I couldn't determine a final answer.")
        print(f"Agent Final Answer: {final_answer}")
        return final_answer
    except Exception as e:
        # Retrieve context for error message if possible (be careful here)
        org_name_for_error = "unknown"
        try:
             from context import get_request_org_name
             org_name_for_error = get_request_org_name()
        except Exception:
             pass
        print(f"Error during agent execution (context method) for org '{org_name_for_error}': {e}")
        # Log traceback here
        return f"An error occurred while processing your request: {e}"
