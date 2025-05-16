from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from langchain_core.messages import AIMessage, HumanMessage
from Data_Base.database import get_db
from ..services.assistant import graph
from Data_Base import models
from ..schemas.approval import ApprovalRequest
from ..schemas.chat import ChatRequest, ChatResponse
from ..utils.helper import get_or_create_conversation
from ..utils.serializers import serialize_message, deserialize_message
from ..utils.logger import logger

router = APIRouter(tags=["chat"])

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    logger.info(f"Received chat request - Thread ID: {request.thread_id}, Customer ID: {request.customer_id}")
    
    try:
        # Get or create conversation
        conversation = get_or_create_conversation(db, request.customer_id, request.thread_id)
        logger.debug(f"Conversation retrieved/created for thread {request.thread_id}")
        
        # Create config
        config = {
            "configurable": {
                "customer_id": conversation.customer_id,
                "thread_id": conversation.thread_id,
            }
        }
        
        # Check for pending approval
        if conversation.pending_approval:
            logger.info(f"Pending approval found for thread {request.thread_id}")
            return ChatResponse(
                thread_id=conversation.thread_id,
                response="This action requires approval. Please confirm using the /approve endpoint.",
                requires_approval=True,
                tool_details=conversation.pending_approval
            )
        
        # Deserialize existing messages and add new message
        messages = [deserialize_message(msg) for msg in conversation.messages]
        human_message = HumanMessage(content=request.message)
        messages.append(human_message)
        
        # Stream the response
        logger.debug(f"Streaming response for thread {request.thread_id}")
        events = list(
            graph.stream(
                {"messages": messages},
                config,
                stream_mode="values",
            )
        )
        
        last_event = events[-1]
        
        # Process the response
        tool_call = None
        assistant_response = ""
        
        if isinstance(last_event, dict) and "messages" in last_event:
            event_messages = last_event["messages"]
            last_message = event_messages[-1] if event_messages else None
            
            if isinstance(last_message, AIMessage):
                if last_message.content:
                    messages.append(last_message)
                    assistant_response = last_message.content
                
                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    tool_call = last_message.tool_calls[0]
                    logger.info(f"Tool call detected for thread {request.thread_id}: {tool_call['name']}")
        
        # Update conversation in database
        conversation.messages = [serialize_message(msg) for msg in messages]
        
        # If there's a tool call that needs approval
        if tool_call:
            snapshot = graph.get_state(config)
            if snapshot.next:
                # Store the pending approval
                conversation.pending_approval = {
                    "name": tool_call["name"],
                    "args": tool_call["args"]
                }
                db.commit()
                logger.info(f"Tool approval required for thread {request.thread_id}: {tool_call['name']}")
                
                return ChatResponse(
                    thread_id=conversation.thread_id,
                    response="This action requires approval. Please confirm using the /approve endpoint.",
                    requires_approval=True,
                    tool_details=conversation.pending_approval
                )
        
        conversation.updated_at = datetime.utcnow()
        db.commit()
        logger.info(f"Chat response completed for thread {request.thread_id}")
        
        return ChatResponse(
            thread_id=conversation.thread_id,
            response=assistant_response,
            requires_approval=False
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint - Thread {request.thread_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/approve", response_model=ChatResponse)
async def approve_action(
    request: ApprovalRequest,
    db: Session = Depends(get_db)
):
    logger.info(f"Received approval request for thread {request.thread_id} - Approved: {request.approved}")
    
    try:
        conversation = db.query(models.ConversationHistory).filter(
            models.ConversationHistory.thread_id == request.thread_id
        ).first()
        
        if not conversation:
            logger.warning(f"Conversation not found for thread {request.thread_id}")
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )
        
        if not conversation.pending_approval:
            logger.warning(f"No pending approval found for thread {request.thread_id}")
            raise HTTPException(
                status_code=404,
                detail="No pending approval found"
            )
        
        config = {
            "configurable": {
                "customer_id": conversation.customer_id,
                "thread_id": conversation.thread_id,
            }
        }
        
        messages = [deserialize_message(msg) for msg in conversation.messages]
        
        if not request.approved:
            logger.info(f"Action denied for thread {request.thread_id}")
            conversation.pending_approval = None
            conversation.updated_at = datetime.utcnow()
            db.commit()
            
            return ChatResponse(
                thread_id=conversation.thread_id,
                response="Action was denied successfully.",
                requires_approval=False
            )

        # Process approval
        logger.debug(f"Processing approved action for thread {request.thread_id}")
        result = graph.invoke(None, config)
        
        assistant_response = ""
        if isinstance(result, dict) and "messages" in result:
            result_messages = result["messages"]
            last_message = result_messages[-1] if result_messages else None
            
            if isinstance(last_message, AIMessage) and last_message.content:
                messages.append(last_message)
                assistant_response = last_message.content
        
        # Update conversation in database
        conversation.messages = [serialize_message(msg) for msg in messages]
        conversation.pending_approval = None
        conversation.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Approval processed successfully for thread {request.thread_id}")
        return ChatResponse(
            thread_id=conversation.thread_id,
            response=assistant_response,
            requires_approval=False
        )
        
    except Exception as e:
        logger.error(f"Error in approve endpoint - Thread {request.thread_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversation/{thread_id}")
async def get_conversation(
    thread_id: str,
    db: Session = Depends(get_db)
):
    conversation = db.query(models.ConversationHistory).filter(
        models.ConversationHistory.thread_id == thread_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "thread_id": conversation.thread_id,
        "messages": conversation.messages,
        "customer_id": conversation.customer_id
    }