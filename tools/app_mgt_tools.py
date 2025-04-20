# tools.py (showing only the updated list_asgardeo_applications)
import json

from langchain.tools import tool
from typing import Optional, Dict, Any
import time
import config
import requests
# Import the correct function from auth.py


from pydantic import BaseModel, Field # Import Pydantic components
from typing import Optional

from auth import get_asgardeo_access_token
from context import get_request_api_key, get_request_org_name


# --- Define Input Schemas for Tools ---

class ListAppsAgentSchema(BaseModel):
    # No arguments needed from LLM if org name comes from context
    pass

class CreateAppAgentSchema(BaseModel):
    organization_name: str = Field(description="The target Asgardeo organization name.")
    app_name: str = Field(description="The desired name for the new application.")
    template: str = Field("SPA", description="Optional application template type (e.g., 'SPA', 'WebApp', 'Mobile'). Defaults to 'SPA'.")

class DeleteAppAgentSchema(BaseModel):
    organization_name: str = Field(description="The target Asgardeo organization name.")
    app_id: str = Field(description="The unique application ID (not the name) to delete.")

class CreateAppAgentSchema(BaseModel):
    app_name: str = Field(description="The desired name for the new application.")


# --- Tool Definitions ---

# ***** MODIFIED @tool DECORATOR *****
@tool
def list_asgardeo_applications() -> str:
    """
    (Internal Docstring - can mention api_key_b64 here, but the agent won't see this one directly)
    Lists applications registered in the specified Asgardeo organization using Client Credentials.
    """

    """
        Lists applications registered in the Asgardeo organization associated with the current request context.
        """
    # --- Get values from context ---
    try:
        api_key_b64 = get_request_api_key()
        organization_name = get_request_org_name()
        print(f"Executing list_asgardeo_applications (using context) for org: {organization_name}")
    except RuntimeError as e:
        print(f"Context Error: {e}")
        return f"Error: Could not retrieve request context (API Key or Org Name). Detail: {e}"

    # ... function logic remains the same, using api_key_b64 ...
    print(f"Executing list_asgardeo_applications(organization_name={organization_name})")
    api_endpoint = f"{config.ASGARDEO_BASE_URL}{organization_name}/api/server/v1/applications"
    print(f"Targeting Asgardeo API endpoint: {api_endpoint}")
    # ... rest of the logic using api_key_b64 ...
    try:
        access_token = get_asgardeo_access_token(api_key_b64, organization_name)
        print(f"Obtained Access Token (partial): {access_token[:20]}...")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        print(f"Making GET request to {api_endpoint}")
        response = requests.get(api_endpoint, headers=headers)
        response.raise_for_status()

        print(f"API Call Successful (Status Code: {response.status_code})")
        applications_data = response.json()

        if not applications_data:
             return f"No applications found in organization '{organization_name}'."

        app_list = []
        count = 0
        # Adjust parsing based on actual API response
        data_list = applications_data if isinstance(applications_data, list) else applications_data.get('applications', []) # Example handling if data is nested
        total_apps = len(data_list)

        for app in data_list:
            if count >= 10 and total_apps > 10:
                 app_list.append("- ... (and more)")
                 break
            app_id = app.get('id', 'N/A')
            app_name = app.get('name', 'N/A')
            client_id_val = app.get('clientId', 'N/A')
            app_list.append(f"- Name: {app_name} (ID: {app_id}, ClientID: {client_id_val})")
            count += 1

        app_list_str = "\n".join(app_list)
        return f"Found {total_apps} application(s) in organization '{organization_name}':\n{app_list_str}"

    except ValueError as e:
        print(f"Authentication/Token Error in list_asgardeo_applications: {e}")
        return f"Error obtaining authorization token for organization '{organization_name}': {e}. Please check API key and target URL."
    except requests.exceptions.RequestException as e:
        print(f"Network/API Error in list_asgardeo_applications: {e}")
        status_code = e.response.status_code if e.response is not None else "N/A"
        return f"Error communicating with Asgardeo API for organization '{organization_name}' (Status: {status_code}): {e}"
    except requests.exceptions.JSONDecodeError as e:
         print(f"API Response Parsing Error in list_asgardeo_applications: {e}")
         # It might be useful to log response.text here
         return f"Error parsing the response from Asgardeo API for organization '{organization_name}'. The response might not be valid JSON."
    except Exception as e:
        print(f"Unexpected Error in list_asgardeo_applications: {e}")
        # Log traceback here in production
        return f"An unexpected error occurred while listing applications for organization '{organization_name}': {e}"


