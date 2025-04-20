# main_agent.py
import json
from urllib.parse import urlparse

from langchain_openai import AzureChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.messages import HumanMessage
from langchain_core.prompts import MessagesPlaceholder # Import this for chat history


# Import configuration and tools/helpers
import config
from utils.spec_loader import load_spec_from_url
from tools.api_spec_assistant import ApiAssistantTool # Import the Tool class
from tools.api_execution_tool import ApiExecutionTool

# --- Initialization ---
print("Initializing components for ReAct Agent...")

# 1. Initialize LLM
try:
    llm = AzureChatOpenAI(
        azure_endpoint=config.AZURE_OPENAI_CONFIG["endpoint"],
        api_key=config.AZURE_OPENAI_CONFIG["api_key"],
        api_version=config.AZURE_OPENAI_CONFIG["api_version"],
        azure_deployment=config.AZURE_OPENAI_CONFIG["deployment_name"],
        temperature=0.0, # Keep temperature low for predictable planning
    )
    print("LLM initialized.")
except Exception as e:
    print(f"Error initializing LLM: {e}")
    exit()

# --- Load and Prepare Specs ---
raw_app_mgt_spec = {}
raw_scim2_spec = {}
try:
    # Load App Mgt Spec
    raw_app_mgt_spec = load_spec_from_url(config.ASGARDEO_CONFIG["app_mgt_spec_url"])
    print("App Management Spec loaded.")

    # Load SCIM2 Spec
    raw_scim2_spec = load_spec_from_url(config.ASGARDEO_CONFIG["scim2_spec_url"])
    print("SCIM2 Spec loaded.")

    # --- == SIMPLIFIED SPEC MODIFICATION == ---

    # --- Modify App Mgt Spec ---
    print("\nModifying App Mgt spec in memory...")
    app_mgt_spec = raw_app_mgt_spec # Work on the loaded dict
    app_mgt_prefix = "/api/server/v1" # Define the specific prefix
    print(f"  Using App Mgt prefix: '{app_mgt_prefix}'")

    # Remove servers block (good practice)
    if "servers" in app_mgt_spec: del app_mgt_spec["servers"]

    # Prepend the defined prefix to all paths
    if "paths" in app_mgt_spec:
        original_paths = app_mgt_spec.get("paths", {})
        modified_paths = {}
        for path, path_item in original_paths.items():
            if not path.startswith('/'): path = '/' + path # Ensure leading slash
            new_path_key = f"{app_mgt_prefix}{path}"
            modified_paths[new_path_key] = path_item
        app_mgt_spec["paths"] = modified_paths # Update the spec dict
    print("App Mgt spec modification complete.")
    # --- End App Mgt Modification ---


    # --- Modify SCIM2 Spec ---
    print("\nModifying SCIM2 spec in memory...")
    scim2_spec = raw_scim2_spec # Work on the loaded dict
    scim2_prefix = "/scim2" # Define the specific prefix for SCIM2
    print(f"  Using SCIM2 prefix: '{scim2_prefix}'") # NOTE: Use /scim2/v2 if that's correct for your spec version

    # Remove servers block
    if "servers" in scim2_spec: del scim2_spec["servers"]

    # Prepend the defined prefix to all paths
    if "paths" in scim2_spec:
        original_paths = scim2_spec.get("paths", {})
        modified_paths = {}
        for path, path_item in original_paths.items():
            if not path.startswith('/'): path = '/' + path # Ensure leading slash
            new_path_key = f"{scim2_prefix}{path}" # e.g., /scim2 + /Users
            modified_paths[new_path_key] = path_item
        scim2_spec["paths"] = modified_paths # Update the spec dict
    print("SCIM2 spec modification complete.")
    # --- END SIMPLIFIED SPEC MODIFICATION ---

except Exception as e:
    print(f"Error loading or modifying specs: {e}")
    exit()

# 3. Instantiate Tools
#    Pass the correctly modified specs
try:
    app_mgt_assistant_tool = ApiAssistantTool(
        name="app_mgt_api_spec_assistant",
        description="Useful for determining API details (method, path, params) for Application Management actions (listing apps, creating apps, deleting apps, managing app settings).",
        llm=llm,
        raw_spec=app_mgt_spec # Pass modified App Mgt spec
    )

    scim2_assistant_tool = ApiAssistantTool(
        name="scim2_api_spec_assistant",
        description="Useful for determining API details (method, path, params) for SCIM2 actions (managing Users, Groups, Roles - e.g., listing users, getting user details, creating groups).",
        llm=llm,
        raw_spec=scim2_spec # Pass modified SCIM2 spec
    )

    api_executor_tool = ApiExecutionTool()
    tools = [app_mgt_assistant_tool, scim2_assistant_tool, api_executor_tool]
    print(f"Tools instantiated: {[tool.name for tool in tools]}")
