"""
Routes API REST
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import structlog
import os
import asyncio
import json

from app.services.orchestrator import OrchestratorService
from app.services.slack_service import SlackService
from app.services.human_support_service import HumanSupportService
from app.services.knowledge_base_storage import KnowledgeBaseStorage
from app.database.supabase_client import SupabaseClient
from app.database.redis_client import RedisClient
from app.middleware.auth_middleware import get_current_user, get_current_admin
from app.core.config import settings

logger = structlog.get_logger()

api_router = APIRouter()
orchestrator = OrchestratorService()
slack_service = SlackService()
human_support = HumanSupportService()
knowledge_base_storage = KnowledgeBaseStorage()  # Instance partagée utilisant le service role key
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


class EscalationRequest(BaseModel):
    """Requête pour démarrer une escalade humaine"""
    session_id: str
    message: str


class EscalationResponse(BaseModel):
    """Réponse d'escalade"""
    status: str
    metadata: dict


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
        user_name = current_user.get("name")
        
        # Support humain déjà actif ?
        if await human_support.is_session_escalated(request.session_id):
            await human_support.forward_user_message(
                session_id=request.session_id,
                user_id=user_id,
                user_name=user_name,
                text=request.message
            )
            return ChatResponse(
                message="Je transmets votre message à notre équipe support. Un collègue vous répondra directement ici.",
                agent="human_support",
                metadata={"human_support": True, "status": "forwarded"}
            )
        
        response = await orchestrator.process_request(
            message=request.message,
            session_id=request.session_id,
            user_id=user_id,
            user_name=user_name
        )
        
        return ChatResponse(
            message=response["message"],
            agent=response.get("agent", "unknown"),
            metadata=response.get("metadata", {})
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/support/escalations", response_model=EscalationResponse)
async def start_human_escalation(
    request: EscalationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Permet à un utilisateur de déclencher explicitement une escalade vers le support humain
    """
    try:
        user_id = current_user.get("email")
        user_name = current_user.get("name")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        result = await human_support.start_escalation(
            session_id=request.session_id,
            user_id=user_id,
            user_name=user_name,
            initial_message=request.message
        )
        
        status = "already_active" if result.get("already_active") else "started"
        return EscalationResponse(
            status=status,
            metadata={
                "human_support": True,
                "session_id": request.session_id
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error starting human escalation", error=str(e))
        raise HTTPException(status_code=500, detail="Unable to start escalation")


@api_router.post("/support/escalations/{session_id}/close")
async def close_human_escalation(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Permet de clôturer manuellement une escalade en cours
    """
    try:
        # Vérifier que l'utilisateur est bien connecté (pas de contrôle supplémentaire pour l'instant)
        if not current_user.get("email"):
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        await human_support.stop_escalation(session_id)
        return {"status": "closed", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error closing human escalation", error=str(e))
        raise HTTPException(status_code=500, detail="Unable to close escalation")


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
        
        # Optimisation: réutiliser le résultat du SELECT au lieu de refaire un SELECT dans create_or_update_conversation
        if existing_conv.data and len(existing_conv.data) > 0:
            # Mettre à jour la conversation existante directement
            result = client.table("conversations")\
                .update({
                    "title": title,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("session_id", session_id)\
                .eq("user_id", user_id)\
                .execute()
            conversation = result.data[0] if result.data else None
        else:
            # Créer la nouvelle conversation
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


# Endpoints admin pour la base de connaissances
class KnowledgeBaseFileRequest(BaseModel):
    """Requête pour créer/modifier un fichier de la base de connaissances"""
    content: str


@api_router.get("/admin/knowledge-base/files")
async def list_knowledge_base_files(
    current_user: dict = Depends(get_current_admin)
):
    """
    Liste tous les fichiers de la base de connaissances (admin uniquement)
    Utilise Supabase Storage
    """
    try:
        files = await knowledge_base_storage.list_files()
        
        return {"files": files}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error listing knowledge base files", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Route OPTIONS explicite pour les fichiers knowledge-base
# Nécessaire car Apache peut avoir des problèmes avec les chemins contenant %2F
# Le middleware ForceCORSMiddleware devrait normalement gérer ça, mais cette route
# sert de fallback spécifique pour les chemins avec %2F qui peuvent ne pas être
# correctement routés par Apache vers le middleware
@api_router.options("/admin/knowledge-base/files/{file_path:path}")
async def options_knowledge_base_file(file_path: str, request: Request):
    """
    Gère les requêtes OPTIONS (preflight CORS) pour les fichiers de la base de connaissances
    Les requêtes OPTIONS ne nécessitent pas d'authentification (preflight CORS)
    Cette route est un fallback spécifique pour les chemins avec %2F
    """
    from fastapi.responses import Response
    from app.core.config import settings
    
    # Décoder le chemin URL (en cas d'encodage %2F pour /)
    from urllib.parse import unquote
    file_path = unquote(file_path)
    
    origin = request.headers.get("origin")
    allowed_origin = None
    if origin and origin in settings.CORS_ORIGINS:
        allowed_origin = origin
    elif settings.CORS_ORIGINS:
        allowed_origin = settings.CORS_ORIGINS[0]
    else:
        allowed_origin = "*"
    
    logger.info(
        "OPTIONS handler for knowledge-base file (fallback)",
        path=file_path,
        origin=origin,
        allowed_origin=allowed_origin
    )
    
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept, X-Requested-With",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "3600",
        }
    )


@api_router.get("/admin/knowledge-base/files/{file_path:path}")
async def get_knowledge_base_file(
    file_path: str,
    current_user: dict = Depends(get_current_admin)
):
    """
    Récupère le contenu d'un fichier de la base de connaissances (admin uniquement)
    Utilise Supabase Storage
    """
    try:
        from urllib.parse import unquote
        
        # Décoder le chemin URL (en cas d'encodage %2F pour /)
        file_path = unquote(file_path)
        
        # Sécuriser le chemin pour éviter les path traversal attacks
        if ".." in file_path or file_path.startswith("/"):
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        file_data = await knowledge_base_storage.get_file(file_path)
        
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")
        
        return file_data
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error reading knowledge base file", error=str(e), file_path=file_path)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.put("/admin/knowledge-base/files/{file_path:path}")
async def update_knowledge_base_file(
    file_path: str,
    request: KnowledgeBaseFileRequest,
    current_user: dict = Depends(get_current_admin)
):
    """
    Crée ou modifie un fichier de la base de connaissances (admin uniquement)
    Utilise Supabase Storage
    """
    try:
        from urllib.parse import unquote
        
        logger.info("PUT request received for knowledge base file", file_path=file_path, user=current_user.get("email"))
        
        # Décoder le chemin URL (en cas d'encodage %2F pour /)
        file_path = unquote(file_path)
        
        # Sécuriser le chemin pour éviter les path traversal attacks
        if ".." in file_path or file_path.startswith("/"):
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        logger.debug("Saving file to storage", file_path=file_path, content_length=len(request.content))
        file_data = await knowledge_base_storage.save_file(file_path, request.content)
        
        if not file_data:
            logger.error("save_file returned None", file_path=file_path)
            raise HTTPException(status_code=500, detail="Failed to save file to storage")
        
        logger.info("Knowledge base file updated successfully", file_path=file_path, normalized_path=file_data.get("path"), user=current_user.get("email"))
        
        return file_data
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error("ValueError in update_knowledge_base_file", error=str(e), file_path=file_path)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error updating knowledge base file", error=str(e), exc_info=True, file_path=file_path)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.delete("/admin/knowledge-base/files/{file_path:path}")
async def delete_knowledge_base_file(
    file_path: str,
    current_user: dict = Depends(get_current_admin)
):
    """
    Supprime un fichier de la base de connaissances (admin uniquement)
    Utilise Supabase Storage
    """
    try:
        from urllib.parse import unquote
        
        # Décoder le chemin URL (en cas d'encodage %2F pour /)
        file_path = unquote(file_path)
        
        # Sécuriser le chemin pour éviter les path traversal attacks
        if ".." in file_path or file_path.startswith("/"):
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        # Ne pas permettre la suppression de README.md
        if file_path.endswith("README.md") or file_path == "README.md":
            raise HTTPException(status_code=400, detail="Cannot delete README.md")
        
        # Vérifier que le fichier existe
        if not await knowledge_base_storage.file_exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Supprimer le fichier
        success = await knowledge_base_storage.delete_file(file_path)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete file")
        
        logger.info("Knowledge base file deleted", file_path=file_path, user=current_user.get("email"))
        
        return {"message": "File deleted successfully", "path": file_path}
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error deleting knowledge base file", error=str(e), file_path=file_path)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/admin/slack/bot-info")
async def get_slack_bot_info(
    current_admin: dict = Depends(get_current_admin)
):
    """
    Endpoint admin pour récupérer les informations du bot Slack.
    Utile pour savoir comment inviter le bot dans les canaux.
    """
    try:
        bot_info = await slack_service.get_bot_info()
        
        if not bot_info:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Slack bot not configured or not accessible",
                    "hint": "Check SLACK_BOT_TOKEN in .env and ensure the app is installed in the workspace"
                }
            )
        
        # Vérifier l'accès au canal support
        support_channel = getattr(settings, "SLACK_SUPPORT_CHANNEL", "")
        channel_info = None
        channel_access = False
        
        if support_channel:
            channel_info = await slack_service.get_channel_info(support_channel)
            channel_access = channel_info is not None
            
            # Si pas d'accès, tenter de rejoindre
            if not channel_access:
                await slack_service.join_channel(support_channel)
                channel_info = await slack_service.get_channel_info(support_channel)
                channel_access = channel_info is not None
        
        return {
            "bot": {
                "user_id": bot_info.get("bot_user_id"),
                "user_name": bot_info.get("bot_user_name"),
                "team_id": bot_info.get("team_id"),
                "team_name": bot_info.get("team_name"),
            },
            "support_channel": {
                "channel_id": support_channel,
                "configured": bool(support_channel),
                "accessible": channel_access,
                "channel_name": channel_info.get("name") if channel_info else None,
                "is_private": channel_info.get("is_private") if channel_info else None,
            },
            "invite_instructions": {
                "method_1": f"Dans le canal #support-it, tapez: /invite @{bot_info.get('bot_user_name', 'VyBuddy Live Support')}",
                "method_2": f"OU utilisez l'ID du bot: /invite <@{bot_info.get('bot_user_id', '')}>" if bot_info.get('bot_user_id') else "ID du bot non disponible",
                "method_3": "OU via l'interface: Cliquez sur le nom du canal → Membres → Ajouter des personnes",
                "note": "Pour les canaux privés, le bot doit être invité manuellement. Les canaux publics peuvent être rejoints automatiquement."
            }
        }
    except Exception as e:
        logger.error("Error getting Slack bot info", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "details": str(e)}
        )


