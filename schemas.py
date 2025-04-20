# schemas.py
from pydantic import BaseModel, Field
from typing import List, Dict, Union

class ChatMessage(BaseModel):
    """Represents a single message turn in the chat."""
    role: str = Field(..., pattern="^(user|agent)$")
    content: str

class ChatRequest(BaseModel):
    """Request payload for the /chat endpoint."""
    organization_name: str = Field(..., description="The target Asgardeo organization name.")
    chat: List[ChatMessage] = Field(..., min_items=1)

class ChatResponse(BaseModel):
    """Response payload for the /chat endpoint."""
    role: str = "agent"
    content: str
