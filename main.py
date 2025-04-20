# main.py
from fastapi import FastAPI, Request, HTTPException, Header, Depends, status
from typing import Annotated, List
import uvicorn
from starlette.middleware.cors import CORSMiddleware

import config
from schemas import ChatRequest, ChatResponse, ChatMessage
# Import the context variables and the *new* agent runner
from context import request_api_key_b64_cv, request_org_name_cv
from agent import run_agent_with_context # Assume agent.py is updated (see step 4)

app = FastAPI(
    title="Asgardeo AI Management Agent (Context Aware)",
    description="API using context variables for request data.",
    version="0.3.0",
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency for API Key (remains the same)
async def get_decoded_api_key(api_key: Annotated[str | None, Header(alias="api-key")] = None) -> str:
    # ... (implementation remains the same) ...
    if api_key is None: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing 'api-key' header")
    if not api_key.strip(): raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key cannot be empty")
    return api_key

# Optional dependency for org name (if not using contextvar exclusively)
async def get_org_from_payload(payload: ChatRequest) -> str:
     if not payload.organization_name:
          raise HTTPException(status_code=400, detail="Organization name missing in payload")
     return payload.organization_name

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    payload: ChatRequest, # Need full payload for history and org name
    api_key_b64: Annotated[str, Depends(get_decoded_api_key)],
    # organization_name: Annotated[str, Depends(get_org_from_payload)] # Can still extract it here
):
    """
    Handles chat requests, setting API key and Org Name in context variables.
    """
    organization_name = payload.organization_name # Get org name from payload
    if not organization_name:
         raise HTTPException(status_code=400, detail="Organization name missing in payload")

    print(f"\n--- Received /chat request for Org: {organization_name} (Context Method) ---")

    # --- Set Context Variables ---
    api_key_token = request_api_key_b64_cv.set(api_key_b64)
    org_name_token = request_org_name_cv.set(organization_name)
    print(f"Context Vars Set: api_key_set={'Yes' if api_key_token else 'No'}, org_name_set={'Yes' if org_name_token else 'No'}")


    # Limit chat history
    history_to_keep = payload.chat[-config.MAX_CHAT_HISTORY:]
    if not history_to_keep or history_to_keep[-1].role != 'user':
        # Reset context before raising error
        request_api_key_b64_cv.reset(api_key_token)
        request_org_name_cv.reset(org_name_token)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chat payload.")

    last_user_message = history_to_keep[-1].content
    # Format history as needed by the agent runner
    formatted_history = [{"role": msg.role, "content": msg.content} for msg in history_to_keep[:-1]]

    try:
        # --- Call agent runner (doesn't need key/org passed) ---
        agent_response_content = run_agent_with_context(
            user_query=last_user_message,
            chat_history=formatted_history,
        )
        return ChatResponse(content=agent_response_content)

    except Exception as e:
        print(f"Error during agent execution (context method) for org '{organization_name}': {e}")
        # Log exception traceback here
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An internal error occurred: {e}")

    finally:
        # --- IMPORTANT: Reset Context Variables ---
        # This ensures they don't leak to other requests
        if api_key_token:
            request_api_key_b64_cv.reset(api_key_token)
        if org_name_token:
            request_org_name_cv.reset(org_name_token)
        print("Context Vars Reset")


@app.get("/health", status_code=status.HTTP_200_OK)
# ... (health check remains the same) ...
async def health_check():
    return {"status": "ok", "target": "Asgardeo Agent (Context Aware)"}

# --- Run the API ---
if __name__ == "__main__":
    print("Starting Asgardeo Management Agent API...")
    from dotenv import load_dotenv
    load_dotenv()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