except Exception as e:
    print(f"Error instantiating tools: {e}")
    exit()


# 4. Define the ReAct Agent Prompt Template (Updated for Routing & Executor Input)
react_prompt_template = """
Answer the following questions as best you can. You MUST strictly follow the specified format.

You have access to the following tools:
{tools}

The available tool names are: {tool_names}

Use the following format EXACTLY:

Question: the input question you must answer
Thought: You should always think about what to do step-by-step. Break down complex tasks.
1.  Determine if the request relates to Application Management OR SCIM2 (Users, Groups, Roles).
2.  Choose the correct API assistant tool: 'app_mgt_api_spec_assistant' for applications, 'scim2_api_spec_assistant' for users/groups/roles.
3.  Use the chosen assistant tool to find the API details (method, path including prefix like /api/server/v1 or /scim2, params needed) for the specific action. Input a clear description (e.g., 'find how to list applications', 'find how to list users').
4.  The assistant tool will return a JSON string with details in the Observation.
5.  Use the 'asgardeo_api_executor' tool to make the API call. Its input MUST be the exact JSON string obtained from the assistant tool (passed as the value for the 'api_call_details_json' argument).
6.  If the action requires specific parameter VALUES (like an ID from a name, or data for creation), plan the steps to get that data first (using the tools), then call the executor, ensuring the necessary `query_params`, `path_params`, or `request_body` keys *with their values* are included within the JSON string passed to `api_call_details_json`.
Observation: The result received from the tool (either JSON string from assistant or API response/error from executor).
*** ERROR HANDLING ***
Thought: Check the Observation. If the Observation from 'asgardeo_api_executor' starts with 'API Request Failed:', then the API call failed. Stop planning and provide the error details in the Final Answer.
Final Answer: If an API error occurred, report the failure clearly, mentioning the requested action and including the error details from the Observation. Do not attempt any more Actions.
*** END ERROR HANDLING ***
Thought: (If no error) Analyze the Observation. Decide the next step. If the goal is achieved, formulate the final answer. Otherwise, plan the next Action/Action Input.
Action: The EXACT name of the tool to use (must be one of [{tool_names}]).
Action Input: The input required for the chosen tool. For 'asgardeo_api_executor', provide a JSON containing the single key 'api_call_details_json' where the value is the JSON string from the assistant tool. For 'api_spec_assistant', provide a JSON containing the single key 'action_description' with the text description.
Observation: ...
Thought: I now know the final answer...
Final Answer: The final answer... (be helpful, summarize, confirm actions)

Begin! Remember to check chat history for context.

Previous conversation history:
{chat_history}

Question: {input}
Thought:{agent_scratchpad}
"""

prompt = ChatPromptTemplate.from_template(react_prompt_template)

# 5. Create the ReAct Agent (remains the same)
agent = create_react_agent(llm, tools, prompt)
print("ReAct agent created.")


# 6. Setup Memory for Chat History
# Use ConversationBufferWindowMemory to keep the last K interactions
memory = ConversationBufferWindowMemory(
    k=5,  # Keep the last 5 turns
    memory_key='chat_history',
    input_key='input', # Ensure these keys match placeholders if needed by memory/agent
    output_key='output',
    return_messages=True # Return history as message objects
)

# 7. Create the Agent Executor
# This runs the agent loop, managing tools, memory, and potential errors
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory, # Add memory here
    verbose=True,   # See the agent's thoughts
    handle_parsing_errors="Check your output and make sure it conforms to the expected format.", # Provide guidance on parsing errors
    max_iterations=10 # Prevent runaway loops
)
print("Agent Executor created.")

# --- Interactive Chat Loop ---
print("\n--- Asgardeo ReAct Agent Initialized ---")
print("Ask me questions or give commands related to Asgardeo App Management (e.g., 'List applications', 'Delete app called SubOrgApp01'). Type 'exit' to quit.")

while True:
    try:
        user_query = input("\nYour question/command: ")
        if user_query.lower() == 'exit':
            print("Exiting agent.")
            break
        if not user_query:
            continue

        # Invoke the agent executor with the user input
        # The executor will handle the ReAct loop, tool calls, and memory
        response = agent_executor.invoke({"input": user_query})

        # The response dictionary should contain the 'output' key with the agent's final answer
        print("\nAgent Response:")
        print(response.get('output', 'Agent did not provide a final answer.'))

    except Exception as e:
        # Catch potential errors during agent execution
        print(f"\nAn error occurred during agent execution: {e}")
        # You might want to reset memory or handle specific errors here
    except KeyboardInterrupt:
        print("\nExiting agent.")
        break
