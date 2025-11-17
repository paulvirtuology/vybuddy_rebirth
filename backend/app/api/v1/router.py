"""
Routes API REST
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import structlog

from app.services.orchestrator import OrchestratorService
from app.database.supabase_client import SupabaseClient
from app.database.redis_client import RedisClient
from app.middleware.auth_middleware import get_current_user, get_current_admin

logger = structlog.get_logger()

api_router = APIRouter()
orchestrator = OrchestratorService()
supabase = SupabaseClient()
redis_client = RedisClient()


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
    Crée une nouvelle conversation ou met à jour le titre d'une conversation existante
    Requiert une authentification valide
    
    Si c'est une nouvelle conversation, l'historique Redis est nettoyé pour garantir
    que chaque conversation démarre avec un historique vide et isolé.
    """
    try:
        user_id = current_user.get("email")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        # Vérifier si la conversation existe déjà dans Supabase
        client = supabase._get_client()
        existing_conv = client.table("conversations")\
            .select("*")\
            .eq("session_id", session_id)\
            .eq("user_id", user_id)\
            .execute()
        
        is_new_conversation = not existing_conv.data or len(existing_conv.data) == 0
        
        # Si c'est une nouvelle conversation, nettoyer l'historique Redis
        # pour garantir que chaque conversation démarre avec un historique vide et isolé
        if is_new_conversation:
            await redis_client.clear_session_history(session_id)
            logger.info(
                "New conversation created - Redis history cleared",
                session_id=session_id,
                user_id=user_id
            )
        
        conversation = await supabase.create_or_update_conversation(
            session_id=session_id,
            user_id=user_id,
            title=title
        )
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"success": True, "conversation": conversation, "is_new": is_new_conversation}
        
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


# Modèles pour les feedbacks
class FeedbackRequest(BaseModel):
    """Requête de feedback général"""
    session_id: str
    feedback_type: str = "general"
    content: str
    title: Optional[str] = None
    rating: Optional[int] = None


class MessageFeedbackRequest(BaseModel):
    """Requête de feedback sur un message"""
    interaction_id: str
    session_id: str
    bot_message: str
    reaction: Optional[str] = None  # 'like' ou 'dislike'
    comment: Optional[str] = None


class BatchFeedbackRequest(BaseModel):
    """Requête batch pour récupérer plusieurs feedbacks"""
    interaction_ids: List[str]


@api_router.post("/feedbacks")
async def create_feedback(
    request: FeedbackRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Crée un feedback général
    Requiert une authentification valide
    """
    try:
        user_id = current_user.get("email")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        feedback = await supabase.create_feedback(
            user_id=user_id,
            session_id=request.session_id,
            feedback_type=request.feedback_type,
            content=request.content,
            title=request.title,
            rating=request.rating
        )
        
        if not feedback:
            raise HTTPException(status_code=500, detail="Error creating feedback")
        
        return {"success": True, "feedback": feedback}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/feedbacks/messages")
async def create_message_feedback(
    request: MessageFeedbackRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Crée ou met à jour un feedback sur un message du bot (like/dislike + commentaire)
    Requiert une authentification valide
    """
    try:
        user_id = current_user.get("email")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        # Valider la réaction
        if request.reaction and request.reaction not in ['like', 'dislike']:
            raise HTTPException(status_code=400, detail="Reaction must be 'like' or 'dislike'")
        
        feedback = await supabase.create_message_feedback(
            interaction_id=request.interaction_id,
            user_id=user_id,
            session_id=request.session_id,
            bot_message=request.bot_message,
            reaction=request.reaction,
            comment=request.comment
        )
        
        if not feedback:
            raise HTTPException(status_code=500, detail="Error creating message feedback")
        
        return {"success": True, "feedback": feedback}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/feedbacks/messages/{interaction_id}")
async def get_message_feedback(
    interaction_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Récupère le feedback d'un utilisateur pour un message spécifique
    Requiert une authentification valide
    """
    try:
        user_id = current_user.get("email")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        feedback = await supabase.get_user_message_feedback(
            interaction_id=interaction_id,
            user_id=user_id
        )
        
        return {"feedback": feedback}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/feedbacks/messages/batch")
async def get_message_feedbacks_batch(
    request: BatchFeedbackRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Récupère les feedbacks d'un utilisateur pour plusieurs messages en une seule requête
    Requiert une authentification valide
    """
    try:
        user_id = current_user.get("email")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")
        
        interaction_ids = request.interaction_ids or []
        if not interaction_ids:
            return {"feedbacks": {}}
        
        # Valider que ce sont des UUIDs valides
        import re
        uuid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        valid_ids = [id for id in interaction_ids if uuid_regex.match(id)]
        
        if not valid_ids:
            return {"feedbacks": {}}
        
        feedbacks = await supabase.get_user_message_feedbacks_batch(
            interaction_ids=valid_ids,
            user_id=user_id
        )
        
        return {"feedbacks": feedbacks}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoints admin uniquement
@api_router.get("/admin/feedbacks")
async def get_all_feedbacks(
    limit: int = 100,
    current_user: dict = Depends(get_current_admin)
):
    """
    Récupère tous les feedbacks généraux (admin uniquement)
    """
    try:
        feedbacks = await supabase.get_all_feedbacks(limit=limit)
        return {"feedbacks": feedbacks}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/feedbacks/messages")
async def get_all_message_feedbacks(
    limit: int = 100,
    current_user: dict = Depends(get_current_admin)
):
    """
    Récupère tous les feedbacks sur messages (admin uniquement)
    """
    try:
        feedbacks = await supabase.get_all_message_feedbacks(limit=limit)
        return {"feedbacks": feedbacks}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/feedbacks/stats")
async def get_feedback_stats(
    current_user: dict = Depends(get_current_admin)
):
    """
    Récupère les statistiques des feedbacks (admin uniquement)
    """
    try:
        stats = await supabase.get_feedback_stats()
        return {"stats": stats}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

