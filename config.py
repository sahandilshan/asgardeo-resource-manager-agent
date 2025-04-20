# config.py
import os
from dotenv import load_dotenv

# Load .env file variables
load_dotenv()

# Azure OpenAI Config
AZURE_OPENAI_CONFIG = {
    "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
    "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
    "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
    "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
}

# Asgardeo Config
ASGARDEO_CONFIG = {
    "api_token": os.getenv("ASGARDEO_API_TOKEN"),
    "app_mgt_spec_url": os.getenv("ASGARDEO_APP_MGT_SPEC_URL"),
    "scim2_spec_url": os.getenv("ASGARDEO_SCIM2_SPEC_URL"),
    "base_url": os.getenv("ASGARDEO_API_BASE_URL", "").rstrip('/'), # Load the single URL
}

# --- Validation (Optional but Recommended) ---
if not all(AZURE_OPENAI_CONFIG.values()):
    missing_azure = [k for k, v in AZURE_OPENAI_CONFIG.items() if not v]
    raise ValueError(f"Missing Azure OpenAI config in .env: {missing_azure}")

if not ASGARDEO_CONFIG["api_token"]:
    print("Warning: ASGARDEO_API_TOKEN not found in .env file. API calls will likely fail.")

if not ASGARDEO_CONFIG["app_mgt_spec_url"]:
     raise ValueError("Missing Asgardeo App Mgt config in .env: app_mgt_spec_url")
if not ASGARDEO_CONFIG["base_url"]:
     raise ValueError("Missing Asgardeo App Mgt config in .env: ASGARDEO_API_BASE_URL")

print("Configuration loaded successfully.")

# You can add functions here later to get specific configs if needed
def get_app_mgt_config():
    return {
        "spec_url": ASGARDEO_CONFIG["app_mgt_spec_url"],
        "base_url": ASGARDEO_CONFIG["base_url"]
    }

# Add functions for other configs later...