@tool #(args_schema=DeleteAppAgentSchema) # Add schema if needed for validation by agent framework
# Function signature only takes args the LLM needs to determine
def delete_asgardeo_application(app_id: str) -> str:
    """
    Deletes an existing application registration from the Asgardeo organization
    associated with the current request context, identified by its unique application ID.
    Requires the application ID. This is a destructive action.
    """
    # --- Get values from context ---
    try:
        api_key_b64 = get_request_api_key()
        organization_name = get_request_org_name()
        print(f"Executing delete_asgardeo_application (using context) for org: {organization_name}, App ID: {app_id}")
    except RuntimeError as e:
        print(f"Context Error: {e}")
        return f"Error: Could not retrieve request context (API Key or Org Name). Detail: {e}"

    # Validate app_id (basic check)
    if not app_id or not isinstance(app_id, str):
        return "Error: Invalid or missing application ID provided."

    # --- Construct Endpoint URL ---
    # Ensure no double slashes if base URL ends with /
    api_endpoint = f"{config.ASGARDEO_BASE_URL.rstrip('/')}/{organization_name}/api/server/v1/applications/{app_id}"
    print(f"Targeting Asgardeo DELETE endpoint: {api_endpoint}")

    try:
        # 1. Get Access Token
        access_token = get_asgardeo_access_token(api_key_b64, organization_name)
        print(f"Obtained Access Token (partial): {access_token[:20]}...")

        # 2. Prepare Headers
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json", # Include accept header even for DELETE
            # User-Agent, Referer, Access-Control-Allow-Origin are usually not needed here
        }

        # 3. Make the DELETE Request
        print(f"Making DELETE request to {api_endpoint}")
        response = requests.delete(api_endpoint, headers=headers)

        # 4. Process the Response
        # A successful DELETE often returns 204 No Content
        if response.status_code == 204:
            print(f"API Call Successful (Status Code: {response.status_code} No Content)")
            return f"Successfully deleted application with ID '{app_id}' from organization '{organization_name}'."
        elif 200 <= response.status_code < 300:
             # Handle other potential success codes (e.g., 200 OK with a body)
             print(f"API Call Successful (Status Code: {response.status_code})")
             # You might want to check response.text or response.json() if needed
             return f"Application deletion initiated or confirmed for ID '{app_id}' in organization '{organization_name}' (Status: {response.status_code})."
        else:
            # For non-2xx responses, raise_for_status() will raise an exception caught below
            response.raise_for_status()
            # This line might not be reached if raise_for_status handles all errors
            return f"Received unexpected status code {response.status_code} attempting to delete application ID '{app_id}'."

    except ValueError as e: # Catches errors from get_asgardeo_access_token
        print(f"Authentication/Token Error in delete_asgardeo_application: {e}")
        return f"Error obtaining authorization token for organization '{organization_name}': {e}. Please check API key and target URL."
    except requests.exceptions.HTTPError as e:
        # Specific handling for HTTP errors (4xx, 5xx) raised by raise_for_status()
        status_code = e.response.status_code
        error_message = f"Failed to delete application ID '{app_id}' in organization '{organization_name}'. Status Code: {status_code}."
        try:
            # Try to get more details from the response body
            error_details = e.response.json() # Assumes error response is JSON
            desc = error_details.get('description') or error_details.get('message') or error_details.get('detail')
            if desc:
                error_message += f" Detail: {desc}"
            else:
                 error_message += f" Response: {e.response.text[:200]}" # Fallback to raw text
        except (requests.exceptions.JSONDecodeError, AttributeError):
             error_message += f" Response: {e.response.text[:200]}" # Fallback if not JSON or response missing

        print(f"API HTTP Error in delete_asgardeo_application: {error_message}")
        return error_message # Return a user-friendly error
    except requests.exceptions.RequestException as e:
        # Handle other network errors (connection, timeout, etc.)
        print(f"Network/API Error in delete_asgardeo_application: {e}")
        return f"Error communicating with Asgardeo API for organization '{organization_name}': {e}"
    except Exception as e:
        # Catch any other unexpected errors
        print(f"Unexpected Error in delete_asgardeo_application: {e}")
        # Log the full traceback here in a real application
        return f"An unexpected error occurred while deleting application ID '{app_id}' for organization '{organization_name}': {e}"

