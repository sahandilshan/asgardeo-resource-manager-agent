# tools/api_execution_tool.py
import json
from typing import Type, Optional, Dict, Any # Keep Any for parsed dict flexibility
import requests
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field, ValidationError # Import ValidationError

from config import ASGARDEO_CONFIG

# --- MODIFIED INPUT SCHEMA ---
class ApiExecutionToolInput(BaseModel):
    """Input schema for the ApiExecutionTool."""
    api_call_details_json: str = Field(description='A JSON string containing the API call details (method, path, query_params, path_params, request_body_schema).')

# --- MODIFIED TOOL CLASS ---
class ApiExecutionTool(BaseTool):
    """Tool to execute API requests against a configured Asgardeo endpoint, taking call details as a JSON string."""
    name: str = "asgardeo_api_executor"
    # --- UPDATED DESCRIPTION ---
    description: str = (
        "Executes a specific API call (GET, POST, PUT, DELETE) against the appropriate Asgardeo API endpoint. "
        "Input MUST be a single JSON string containing keys: 'method', 'path' (the full relative path including prefixes like /api/server/v1 or /scim2/v2), 'query_params', 'path_params', 'request_body_schema'. "
        "This JSON string is typically obtained from the 'app_mgt_api_spec_assistant' or 'scim2_api_spec_assistant' tool."
    )
    args_schema: Type[BaseModel] = ApiExecutionToolInput


    # --- MODIFIED _run signature and added parsing ---
    def _run(
        self,
        api_call_details_json: str,  # Takes only the JSON string input
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        print(f"\nExecution Tool: Received Input JSON string: {api_call_details_json}")

        # --- Parse JSON ---
        try:
            call_details = json.loads(api_call_details_json)
            method = call_details.get("method")
            relative_path = call_details.get("path")  # e.g., /api/server/v1/applications or /scim2/v2/Users
            query_params_values = call_details.get("query_params")
            path_params_values = call_details.get("path_params")
            request_body_values = call_details.get("request_body")

            if not method or not relative_path:
                raise ValueError("Parsed JSON details are missing 'method' or 'path'.")
        except json.JSONDecodeError:
            return f"Error: Input was not a valid JSON string: {api_call_details_json}"
        except (KeyError, ValueError) as e:
            return f"Error: Invalid content in JSON details: {e}. Received: {api_call_details_json}"

        # --- Infer Base URL Key based on Path Prefix ---
        api_base_url_key = "base_url"

            # --- Get Base URL and Token using the key ---
        base_url = ASGARDEO_CONFIG.get(api_base_url_key)  # <-- Use the key here
        api_token = ASGARDEO_CONFIG.get("api_token")

        if not api_token: return "Error: Asgardeo API token missing."
        if not base_url: return f"Error: Asgardeo base URL for key '{api_base_url_key}' missing."
        # ---

        print(f"\nExecution Tool: Preparing request...")
        print(f"  Using Base URL ({api_base_url_key}): {base_url}")  # Log which base URL is used
        print(f"  Method: {method}")
        # ... (rest of the print statements) ...

        # Substitute path parameters (logic is the same)
        final_path = relative_path
        if path_params_values:
            try:
                temp_path = relative_path
                for key, value in path_params_values.items():
                    placeholder = f"{{{key}}}"
                    if placeholder in temp_path:
                        temp_path = temp_path.replace(placeholder, str(value))
                    else:
                        print(f"  Warning: Path parameter key '{key}' not found...")
                final_path = temp_path
            except Exception as e:
                return f"Error substituting path parameters: {e}"

        full_url = f"{base_url}{final_path}"
        print(f"  >>> Full URL requested: {full_url}")

        headers = { # Headers remain the same
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        print(f"  >>> Headers Sent: {headers}")

        try:
            response = requests.request(
                method=method.upper(),
                url=full_url,
                headers=headers,
                params=query_params_values, # Use the dictionary of values directly
                json=request_body_values,   # Use the dictionary of values directly
                timeout=30
            )
            # ... rest of response handling and error handling remains the same ...
            print(f"  <<< Status Code Received: {response.status_code}")
            response.raise_for_status()
            try:
                response_data = response.json()
                print(f"Execution Tool: Success. Returning JSON.")
                return json.dumps(response_data, indent=2)
            except json.JSONDecodeError:
                response_text = response.text
                print(f"Execution Tool: Success. Returning Text (non-JSON response).")
                return response_text
        except requests.exceptions.HTTPError as e:
            error_content = e.response.text
            print(f"Execution Tool: HTTP Error {e.response.status_code}: {error_content}")
            return f"API Request Failed: HTTP {e.response.status_code}\n--- Response Body ---\n{error_content}"
        except requests.exceptions.RequestException as e:
            print(f"Execution Tool: Request Exception: {e}")
            return f"API Request Failed: Connection or request error - {e}"
        except Exception as e:
             print(f"Execution Tool: Unexpected error during API call: {e}")
             return f"API Request Failed: Unexpected error - {str(e)}"

    async def _arun(self, api_call_details_json: str) -> str:
        # Async wrapper takes only the single JSON string now
        return self._run(api_call_details_json=api_call_details_json)
