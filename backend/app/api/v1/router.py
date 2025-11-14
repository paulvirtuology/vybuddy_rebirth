"""
Routes API REST
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from app.services.orchestrator import OrchestratorService
from app.database.supabase_client import SupabaseClient
from app.middleware.auth_middleware import get_current_user

api_router = APIRouter()
orchestrator = OrchestratorService()
supabase = SupabaseClient()


class ChatRequest(BaseModel):
    """Requête de chat"""
    message: str
    session_id: str
    user_id: str


class ChatResponse(BaseModel):
    """Réponse de chat"""
    message: str
    agent: str
    metadata: dict = {}


@api_router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint REST pour le chat (alternative au WebSocket)
    Requiert une authentification valide
    """
    try:
        # Utiliser l'email de l'utilisateur authentifié
        user_id = current_user.get("email", request.user_id)
        
        response = await orchestrator.process_request(
            message=request.message,
            session_id=request.session_id,
            user_id=user_id
        )
        
        return ChatResponse(
            message=response["message"],
            agent=response.get("agent", "unknown"),
            metadata=response.get("metadata", {})
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/conversations")
async def get_conversations(
    current_user: dict = Depends(get_current_user),
    limit: int = 50
):
    """
    Récupère toutes les conversations de l'utilisateur authentifié
    Requiert une authentification valide
    """
    try:
        user_id = current_user.get("email")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        conversations = await supabase.get_user_conversations(
            user_id=user_id,
            limit=limit
        )
        
        # Formater les conversations pour le frontend
        formatted = [
            {
                "id": conv["session_id"],
                "title": conv["title"],
                "timestamp": conv["updated_at"]
            }
            for conv in conversations
        ]
        
        return {"conversations": formatted}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/conversations/{session_id}/messages")
async def get_conversation_messages(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    limit: int = 100
):
    """
    Récupère tous les messages d'une conversation
    Requiert une authentification valide
    L'utilisateur ne peut accéder qu'à ses propres conversations
    """
    try:
        user_id = current_user.get("email")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        messages = await supabase.get_conversation_messages(
            session_id=session_id,
            user_id=user_id,
            limit=limit
        )
        
        # Formater les messages pour le frontend
        formatted = [
            {
                "id": msg["id"],
                "type": msg["message_type"],
                "content": msg["content"],
                "timestamp": msg["created_at"],
                "agent": msg.get("agent_used"),
                "metadata": msg.get("metadata", {})
            }
            for msg in messages
        ]
        
        return {"session_id": session_id, "messages": formatted}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/conversations/{session_id}/title")
async def update_conversation_title(
    session_id: str,
    title: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Met à jour le titre d'une conversation
    Requiert une authentification valide
    """
    try:
        user_id = current_user.get("email")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        conversation = await supabase.create_or_update_conversation(
            session_id=session_id,
            user_id=user_id,
            title=title
        )
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"success": True, "conversation": conversation}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/history/{session_id}")
async def get_history(
    session_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """
    Récupère l'historique d'une session (endpoint legacy)
    Requiert une authentification valide
    """
    try:
        user_id = current_user.get("email")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        history = await supabase.get_interaction_history(
            session_id=session_id,
            user_id=user_id,
            limit=limit
        )
        return {"session_id": session_id, "history": history}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

