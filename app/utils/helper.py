from langchain_core.runnables import RunnableLambda

from langgraph.prebuilt import ToolNode

from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import uuid
from langchain_core.messages import ToolMessage
from Data_Base import models


def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n please fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }


def create_tool_node_with_fallback(tools: list) -> dict:
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )


def get_or_create_conversation(db: Session, customer_id: Optional[int], thread_id: Optional[str]) -> models.ConversationHistory:
    """Get existing conversation or create a new one with customer validation"""

    if thread_id:
        conversation = db.query(models.ConversationHistory).filter(
            models.ConversationHistory.thread_id == thread_id
        ).first()
        
        if conversation:
            # Ensure the thread belongs to the same customer
            if conversation.customer_id != customer_id:
                raise HTTPException(status_code=403, detail="Thread ID does not belong to this customer")
            return conversation

    if not customer_id:
        raise HTTPException(status_code=400, detail="customer_id is required for new conversations")

    # Verify if the customer exists
    customer = db.query(models.Customer).filter(
        models.Customer.customer_id == customer_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Create a new conversation with a unique thread_id
    new_thread_id = str(uuid.uuid4())
    conversation = models.ConversationHistory(
        thread_id=new_thread_id,
        customer_id=customer_id,
        messages=[],
        created_at=datetime.utcnow()
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation