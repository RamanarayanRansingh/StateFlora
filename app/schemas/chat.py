from typing import Optional, Dict, Any
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    customer_id: Optional[int] = None
    thread_id: Optional[str] = None

class ChatResponse(BaseModel):
    thread_id: str
    response: str
    requires_approval: bool = False
    tool_details: Optional[Dict[str, Any]] = None