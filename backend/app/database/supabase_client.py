"""
Client Supabase pour les logs et l'historique
"""
from supabase import create_client, Client
import structlog
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.config import settings

logger = structlog.get_logger()


class SupabaseClient:
    """Client Supabase pour le stockage des logs"""
    
    def __init__(self):
        self.supabase: Optional[Client] = None
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_KEY
    
    def _get_client(self) -> Client:
        """Retourne le client Supabase (singleton)"""
        if not self.supabase:
            self.supabase = create_client(self.url, self.key)
        return self.supabase
    
    async def log_interaction(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        bot_response: str,
        agent_used: str,
        metadata: Dict[str, Any] = None
    ):
        """
        Enregistre une interaction dans Supabase
        
        Args:
            session_id: ID de la session
            user_id: ID de l'utilisateur
            user_message: Message de l'utilisateur
            bot_response: Réponse du bot
            agent_used: Agent utilisé
            metadata: Métadonnées supplémentaires
        """
        try:
            client = self._get_client()
            
            data = {
                "session_id": session_id,
                "user_id": user_id,
                "user_message": user_message,
                "bot_response": bot_response,
                "agent_used": agent_used,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = client.table("interactions").insert(data).execute()
            
            logger.info(
                "Interaction logged to Supabase",
                session_id=session_id,
                agent_used=agent_used
            )
            
            return result.data
            
        except Exception as e:
            logger.error(
                "Error logging interaction to Supabase",
                error=str(e),
                exc_info=True
            )
    
    async def get_interaction_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> list:
        """
        Récupère l'historique des interactions pour une session
        
        Args:
            session_id: ID de la session
            limit: Nombre maximum d'interactions
            
        Returns:
            Liste des interactions
        """
        try:
            client = self._get_client()
            
            result = client.table("interactions")\
                .select("*")\
                .eq("session_id", session_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(
                "Error getting interaction history",
                error=str(e)
            )
            return []
    
    async def log_ticket_creation(
        self,
        session_id: str,
        user_id: str,
        ticket_id: str,
        issue_description: str
    ):
        """
        Enregistre la création d'un ticket
        
        Args:
            session_id: ID de la session
            user_id: ID de l'utilisateur
            ticket_id: ID du ticket Odoo
            issue_description: Description du problème
        """
        try:
            client = self._get_client()
            
            data = {
                "session_id": session_id,
                "user_id": user_id,
                "ticket_id": ticket_id,
                "issue_description": issue_description,
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = client.table("tickets").insert(data).execute()
            
            logger.info(
                "Ticket creation logged to Supabase",
                session_id=session_id,
                ticket_id=ticket_id
            )
            
            return result.data
            
        except Exception as e:
            logger.error(
                "Error logging ticket creation",
                error=str(e)
            )