@api_router.post("/admin/knowledge-base/reindex")
async def reindex_knowledge_base(
    current_user: dict = Depends(get_current_admin)
):
    """
    Re-indexe la base de connaissances dans Pinecone (admin uniquement)
    """
    try:
        # Importer et exécuter le script de chargement
        import sys
        
        # Ajouter le chemin du backend au sys.path
        backend_dir = Path(__file__).parent.parent.parent.parent
        scripts_dir = backend_dir / "scripts"
        
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        
        # Importer la fonction de chargement
        from scripts.load_knowledge_base import load_knowledge_base
        
        # Exécuter le chargement de manière asynchrone
        await load_knowledge_base()
        
        logger.info("Knowledge base reindexed", user=current_user.get("email"))
        
        return {"message": "Knowledge base reindexed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error reindexing knowledge base", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error reindexing: {str(e)}")


# ============================================
# Slack Integration Endpoints
# ============================================

class SlackEventRequest(BaseModel):
    """Modèle pour les événements Slack"""
    token: Optional[str] = None
    team_id: Optional[str] = None
    api_app_id: Optional[str] = None
    event: Optional[dict] = None
    type: Optional[str] = None
    challenge: Optional[str] = None  # Pour l'URL verification
    event_id: Optional[str] = None
    event_time: Optional[int] = None


@api_router.post("/slack/events")
async def slack_events(
    request: Request,
    x_slack_signature: Optional[str] = Header(None, alias="X-Slack-Signature"),
    x_slack_request_timestamp: Optional[str] = Header(None, alias="X-Slack-Request-Timestamp")
):
    """
    Endpoint webhook pour recevoir les événements Slack
    Gère les messages, mentions et autres événements
    """
    try:
        # Récupérer le corps de la requête
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8')
        
        # Log de diagnostic : on reçoit bien des requêtes ?
        logger.info(
            "Slack webhook called",
            has_signature=bool(x_slack_signature),
            has_timestamp=bool(x_slack_request_timestamp),
            body_preview=body_str[:200] if body_str else "empty"
        )
        
        # Vérifier la signature Slack (sécurité)
        # #ZNOTE: En développement, on peut temporairement désactiver la vérification pour debug
        if x_slack_signature and x_slack_request_timestamp:
            signature_valid = slack_service.verify_slack_signature(
                timestamp=x_slack_request_timestamp,
                body=body_str,
                signature=x_slack_signature
            )
            if not signature_valid:
                logger.error(
                    "Invalid Slack signature - event will be rejected",
                    signature_preview=x_slack_signature[:20] if x_slack_signature else None,
                    timestamp=x_slack_request_timestamp,
                    body_preview=body_str[:200]
                )
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid signature"}
                )
            logger.debug("Slack signature verified successfully")
        
        # Parser le JSON
        try:
            data = json.loads(body_str)
        except json.JSONDecodeError:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid JSON"}
            )
        
        # URL Verification Challenge (première connexion)
        if data.get("type") == "url_verification":
            challenge = data.get("challenge")
            logger.debug("Slack URL verification challenge received")
            return JSONResponse(content={"challenge": challenge})
        
        # Log tous les événements reçus pour debug
        event_type = data.get("type")
        event = data.get("event", {})
        event_subtype = event.get("type") if event else None
        
        logger.info(
            "Slack event received",
            event_type=event_type,
            event_subtype=event_subtype,
            has_event=bool(event),
            event_keys=list(event.keys()) if event else []
        )
        
        # Traiter les événements de message
        if data.get("type") == "event_callback" and event.get("type") == "message":
            # Extraire les informations du message d'abord
            channel = event.get("channel")
            user = event.get("user")
            text = event.get("text", "").strip()
            ts = event.get("ts")
            thread_ts = event.get("thread_ts")  # Si c'est une réponse dans un thread
            bot_id = event.get("bot_id")
            subtype = event.get("subtype")
            
            # Log tous les messages reçus pour diagnostic
            support_channel_id = getattr(settings, "SLACK_SUPPORT_CHANNEL", "")
            logger.info(
                "Slack message event received",
                channel=channel,
                channel_type=event.get("channel_type"),  # 'C' pour public, 'G' pour privé, 'D' pour DM
                user=user,
                has_thread=bool(thread_ts),
                thread_ts=thread_ts,
                is_support_channel=(channel == support_channel_id),
                text_preview=text[:50] if text else "empty"
            )
            
            # PRIORITÉ 1: Si le message appartient à un thread d'escalade humain, le router vers l'utilisateur
            # (même si c'est un message de bot, on veut traiter les réponses humaines dans les threads)
            if thread_ts:
                mapped_session = await human_support.get_session_by_thread(channel, thread_ts)
                logger.info(
                    "Checking thread for human support",
                    channel=channel,
                    thread_ts=thread_ts,
                    user=user,
                    bot_id=bot_id,
                    text_preview=text[:50],
                    mapped_session=mapped_session,
                    is_support_channel=(channel == support_channel_id)
                )
                if mapped_session:
                    # Ignorer les messages du bot VyBuddy (même s'ils ont un user)
                    # Les messages du bot ont toujours un bot_id dans un thread d'escalade
                    # Les vrais messages humains n'ont PAS de bot_id
                    if bot_id:
                        logger.debug(
                            "Ignoring bot message in escalation thread",
                            bot_id=bot_id,
                            user=user,
                            session_id=mapped_session,
                            text_preview=text[:50]
                        )
                        return JSONResponse(content={"status": "ok"})
                    
                    # Vérifier aussi les patterns spécifiques du bot (sécurité supplémentaire)
                    bot_patterns = [
                        ":rotating_light: *Nouvelle demande d'escalade VyBuddy*",
                        "*Nouvelle demande d'escalade VyBuddy*",
                        "Nouvelle demande d'escalade VyBuddy"
                    ]
                    if any(pattern in text for pattern in bot_patterns):
                        logger.debug(
                            "Ignoring bot pattern message in escalation thread",
                            session_id=mapped_session,
                            text_preview=text[:50]
                        )
                        return JSONResponse(content={"status": "ok"})
                    
                    # Traiter le message (message humain dans un thread d'escalade)
                    # Les vrais messages humains n'ont PAS de bot_id
                    logger.info(
                        "Routing Slack reply to user",
                        session_id=mapped_session,
                        channel=channel,
                        thread_ts=thread_ts,
                        user=user,
                        text_preview=text[:50]
                    )
                    await human_support.handle_slack_reply(
                        channel=channel,
                        thread_ts=thread_ts,
                        slack_user_id=user,  # Pas de fallback bot_id car on a déjà filtré les bots
                        text=text
                    )
                    return JSONResponse(content={"status": "ok"})
                else:
                    logger.warning(
                        "Thread found but no session mapped",
                        channel=channel,
                        thread_ts=thread_ts
                    )
            
            # Ignorer les messages vides
            if not text:
                return JSONResponse(content={"status": "ok"})
            
            # Ignorer les événements de bot (éviter les boucles) - SAUF dans les threads d'escalade déjà traités
            if bot_id or subtype == "bot_message":
                logger.debug("Ignoring bot message event", bot_id=bot_id, subtype=subtype)
                return JSONResponse(content={"status": "ok"})
            
            # Ignorer les messages système que Slack ne permet pas de commenter
            system_subtypes = {
                "channel_join",
                "channel_leave",
                "channel_topic",
                "channel_purpose",
                "channel_name",
                "channel_archive",
                "channel_convert",  # Conversion de canal public en privé (ou vice versa)
                "group_join",
                "group_leave",
                "message_replied",
                "thread_broadcast"
            }
            if subtype in system_subtypes:
                logger.debug(
                    "Ignoring Slack system message",
                    subtype=subtype,
                    channel=channel
                )
                return JSONResponse(content={"status": "ok"})
            
            # Ignorer les messages édités ou supprimés
            if subtype in ["message_changed", "message_deleted"]:
                return JSONResponse(content={"status": "ok"})
            
            logger.debug(
                "Slack message received",
                channel=channel,
                user=user,
                text_preview=text[:50],
                thread_ts=thread_ts
            )
            
            # Créer un session_id basé sur le canal et le thread
            # Si c'est un thread, utiliser le thread_ts comme session_id
            # Sinon, utiliser le canal comme session_id
            if thread_ts:
                session_id = f"slack_{channel}_{thread_ts}"
            else:
                session_id = f"slack_{channel}_{ts}"
            
            # Récupérer les infos utilisateur Slack
            user_info = await slack_service.get_user_info(user)
            user_email = user_info.get("profile", {}).get("email", f"slack_{user}") if user_info else f"slack_{user}"
            user_name = user_info.get("real_name", user_info.get("name", "Unknown")) if user_info else "Unknown"
            
            # Sauvegarder le message utilisateur dans Supabase
            supabase = SupabaseClient()
            await supabase.save_message(
                session_id=session_id,
                user_id=user_email,
                message_type="user",
                content=text,
                metadata={
                    "platform": "slack",
                    "slack_channel": channel,
                    "slack_user": user,
                    "slack_user_name": user_name,
                    "slack_ts": ts,
                    "thread_ts": thread_ts
                }
            )
            
            # Traiter le message avec l'orchestrateur
            orchestrator = OrchestratorService()
            
            # Callback pour streamer la réponse (mais on enverra tout d'un coup dans Slack)
            response_parts = []
            
            async def stream_callback(token: str):
                """Accumule les tokens pour la réponse complète"""
                response_parts.append(token)
            
            # Traiter la requête
            response = await orchestrator.process_request(
                message=text,
                session_id=session_id,
                user_id=user_email,
                stream_callback=stream_callback
            )
            
            # Construire la réponse complète
            response_text = response.get("message", "")
            if response_parts:
                response_text = "".join(response_parts)
            
            # Envoyer la réponse dans Slack (dans le thread si c'est une réponse)
            try:
                await slack_service.send_message(
                    channel=channel,
                    text=response_text,
                    thread_ts=thread_ts or ts  # Répondre dans le thread ou créer un nouveau thread
                )
                
                # Sauvegarder la réponse du bot
                await supabase.save_message(
                    session_id=session_id,
                    user_id=user_email,
                    message_type="bot",
                    content=response_text,
                    agent_used=response.get("agent", "unknown"),
                    metadata={
                        **response.get("metadata", {}),
                        "platform": "slack",
                        "slack_channel": channel
                    }
                )
                
                logger.info(
                    "Slack response sent",
                    channel=channel,
                    thread_ts=thread_ts or ts
                )
                
            except Exception as e:
                logger.error(
                    "Error sending Slack response",
                    error=str(e),
                    channel=channel
                )
                # Envoyer un message d'erreur
                try:
                    await slack_service.send_message(
                        channel=channel,
                        text="Désolé, j'ai rencontré un problème technique. Veuillez réessayer.",
                        thread_ts=thread_ts or ts
                    )
                except:
                    pass
            
            return JSONResponse(content={"status": "ok"})
        
        # Autres types d'événements (non gérés pour l'instant)
        logger.debug("Unhandled Slack event type", event_type=data.get("type"))
        return JSONResponse(content={"status": "ok"})
        
    except Exception as e:
        logger.error("Slack events error", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )


