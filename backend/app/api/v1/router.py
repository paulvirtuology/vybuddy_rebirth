"""
Routes API REST
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.services.orchestrator import OrchestratorService
from app.database.supabase_client import SupabaseClient

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
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint REST pour le chat (alternative au WebSocket)
    """
    try:
        response = await orchestrator.process_request(
            message=request.message,
            session_id=request.session_id,
            user_id=request.user_id
        )
        
        return ChatResponse(
            message=response["message"],
            agent=response.get("agent", "unknown"),
            metadata=response.get("metadata", {})
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/history/{session_id}")
async def get_history(session_id: str, limit: int = 50):
    """
    Récupère l'historique d'une session
    """
    try:
        history = await supabase.get_interaction_history(
            session_id=session_id,
            limit=limit
        )
        return {"session_id": session_id, "history": history}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

