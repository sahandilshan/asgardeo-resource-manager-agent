# tools/api_spec_assistant.py
import json
from typing import Type, Dict, Any
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers.json import SimpleJsonOutputParser
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr # Use PrivateAttr for non-validated fields

# Keep the prompt template as defined before
PROMPT_TEMPLATE = """
You are an expert API assistant...
Your task is to analyze the provided OpenAPI specification (in JSON format) and identify the exact details needed to perform a specific action described by the user.

ACTION DESCRIPTION:
{action_description}

OPENAPI SPECIFICATION (JSON format):
```json
{spec_json_string}
```

Based ONLY on the provided specification and the action description, determine the following:

The required HTTP method (e.g., "GET", "POST", "PUT", "DELETE").
The relative API path (e.g., "/applications", "/users/{{userId}}"). Do NOT include any server or base URL. If path parameters exist (like {{userId}}), include them in the path string exactly as they appear in the spec.
A list of required query parameter names as defined in the spec's 'parameters' section (where in='query' and required=true), if any. Return an empty list if none.
A list of required path parameter names as defined in the spec's 'parameters' section (where in='path' and required=true), if any. Return an empty list if none.
A concise JSON schema description of the expected request body for POST/PUT/PATCH requests, if applicable and defined in the spec's 'requestBody'. Return null if not applicable or not defined.
Respond ONLY with a valid JSON object containing the keys: "method", "path", "query_params", "path_params", "request_body_schema".
Do not add any explanations, introductory text, or markdown formatting around the JSON.

Example Input Action: "list available applications"
Example Output:
{{
"method": "GET",
"path": "/api/server/v1/applications",
"query_params": [],
"path_params": [],
"request_body_schema": null
}}

Example Input Action: "get details for application with id 12345"
Example Output:
{{
"method": "GET",
"path": "/api/server/v1/applications/{{applicationId}}",
"query_params": [],
"path_params": ["applicationId"],
"request_body_schema": null
}}

Example Input Action: "create a new SAML application"
Example Output:
{{
"method": "POST",
"path": "/api/server/v1/applications",
"query_params": [],
"path_params": [],
"request_body_schema": {{ "description": "Details for the new SAML application including name, description, templateId.", "type": "object" }}
}}

If you cannot confidently determine a single, specific API call from the spec for the given action, respond ONLY with the following JSON:
{{ "error": "Could not determine specific API call for the action from the provided spec." }}
"""

# Define the input schema for the Tool
class ApiAssistantInput(BaseModel):
    action_description: str = Field(description="The natural language description of the specific action to find API details for (e.g., 'list applications', 'get details for application ID 123').")

# Define the Tool class
class ApiAssistantTool(BaseTool):
    """Tool to find API details (method, path, params) for a specific action based on an OpenAPI spec."""
    name: str = "api_spec_assistant"
    description: str = (
        "Useful for determining the correct HTTP method, relative API path, query parameters, "
        "path parameters, and request body schema needed to perform a specific action described in natural language. "
        "Input should be a clear description of the single action (e.g., 'find how to list applications', 'get details for a specific user'). "
        "It analyzes the relevant OpenAPI specification."
    )
    args_schema: Type[BaseModel] = ApiAssistantInput

    # Use PrivateAttr for attributes that are part of the tool's state but not its input schema
    _llm: BaseLanguageModel = PrivateAttr()
    _raw_spec: Dict[str, Any] = PrivateAttr()

    # Custom initialization to pass LLM and spec
    def __init__(self, llm: BaseLanguageModel, raw_spec: Dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        self._llm = llm
        self._raw_spec = raw_spec

    def _run(
        self,
        action_description: str,
        # run_manager: Optional[CallbackManagerForToolRun] = None, # Optional arg
    ) -> str:
        """Use the tool."""
        print(f"\nAssistant Tool: Finding API details for action: '{action_description}'")
        try:
            # Serialize spec - handle potential errors
            try:
                spec_json_string = json.dumps(self._raw_spec, indent=2)
            except TypeError as te:
                print(f"Warning: Spec contains non-serializable elements: {te}. Trying simple conversion.")
                spec_json_string = json.dumps(str(self._raw_spec)) # Fallback

            prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
            parser = SimpleJsonOutputParser()
            chain = prompt | self._llm | parser

            api_details = chain.invoke({
                "action_description": action_description,
                "spec_json_string": spec_json_string
            })

            print(f"Assistant Tool: Received API details from LLM: {api_details}")
            # Validation or error checking on api_details can be added here

            # Return the result as a JSON string for the agent
            return json.dumps(api_details)

        except json.JSONDecodeError as e:
            print(f"Assistant Tool: Error parsing LLM response as JSON: {e}")
            return json.dumps({"error": "Failed to parse LLM response as JSON."})
        except Exception as e:
            print(f"Assistant Tool: An unexpected error occurred: {e}")
            return json.dumps({"error": f"An unexpected error occurred in API assistant tool: {str(e)}"})

    async def _arun(self, action_description: str) -> str:
        # Simple async wrapper for now
        # For true async, need async LLM call and potentially async spec processing
        return self._run(action_description=action_description)

# --- Remove the old function if desired, or keep for direct testing ---
# def get_api_details_for_action(...)

def get_api_details_for_action(action_description: str, raw_spec: dict, llm: BaseLanguageModel) -> dict:
    """
    Uses an LLM to find API details (method, path, params) for a given action
    based on a raw OpenAPI spec dictionary.

    Args:
        action_description: Natural language description of the task.
        raw_spec: The raw OpenAPI specification as a Python dictionary.
        llm: The initialized LangChain language model instance.

    Returns:
        A dictionary containing API details or an error.
    """
    print(f"Assistant: Finding API details for action: '{action_description}'")
    try:
        # Serialize the spec dict to a JSON string for the prompt
        # Handle potential serialization errors if the spec has complex objects
        try:
             spec_json_string = json.dumps(raw_spec, indent=2)
        except TypeError as te:
             print(f"Warning: Spec contains non-serializable elements: {te}. Trying simple conversion.")
             # Fallback or more robust serialization might be needed
             spec_json_string = json.dumps(str(raw_spec))


        prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
        # Using SimpleJsonOutputParser to attempt direct JSON parsing
        # Note: More robust JSON parsing might be needed if LLM output is inconsistent
        parser = SimpleJsonOutputParser()
        chain = prompt | llm | parser

        # Invoke the LLM chain
        api_details = chain.invoke({
            "action_description": action_description,
            "spec_json_string": spec_json_string
        })

        print(f"Assistant: Received API details from LLM: {api_details}")
        # Basic validation (can be expanded)
        if not isinstance(api_details, dict):
             raise ValueError("LLM response was not parsed into a dictionary.")
        if "error" in api_details:
             print(f"Assistant: LLM indicated an error: {api_details['error']}")
             return api_details # Return the error dict as is
        if not all(k in api_details for k in ["method", "path", "query_params", "path_params", "request_body_schema"]):
             print("Warning: LLM response missing required keys. Attempting to use anyway.")
             # Consider raising an error or returning a standard error format here

        return api_details

    except json.JSONDecodeError as e:
        print(f"Assistant: Error parsing LLM response as JSON: {e}")
        # This might happen if the LLM doesn't follow instructions perfectly
        # You might want to return the raw response or implement retries
        return {"error": f"Failed to parse LLM response as JSON."}
    except Exception as e:
        print(f"Assistant: An unexpected error occurred: {e}")
        return {"error": f"An unexpected error occurred in API assistant: {str(e)}"}
