from pydantic import BaseModel

class ApprovalRequest(BaseModel):
    thread_id: str
    approved: bool