# context.py
from contextvars import ContextVar
from typing import Optional

# Define context variables with a default value (None)
# Use descriptive names
request_api_key_b64_cv: ContextVar[Optional[str]] = ContextVar("request_api_key_b64_cv", default=None)
request_org_name_cv: ContextVar[Optional[str]] = ContextVar("request_org_name_cv", default=None)

# Helper functions (optional but recommended)
def get_request_api_key() -> str:
    """Gets the API key from the current request context."""
    value = request_api_key_b64_cv.get()
    if value is None:
        raise RuntimeError("API key context variable is not set for this request.")
    return value

def get_request_org_name() -> str:
    """Gets the organization name from the current request context."""
    value = request_org_name_cv.get()
    if value is None:
        raise RuntimeError("Organization name context variable is not set for this request.")
    return value
