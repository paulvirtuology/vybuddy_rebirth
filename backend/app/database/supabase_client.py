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
    
    async def create_feedback(
        self,
        user_id: str,
        session_id: str,
        feedback_type: str,
        content: str,
        title: Optional[str] = None,
        rating: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Crée un feedback général
        
        Args:
            user_id: ID de l'utilisateur
            session_id: ID de la session
            feedback_type: Type de feedback ('general', 'bug', 'suggestion', etc.)
            content: Contenu du feedback
            title: Titre du feedback (optionnel)
            rating: Note de 1 à 5 (optionnel)
            
        Returns:
            Données du feedback créé
        """
        try:
            client = self._get_client()
            
            data = {
                "user_id": user_id,
                "session_id": session_id,
                "feedback_type": feedback_type,
                "content": content,
                "title": title,
                "rating": rating,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = client.table("feedbacks").insert(data).execute()
            
            logger.info(
                "Feedback created",
                user_id=user_id,
                feedback_type=feedback_type
            )
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(
                "Error creating feedback",
                error=str(e),
                exc_info=True
            )
            return None
    
    async def create_message_feedback(
        self,
        interaction_id: str,
        user_id: str,
        session_id: str,
        bot_message: str,
        reaction: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Crée un feedback sur un message du bot (like/dislike + commentaire)
        
        Args:
            interaction_id: ID de l'interaction (message du bot)
            user_id: ID de l'utilisateur
            session_id: ID de la session
            bot_message: Contenu du message du bot
            reaction: Réaction ('like' ou 'dislike', optionnel)
            comment: Commentaire (optionnel)
            
        Returns:
            Données du feedback créé ou mis à jour
        """
        try:
            client = self._get_client()
            
            # Vérifier si un feedback existe déjà pour cet utilisateur et cette interaction
            existing = client.table("message_feedbacks")\
                .select("*")\
                .eq("interaction_id", interaction_id)\
                .eq("user_id", user_id)\
                .execute()
            
            data = {
                "user_id": user_id,
                "session_id": session_id,
                "bot_message": bot_message,
                "reaction": reaction,
                "comment": comment,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if existing.data and len(existing.data) > 0:
                # Mettre à jour le feedback existant
                result = client.table("message_feedbacks")\
                    .update(data)\
                    .eq("interaction_id", interaction_id)\
                    .eq("user_id", user_id)\
                    .execute()
                
                logger.info(
                    "Message feedback updated",
                    interaction_id=interaction_id,
                    user_id=user_id
                )
            else:
                # Créer un nouveau feedback
                data["interaction_id"] = interaction_id
                data["created_at"] = datetime.utcnow().isoformat()
                
                result = client.table("message_feedbacks").insert(data).execute()
                
                logger.info(
                    "Message feedback created",
                    interaction_id=interaction_id,
                    user_id=user_id
                )
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(
                "Error creating/updating message feedback",
                error=str(e),
                exc_info=True
            )
            return None
    
    async def get_user_message_feedback(
        self,
        interaction_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Récupère le feedback d'un utilisateur pour un message spécifique
        
        Args:
            interaction_id: ID de l'interaction
            user_id: ID de l'utilisateur
            
        Returns:
            Données du feedback ou None
        """
        try:
            client = self._get_client()
            
            result = client.table("message_feedbacks")\
                .select("*")\
                .eq("interaction_id", interaction_id)\
                .eq("user_id", user_id)\
                .execute()
            
            return result.data[0] if result.data and len(result.data) > 0 else None
            
        except Exception as e:
            logger.error(
                "Error getting user message feedback",
                error=str(e)
            )
            return None
    
    async def get_user_message_feedbacks_batch(
        self,
        interaction_ids: list[str],
        user_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Récupère les feedbacks d'un utilisateur pour plusieurs messages en une seule requête
        
        Args:
            interaction_ids: Liste des IDs d'interactions
            user_id: ID de l'utilisateur
            
        Returns:
            Dictionnaire {interaction_id: feedback_data} ou {} si aucun feedback
        """
        try:
            if not interaction_ids:
                return {}
            
            client = self._get_client()
            
            # Récupérer tous les feedbacks pour ces interactions et cet utilisateur
            result = client.table("message_feedbacks")\
                .select("*")\
                .in_("interaction_id", interaction_ids)\
                .eq("user_id", user_id)\
                .execute()
            
            # Retourner un dictionnaire {interaction_id: feedback_data}
            feedbacks = {}
            if result.data:
                for feedback in result.data:
                    feedbacks[feedback.get("interaction_id")] = feedback
            
            return feedbacks
            
        except Exception as e:
            logger.error(
                "Error getting user message feedbacks batch",
                error=str(e),
                exc_info=True
            )
            return {}
    
    async def is_user_admin(self, user_email: str) -> bool:
        """
        Vérifie si un utilisateur est admin
        
        Args:
            user_email: Email de l'utilisateur
            
        Returns:
            True si l'utilisateur est admin
        """
        try:
            client = self._get_client()
            
            result = client.rpc("is_admin_user", {"user_email": user_email}).execute()
            
            return result.data if result.data else False
            
        except Exception as e:
            logger.error(
                "Error checking admin status",
                error=str(e)
            )
            return False
    
    async def get_all_feedbacks(self, limit: int = 100) -> list:
        """
        Récupère tous les feedbacks généraux (admin uniquement)
        
        Args:
            limit: Nombre maximum de feedbacks
            
        Returns:
            Liste des feedbacks
        """
        try:
            client = self._get_client()
            
            result = client.rpc("get_all_feedbacks", {"limit_count": limit}).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(
                "Error getting all feedbacks",
                error=str(e),
                exc_info=True
            )
            return []
    
    async def get_all_message_feedbacks(self, limit: int = 100) -> list:
        """
        Récupère tous les feedbacks sur messages (admin uniquement)
        
        Args:
            limit: Nombre maximum de feedbacks
            
        Returns:
            Liste des feedbacks sur messages
        """
        try:
            client = self._get_client()
            
            result = client.rpc("get_all_message_feedbacks", {"limit_count": limit}).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(
                "Error getting all message feedbacks",
                error=str(e),
                exc_info=True
            )
            return []
    
    async def get_feedback_stats(self) -> Optional[Dict[str, Any]]:
        """
        Récupère les statistiques des feedbacks (admin uniquement)
        
        Returns:
            Statistiques des feedbacks
        """
        try:
            client = self._get_client()
            
            result = client.rpc("get_feedback_stats").execute()
            
            return result.data[0] if result.data and len(result.data) > 0 else None
            
        except Exception as e:
            logger.error(
                "Error getting feedback stats",
                error=str(e)
            )
            return None