@tool (args_schema=CreateAppAgentSchema) # Add schema if needed
# Function signature only takes args the LLM needs to determine
def create_asgardeo_application(app_name: str) -> str:
    """
    Creates a new application registration with default settings in the Asgardeo
    organization associated with the current request context.
    Requires only the desired application name.
    Uses default settings for protocol (OIDC), grant types (Client Credentials), etc.
    """
    # --- Get values from context ---
    try:
        api_key_b64 = get_request_api_key()
        organization_name = get_request_org_name()
        print(f"Executing create_asgardeo_application (using context) for org: {organization_name}, App Name: {app_name}")
    except RuntimeError as e:
        print(f"Context Error: {e}")
        return f"Error: Could not retrieve request context (API Key or Org Name). Detail: {e}"

    # Validate app_name (basic check)
    if not app_name or not isinstance(app_name, str):
        return "Error: Invalid or missing application name provided."

    # --- Construct Endpoint URL ---
    api_endpoint = f"{config.ASGARDEO_BASE_URL.rstrip('/')}/{organization_name}/api/server/v1/applications"
    print(f"Targeting Asgardeo POST endpoint: {api_endpoint}")

    # --- Construct Request Body (JSON Payload) ---
    # Using defaults based on the provided curl command
    # Consider making these defaults configurable if needed later
    payload: Dict[str, Any] = {
      "name": app_name, # Use the provided app_name
      "advancedConfigurations": {
        "skipLogoutConsent": True,
        "skipLoginConsent": True
      },
      "templateId": "custom-application-oidc", # Default template ID from curl
      "associatedRoles": {
        "allowedAudience": "APPLICATION",
        "roles": []
      },
      "inboundProtocolConfiguration": {
        "oidc": {
            # Default grant type from curl - consider if this is always appropriate
          "grantTypes": ["client_credentials"],
          "isFAPIApplication": False
          # Other OIDC settings might be needed depending on template/defaults
        }
      }
      # Add other default fields as required by the Asgardeo API for creation
    }
    print(f"Request Payload: {json.dumps(payload, indent=2)}") # Log the payload being sent

    try:
        # 1. Get Access Token
        access_token = get_asgardeo_access_token(api_key_b64, organization_name)
        print(f"Obtained Access Token (partial): {access_token[:20]}...")

        # 2. Prepare Headers
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json", # Specify content type for POST
        }

        # 3. Make the POST Request
        print(f"Making POST request to {api_endpoint}")
        response = requests.post(api_endpoint, headers=headers, json=payload) # Use json=payload

        # 4. Process the Response
        # A successful CREATE often returns 201 Created
        if response.status_code == 201:
            print(f"API Call Successful (Status Code: {response.status_code} Created)")
            try:
                response_data = response.json()
                # Extract relevant info like the new app ID and confirm name
                new_app_id = response_data.get('id', 'N/A')
                confirmed_app_name = response_data.get('name', app_name)
                return f"Successfully created application '{confirmed_app_name}' with ID '{new_app_id}' in organization '{organization_name}'."
            except requests.exceptions.JSONDecodeError:
                 return f"Successfully created application '{app_name}' in organization '{organization_name}' (Status: 201), but response body was not valid JSON."
        else:
            # For non-201 responses, raise an exception to be caught below
            response.raise_for_status()
            # This line likely won't be reached
            return f"Received unexpected status code {response.status_code} attempting to create application '{app_name}'."

    except ValueError as e: # Catches errors from get_asgardeo_access_token
        print(f"Authentication/Token Error in create_asgardeo_application: {e}")
        return f"Error obtaining authorization token for organization '{organization_name}': {e}. Please check API key and target URL."
    except requests.exceptions.HTTPError as e:
        # Specific handling for HTTP errors (4xx, 5xx)
        status_code = e.response.status_code
        error_message = f"Failed to create application '{app_name}' in organization '{organization_name}'. Status Code: {status_code}."
        try:
            error_details = e.response.json()
            desc = error_details.get('description') or error_details.get('message') or error_details.get('detail')
            if desc: error_message += f" Detail: {desc}"
            else: error_message += f" Response: {e.response.text[:200]}"
        except (requests.exceptions.JSONDecodeError, AttributeError):
             error_message += f" Response: {e.response.text[:200]}"

        print(f"API HTTP Error in create_asgardeo_application: {error_message}")
        return error_message
    except requests.exceptions.RequestException as e:
        # Handle other network errors
        print(f"Network/API Error in create_asgardeo_application: {e}")
        return f"Error communicating with Asgardeo API for organization '{organization_name}': {e}"
    except Exception as e:
        # Catch any other unexpected errors
        print(f"Unexpected Error in create_asgardeo_application: {e}")
        # Log traceback here
        return f"An unexpected error occurred while creating application '{app_name}' for organization '{organization_name}': {e}"