@api_router.post("/slack/commands")
async def slack_commands(
    request: Request,
    x_slack_signature: Optional[str] = Header(None, alias="X-Slack-Signature"),
    x_slack_request_timestamp: Optional[str] = Header(None, alias="X-Slack-Request-Timestamp")
):
    """
    Endpoint pour gérer les commandes Slack (slash commands)
    Exemple: /vybuddy help
    """
    try:
        # Lire le body brut d'abord (nécessaire pour la vérification de signature)
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8')
        
        # Vérifier la signature AVANT de parser le form-data
        if x_slack_signature and x_slack_request_timestamp:
            if not slack_service.verify_slack_signature(
                timestamp=x_slack_request_timestamp,
                body=body_str,
                signature=x_slack_signature
            ):
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid signature"}
                )
        
        # Parser le form-data (form-urlencoded)
        from urllib.parse import parse_qs
        form_data = parse_qs(body_str)
        
        # Extraire les informations de la commande (form_data est un dict de listes)
        command = form_data.get("command", [""])[0] if form_data.get("command") else ""
        text = form_data.get("text", [""])[0] if form_data.get("text") else ""
        user_id = form_data.get("user_id", [""])[0] if form_data.get("user_id") else ""
        channel_id = form_data.get("channel_id", [""])[0] if form_data.get("channel_id") else ""
        response_url = form_data.get("response_url", [""])[0] if form_data.get("response_url") else ""
        
        logger.debug(
            "Slack command received",
            command=command,
            user_id=user_id,
            channel_id=channel_id,
            text=text
        )
        
        # Traiter la commande
        if command == "/vybuddy" or command == "/vybuddy-help":
            help_text = """🤖 *VyBuddy - Assistant Support IT*

*Commandes disponibles:*
• `/vybuddy <votre question>` - Posez une question à VyBuddy
• `/vybuddy-help` - Affiche cette aide

*Exemples:*
• `/vybuddy Comment réinitialiser mon mot de passe Google Workspace?`
• `/vybuddy Mon MacBook ne se connecte pas au WiFi`

VyBuddy peut vous aider avec:
• Problèmes réseau et WiFi
• Problèmes MacBook
• Google Workspace
• Procédures de support IT
• Création de tickets

*Note:* Vous pouvez aussi mentionner @VyBuddy dans un canal pour obtenir de l'aide !"""
            
            return JSONResponse(content={
                "response_type": "ephemeral",  # Visible uniquement par l'utilisateur
                "text": help_text
            })
        
        # Si c'est une question, traiter avec l'orchestrateur
        if text:
            # Créer un session_id pour cette commande
            session_id = f"slack_cmd_{channel_id}_{user_id}"
            
            # Récupérer les infos utilisateur
            user_info = await slack_service.get_user_info(user_id)
            user_email = user_info.get("profile", {}).get("email", f"slack_{user_id}") if user_info else f"slack_{user_id}"
            
            # Traiter avec l'orchestrateur
            orchestrator = OrchestratorService()
            response = await orchestrator.process_request(
                message=text,
                session_id=session_id,
                user_id=user_email
            )
            
            response_text = response.get("message", "")
            
            return JSONResponse(content={
                "response_type": "in_channel",  # Visible par tous
                "text": response_text
            })
        
        # Commande non reconnue
        return JSONResponse(content={
            "response_type": "ephemeral",
            "text": "Commande non reconnue. Utilisez `/vybuddy-help` pour voir l'aide."
        })
        
    except Exception as e:
        logger.error("Slack commands error", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "response_type": "ephemeral",
                "text": "Une erreur est survenue. Veuillez réessayer."
            }
        )


