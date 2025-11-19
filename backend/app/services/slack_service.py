"""
Service Slack - Gestion des interactions avec Slack
Gère l'envoi de messages, la réception d'événements et la communication bidirectionnelle
"""
import structlog
import asyncio
from typing import Dict, Any, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from app.core.config import settings

logger = structlog.get_logger()


class SlackService:
    """Service pour gérer les interactions avec Slack"""
    
    def __init__(self):
        """Initialise le client Slack"""
        self.client = WebClient(token=settings.SLACK_BOT_TOKEN) if hasattr(settings, 'SLACK_BOT_TOKEN') and settings.SLACK_BOT_TOKEN else None
    
    def is_configured(self) -> bool:
        """Vérifie si le service Slack est configuré"""
        return self.client is not None
    
    async def send_message(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envoie un message dans un canal Slack
        
        Args:
            channel: ID du canal Slack
            text: Texte du message
            thread_ts: Timestamp du message parent (pour répondre dans un thread)
            
        Returns:
            Réponse de l'API Slack
        """
        if not self.is_configured():
            logger.error("Slack service not configured - SLACK_BOT_TOKEN missing")
            raise ValueError("Slack service not configured")
        
        try:
            # Exécuter l'appel synchrone dans un thread pour ne pas bloquer
            response = await asyncio.to_thread(
                self.client.chat_postMessage,
                channel=channel,
                text=text,
                thread_ts=thread_ts
            )
            
            logger.info(
                "Slack message sent",
                channel=channel,
                thread_ts=thread_ts,
                message_preview=text[:50]
            )
            
            return {
                "ok": response["ok"],
                "ts": response["ts"],
                "channel": response["channel"]
            }
            
        except SlackApiError as e:
            logger.error(
                "Slack API error",
                error=str(e),
                channel=channel
            )
            raise
    
    async def send_ephemeral_message(
        self,
        channel: str,
        user: str,
        text: str
    ) -> Dict[str, Any]:
        """
        Envoie un message éphémère (visible uniquement par l'utilisateur)
        
        Args:
            channel: ID du canal Slack
            user: ID de l'utilisateur Slack
            text: Texte du message
            
        Returns:
            Réponse de l'API Slack
        """
        if not self.is_configured():
            logger.error("Slack service not configured - SLACK_BOT_TOKEN missing")
            raise ValueError("Slack service not configured")
        
        try:
            # Exécuter l'appel synchrone dans un thread pour ne pas bloquer
            response = await asyncio.to_thread(
                self.client.chat_postEphemeral,
                channel=channel,
                user=user,
                text=text
            )
            
            logger.info(
                "Slack ephemeral message sent",
                channel=channel,
                user=user
            )
            
            return {
                "ok": response["ok"],
                "message_ts": response.get("message_ts")
            }
            
        except SlackApiError as e:
            logger.error(
                "Slack API error (ephemeral)",
                error=str(e),
                channel=channel,
                user=user
            )
            raise
    
    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations d'un utilisateur Slack
        
        Args:
            user_id: ID de l'utilisateur Slack
            
        Returns:
            Informations de l'utilisateur ou None
        """
        if not self.is_configured():
            return None
        
        try:
            # Exécuter l'appel synchrone dans un thread pour ne pas bloquer
            response = await asyncio.to_thread(
                self.client.users_info,
                user=user_id
            )
            if response["ok"]:
                return response["user"]
            return None
        except SlackApiError as e:
            logger.error("Error fetching Slack user info", error=str(e), user_id=user_id)
            return None
    
    async def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations d'un canal Slack
        
        Args:
            channel_id: ID du canal Slack
            
        Returns:
            Informations du canal ou None
        """
        if not self.is_configured():
            return None
        
        try:
            # Exécuter l'appel synchrone dans un thread pour ne pas bloquer
            response = await asyncio.to_thread(
                self.client.conversations_info,
                channel=channel_id
            )
            if response["ok"]:
                return response["channel"]
            return None
        except SlackApiError as e:
            logger.error("Error fetching Slack channel info", error=str(e), channel_id=channel_id)
            return None
    
    def verify_slack_signature(
        self,
        timestamp: str,
        body: str,
        signature: str
    ) -> bool:
        """
        Vérifie la signature Slack pour authentifier les requêtes webhook
        
        Args:
            timestamp: Timestamp de la requête
            body: Corps de la requête (string)
            signature: Signature Slack (X-Slack-Signature header)
            
        Returns:
            True si la signature est valide
        """
        import hmac
        import hashlib
        import time
        
        if not hasattr(settings, 'SLACK_SIGNING_SECRET') or not settings.SLACK_SIGNING_SECRET:
            logger.warning("SLACK_SIGNING_SECRET not configured, skipping signature verification")
            return True  # En développement, on peut accepter sans vérification
        
        # Vérifier que la requête n'est pas trop ancienne (5 minutes)
        try:
            request_time = int(timestamp)
            current_time = int(time.time())
            if abs(current_time - request_time) > 60 * 5:
                logger.warning("Slack request timestamp too old", timestamp=timestamp)
                return False
        except ValueError:
            return False
        
        # Calculer la signature attendue
        sig_basestring = f"v0:{timestamp}:{body}"
        expected_signature = 'v0=' + hmac.new(
            settings.SLACK_SIGNING_SECRET.encode('utf-8'),
            sig_basestring.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Comparer les signatures de manière sécurisée
        return hmac.compare_digest(expected_signature, signature)

