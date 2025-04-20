# tools.py (showing only the updated list_asgardeo_applications)
from tools.app_mgt_tools import list_asgardeo_applications, delete_asgardeo_application, create_asgardeo_application, \
    search_asgardeo_applications


# --- Helper to get all defined tools ---
# (get_all_tools function remains the same)
def get_context_tools():
    """Returns a list of all defined Langchain tools in this module."""
    return [list_asgardeo_applications, delete_asgardeo_application, create_asgardeo_application, search_asgardeo_applications]