@tool #(args_schema=SearchAppsAgentSchema)
def search_asgardeo_applications(search_term: str) -> str:
    """
    Searches for applications within the Asgardeo organization associated
    with the current request context. Searches the application name,
    client ID, and issuer fields for the provided search term using a 'contains' filter.
    Excludes system applications by default.
    """
    try:
        api_key_b64 = get_request_api_key()
        organization_name = get_request_org_name()
        print(f"Executing search_asgardeo_applications (using context) for org: {organization_name}, Term: '{search_term}'")
    except RuntimeError as e:
        print(f"Context Error: {e}")
        return f"Error: Could not retrieve request context (API Key or Org Name). Detail: {e}"

    if not search_term or not isinstance(search_term, str):
        return "Error: Invalid or missing search term provided."

    api_endpoint = f"{config.ASGARDEO_BASE_URL.rstrip('/')}/{organization_name}/api/server/v1/applications"
    print(f"Targeting Asgardeo GET endpoint: {api_endpoint}")

    # --- Construct Query Parameters ---
    # ***** MODIFIED: Removed explicit quotes around search_term *****
    scim_filter = f'name co {search_term} or clientId co {search_term} or issuer co {search_term}'

    params = {
        "attributes": "advancedConfigurations,templateId,clientId,issuer",
        # ***** MODIFIED: Pass boolean as string *****
        "excludeSystemPortals": "true",
        "filter": scim_filter,
        "limit": 10,
        "offset": 0
    }
    print(f"Query Params before encoding: {params}")

    try:
        access_token = get_asgardeo_access_token(api_key_b64, organization_name)
        print(f"Obtained Access Token (partial): {access_token[:20]}...")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        print(f"Making GET request to {api_endpoint} with search parameters")
        response = requests.get(api_endpoint, headers=headers, params=params) # params handles encoding

        # Add extra debug for 400 errors BEFORE raise_for_status
        if response.status_code == 400:
             print(f"!!! Received 400 Bad Request. URL sent: {response.url}") # Print the exact URL requests built
             print(f"!!! Response Body: {response.text}") # Print the error body from server

        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        print(f"API Call Successful (Status Code: {response.status_code})")
        response_data = response.json()

        total_results = response_data.get('totalResults', 0)
        applications_found = response_data.get('applications', [])

        if not applications_found:
             return f"No applications found matching '{search_term}' in organization '{organization_name}' (excluding system portals)."

        app_list = []
        for app in applications_found:
            app_id = app.get('id', 'N/A')
            app_name = app.get('name', 'N/A')
            client_id_val = app.get('clientId', 'N/A')
            issuer = app.get('issuer', 'N/A')
            app_list.append(f"- Name: {app_name} (ID: {app_id}, ClientID: {client_id_val}, Issuer: {issuer})")

        app_list_str = "\n".join(app_list)
        result_summary = f"Found {total_results} application(s) matching '{search_term}' in organization '{organization_name}'."
        if total_results > len(applications_found):
             result_summary += f" Showing first {len(applications_found)}."

        return f"{result_summary}\n{app_list_str}"

    except ValueError as e:
        print(f"Authentication/Token Error: {e}")
        return f"Error obtaining authorization token for organization '{organization_name}': {e}. Please check API key and target URL."
    except requests.exceptions.HTTPError as e:
        # Error message construction improved slightly
        status_code = "N/A"
        response_text = "N/A"
        request_url = "N/A"
        if e.response is not None:
            status_code = e.response.status_code
            response_text = e.response.text[:500] # Limit length
        if e.request is not None:
             request_url = e.request.url # Get the final URL sent

        error_message = f"Failed to search applications matching '{search_term}' in organization '{organization_name}'. Status Code: {status_code}. URL: {request_url}."
        try:
            # Try parsing error details ONLY if response exists
            if e.response is not None:
                 error_details = e.response.json()
                 desc = error_details.get('description') or error_details.get('message') or error_details.get('detail')
                 if desc: error_message += f" Detail: {desc}"
                 else: error_message += f" Response: {response_text}"
            else:
                 error_message += f" Error Detail: {e}" # Use original error if no response
        except (requests.exceptions.JSONDecodeError, AttributeError):
             error_message += f" Response: {response_text}"

        print(f"API HTTP Error in search_asgardeo_applications: {error_message}")
        return error_message
    except requests.exceptions.RequestException as e:
        print(f"Network/API Error: {e}")
        return f"Error communicating with Asgardeo API for organization '{organization_name}': {e}"
    except requests.exceptions.JSONDecodeError as e:
         print(f"API Response Parsing Error: {e}")
         # response variable might not be defined here if request failed earlier
         return f"Error parsing the search response from Asgardeo API for organization '{organization_name}'. Invalid JSON received."
    except Exception as e:
        print(f"Unexpected Error: {e}")
        # Log traceback here
        return f"An unexpected error occurred while searching applications matching '{search_term}' for organization '{organization_name}': {e}"