@api_router.post("/slack/interactions")
async def slack_interactions(
    request: Request,
    x_slack_signature: Optional[str] = Header(None, alias="X-Slack-Signature"),
    x_slack_request_timestamp: Optional[str] = Header(None, alias="X-Slack-Request-Timestamp")
):
    """
    Endpoint pour gérer les interactions interactives Slack (boutons, menus, etc.)
    """
    try:
        # Lire le body brut d'abord (nécessaire pour la vérification de signature)
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8')
        
        # Vérifier la signature AVANT de parser le form-data
        if x_slack_signature and x_slack_request_timestamp:
            if not slack_service.verify_slack_signature(
                timestamp=x_slack_request_timestamp,
                body=body_str,
                signature=x_slack_signature
            ):
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid signature"}
                )
        
        # Parser le form-data (form-urlencoded)
        from urllib.parse import parse_qs
        form_data = parse_qs(body_str)
        
        # Parser le payload (JSON string dans form-data)
        payload_str = form_data.get("payload", [""])[0] if form_data.get("payload") else "{}"
        payload = json.loads(payload_str) if payload_str else {}
        
        logger.debug("Slack interaction received", payload_type=payload.get("type"))
        
        # Pour l'instant, on retourne juste un accusé de réception
        # Les interactions peuvent être implémentées plus tard (boutons, etc.)
        return JSONResponse(content={"status": "ok"})
        
    except Exception as e:
        logger.error("Slack interactions error", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )

