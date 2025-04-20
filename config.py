# config.py
import os
from dotenv import load_dotenv

load_dotenv() # Load variables from .env file

# --- Asgardeo Configuration ---
ASGARDEO_BASE_URL = os.getenv("ASGARDEO_BASE_URL", "https://api.asgardeo.io/t/") # Default if not set

# --- Azure OpenAI Configuration ---
# Assume Azure OpenAI is the provider
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION") # Make sure this is set in .env

# Validate essential Azure config
if not all([AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME, AZURE_OPENAI_API_VERSION]):
    print("Warning: One or more Azure OpenAI environment variables (API_KEY, ENDPOINT, DEPLOYMENT_NAME, API_VERSION) are missing.")
    # You might want to raise an error here depending on requirements
    # raise ValueError("Missing required Azure OpenAI configuration in environment variables.")

# API Configuration
MAX_CHAT_HISTORY = int(os.getenv("MAX_CHAT_HISTORY", 10))
