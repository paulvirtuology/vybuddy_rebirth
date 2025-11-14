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
    
    async def create_or_update_conversation(
        self,
        session_id: str,
        user_id: str,
        title: str = "Nouveau chat"
    ) -> Optional[Dict[str, Any]]:
        """
        Crée ou met à jour une conversation
        
        Args:
            session_id: ID de la session
            user_id: ID de l'utilisateur
            title: Titre de la conversation
            
        Returns:
            Données de la conversation créée/mise à jour
        """
        try:
            client = self._get_client()
            
            # Vérifier si la conversation existe
            existing = client.table("conversations")\
                .select("*")\
                .eq("session_id", session_id)\
                .eq("user_id", user_id)\
                .execute()
            
            if existing.data and len(existing.data) > 0:
                # Mettre à jour
                result = client.table("conversations")\
                    .update({
                        "title": title,
                        "updated_at": datetime.utcnow().isoformat()
                    })\
                    .eq("session_id", session_id)\
                    .eq("user_id", user_id)\
                    .execute()
                return result.data[0] if result.data else None
            else:
                # Créer
                data = {
                    "session_id": session_id,
                    "user_id": user_id,
                    "title": title,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                result = client.table("conversations").insert(data).execute()
                return result.data[0] if result.data else None
                
        except Exception as e:
            logger.error(
                "Error creating/updating conversation",
                error=str(e),
                exc_info=True
            )
            return None
    
    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = 50
    ) -> list:
        """
        Récupère toutes les conversations d'un utilisateur
        
        Args:
            user_id: ID de l'utilisateur
            limit: Nombre maximum de conversations
            
        Returns:
            Liste des conversations triées par date de mise à jour (plus récentes en premier)
        """
        try:
            client = self._get_client()
            
            result = client.table("conversations")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("updated_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(
                "Error getting user conversations",
                error=str(e),
                exc_info=True
            )
            return []
    
    async def save_message(
        self,
        session_id: str,
        user_id: str,
        message_type: str,
        content: str,
        agent_used: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Sauvegarde un message dans une conversation
        
        Args:
            session_id: ID de la session
            user_id: ID de l'utilisateur
            message_type: Type de message ('user' ou 'bot')
            content: Contenu du message
            agent_used: Agent utilisé (pour les messages bot)
            metadata: Métadonnées supplémentaires
            
        Returns:
            Données du message sauvegardé
        """
        try:
            client = self._get_client()
            
            data = {
                "session_id": session_id,
                "user_id": user_id,
                "message_type": message_type,
                "content": content,
                "agent_used": agent_used,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = client.table("interactions").insert(data).execute()
            
            # Mettre à jour la date de mise à jour de la conversation
            await self.create_or_update_conversation(session_id, user_id)
            
            logger.debug(
                "Message saved to Supabase",
                session_id=session_id,
                message_type=message_type
            )
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(
                "Error saving message to Supabase",
                error=str(e),
                exc_info=True
            )
            return None
    
    async def get_conversation_messages(
        self,
        session_id: str,
        user_id: str,
        limit: int = 100
    ) -> list:
        """
        Récupère tous les messages d'une conversation
        
        Args:
            session_id: ID de la session
            user_id: ID de l'utilisateur (pour vérifier l'accès)
            limit: Nombre maximum de messages
            
        Returns:
            Liste des messages triés par date de création (plus anciens en premier)
        """
        try:
            client = self._get_client()
            
            # Vérifier que la conversation appartient à l'utilisateur
            conv_check = client.table("conversations")\
                .select("id")\
                .eq("session_id", session_id)\
                .eq("user_id", user_id)\
                .execute()
            
            if not conv_check.data or len(conv_check.data) == 0:
                logger.warning(
                    "Conversation access denied",
                    session_id=session_id,
                    user_id=user_id
                )
                return []
            
            result = client.table("interactions")\
                .select("*")\
                .eq("session_id", session_id)\
                .eq("user_id", user_id)\
                .order("created_at", desc=False)\
                .limit(limit)\
                .execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(
                "Error getting conversation messages",
                error=str(e),
                exc_info=True
            )
            return []
    
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
        Enregistre une interaction dans Supabase (méthode legacy, utilise save_message)
        
        Args:
            session_id: ID de la session
            user_id: ID de l'utilisateur
            user_message: Message de l'utilisateur
            bot_response: Réponse du bot
            agent_used: Agent utilisé
            metadata: Métadonnées supplémentaires
        """
        try:
            # Sauvegarder le message utilisateur
            await self.save_message(
                session_id=session_id,
                user_id=user_id,
                message_type="user",
                content=user_message
            )
            
            # Sauvegarder la réponse du bot
            await self.save_message(
                session_id=session_id,
                user_id=user_id,
                message_type="bot",
                content=bot_response,
                agent_used=agent_used,
                metadata=metadata
            )
            
            logger.info(
                "Interaction logged to Supabase",
                session_id=session_id,
                agent_used=agent_used
            )
            
        except Exception as e:
            logger.error(
                "Error logging interaction to Supabase",
                error=str(e),
                exc_info=True
            )
    
    async def get_interaction_history(
        self,
        session_id: str,
        user_id: str = None,
        limit: int = 50
    ) -> list:
        """
        Récupère l'historique des interactions pour une session (méthode legacy)
        Utilise maintenant get_conversation_messages
        
        Args:
            session_id: ID de la session
            user_id: ID de l'utilisateur (requis pour la sécurité)
            limit: Nombre maximum d'interactions
            
        Returns:
            Liste des interactions
        """
        if not user_id:
            logger.warning("get_interaction_history called without user_id")
            return []
        
        return await self.get_conversation_messages(session_id, user_id, limit)
    
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

