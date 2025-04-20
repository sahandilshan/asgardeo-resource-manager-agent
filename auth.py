import base64
from fastapi import HTTPException, status
import requests # Add requests import

import config


def decode_api_key(api_key_header: str) -> tuple[str, str]:
    """
    Decodes the Base64 encoded 'clientId:Secret' API key.
    Returns (clientId, clientSecret) or raises HTTPException.
    """
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key header is missing",
        )
    try:
        if api_key_header.lower().startswith('basic '):
            api_key_header = api_key_header[6:]

        decoded_bytes = base64.b64decode(api_key_header)
        decoded_str = decoded_bytes.decode('utf-8')
        parts = decoded_str.split(':', 1)
        if len(parts) == 2:
            client_id, client_secret = parts
            if client_id and client_secret:
                return client_id, client_secret
            else:
                raise ValueError("Invalid format after decoding.")
        else:
            raise ValueError("API key must be in 'clientId:clientSecret' format after base64 decoding.")
    except (base64.binascii.Error, ValueError, UnicodeDecodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid API key format: {e}",
        )

# --- Placeholder for Token Exchange ---
# This function would live inside the tool or be called by it.
# It simulates exchanging the clientId/Secret for a bearer token.
# --- Asgardeo Token Exchange Implementation ---
def get_asgardeo_access_token(api_key_b64: str, organization_name: str) -> str:
    """
    Exchanges Asgardeo client credentials (provided as a base64 encoded string)
    for a Bearer token using the Client Credentials grant type via a POST request.

    Args:
        api_key_b64: The base64 encoded "clientId:clientSecret" string.
        organization_name: The target Asgardeo organization name.

    Returns:
        The obtained access token string.

    Raises:
        ValueError: If the token exchange fails (network error, bad response, missing token).
    """
    # Construct the token endpoint URL using the configured base URL
    # Note: The curl example used https://localhost:9443, ensure your
    # ASGARDEO_BASE_URL in .env matches your target (e.g., https://api.asgardeo.io/t/)
    token_endpoint = f"{config.ASGARDEO_BASE_URL.rstrip('/')}/{organization_name}/oauth2/token"

    headers = {
        # Use the provided base64 encoded key directly in the Basic Auth header
        'Authorization': f'Basic {api_key_b64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    payload = {
        'grant_type': 'client_credentials'
    }
    params = {
        'scope': 'SYSTEM' # Add scope as a query parameter
    }

    print(f"--- Attempting Asgardeo Token Exchange ---")
    print(f"Token Endpoint: {token_endpoint}")
    print(f"Organization: {organization_name}")
    print(f"Headers: {{'Authorization': 'Basic *****', 'Content-Type': '{headers['Content-Type']}'}}") # Mask key in log
    print(f"Payload: {payload}")
    print(f"Params: {params}")

    try:
        # Make the POST request
        response = requests.post(
            token_endpoint,
            headers=headers,
            data=payload,
            params=params,
            # Consider adding a timeout
            # timeout=10 # Example: 10 seconds
            # If targeting localhost with self-signed cert, might need verify=False
            # verify=False # Use with caution only for local testing!
        )

        # Check for HTTP errors (4xx or 5xx)
        response.raise_for_status()

        # Parse the JSON response
        token_data = response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            print("--- Token exchange failed: 'access_token' not found in response ---")
            print(f"Response Body: {response.text}") # Log response body for debugging
            raise ValueError("Access token not found in the response from Asgardeo token endpoint.")

        print("--- Token exchange successful ---")
        # print(f"Received Token (partial): {access_token[:20]}...") # Optional: log partial token
        return access_token

    except requests.exceptions.RequestException as e:
        print(f"--- Token exchange failed (Network/HTTP Error): {e} ---")
        # Log more details if available
        error_details = str(e)
        if e.response is not None:
            error_details += f" | Status Code: {e.response.status_code} | Response: {e.response.text}"
        raise ValueError(f"Failed to obtain Asgardeo token: {error_details}")
    except requests.exceptions.JSONDecodeError as e:
         print(f"--- Token exchange failed (JSON Parsing Error): {e} ---")
         print(f"Response Body: {response.text}") # Log response body for debugging
         raise ValueError(f"Failed to parse JSON response from Asgardeo token endpoint: {e}")
    except Exception as e:
         # Catch any other unexpected errors during the process
         print(f"--- Token exchange failed (Unexpected Error): {e} ---")
         raise ValueError(f"An unexpected error occurred during token exchange: {e}")