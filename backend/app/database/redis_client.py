"""
Client Redis Cloud pour la gestion des sessions
"""
import json
import redis.asyncio as redis
import structlog
from typing import List, Dict, Optional

from app.core.config import settings

logger = structlog.get_logger()


class RedisClient:
    """Client Redis pour la gestion de l'état des sessions"""
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.password = settings.REDIS_PASSWORD
        self.client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Établit la connexion Redis"""
        try:
            if self.password:
                self.client = await redis.from_url(
                    self.redis_url,
                    password=self.password,
                    decode_responses=True
                )
            else:
                self.client = await redis.from_url(
                    self.redis_url,
                    decode_responses=True
                )
            logger.debug("Redis connection established")
        except Exception as e:
            logger.error("Redis connection error", error=str(e))
            raise
    
    async def disconnect(self):
        """Ferme la connexion Redis"""
        if self.client:
            await self.client.close()
            logger.debug("Redis connection closed")
    
    async def get_session_history(
        self,
        session_id: str,
        max_items: int = 20
    ) -> List[Dict[str, str]]:
        """
        Récupère l'historique d'une session
        
        IMPORTANT: Chaque session_id a son propre historique isolé via la clé Redis
        `session:{session_id}:history`. Cette méthode garantit que seul l'historique
        de cette session spécifique est retourné.
        
        Args:
            session_id: ID de la session (doit être unique pour chaque conversation)
            max_items: Nombre maximum d'éléments à récupérer
            
        Returns:
            Liste des échanges (user, bot) pour cette session uniquement
        """
        if not self.client:
            await self.connect()
        
        try:
            key = f"session:{session_id}:history"
            history_json = await self.client.lrange(key, 0, max_items - 1)
            
            history = []
            for item in history_json:
                try:
                    history.append(json.loads(item))
                except json.JSONDecodeError:
                    continue
            
            logger.debug(
                "Session history retrieved",
                session_id=session_id,
                items_count=len(history),
                redis_key=key
            )
            
            return list(reversed(history))  # Plus récent en premier
            
        except Exception as e:
            logger.error("Error getting session history", error=str(e), session_id=session_id)
            return []
    
    async def add_to_session_history(
        self,
        session_id: str,
        user_message: str,
        bot_response: str
    ):
        """
        Ajoute un échange à l'historique de la session
        
        IMPORTANT: Chaque session_id a son propre historique isolé via la clé Redis
        `session:{session_id}:history`. Les échanges ne sont ajoutés qu'à l'historique
        de cette session spécifique, garantissant l'isolation entre les conversations.
        
        Args:
            session_id: ID de la session (doit être unique pour chaque conversation)
            user_message: Message de l'utilisateur
            bot_response: Réponse du bot
        """
        if not self.client:
            await self.connect()
        
        try:
            key = f"session:{session_id}:history"
            exchange = {
                "user": user_message,
                "bot": bot_response
            }
            
            await self.client.lpush(key, json.dumps(exchange))
            await self.client.ltrim(key, 0, 99)  # Garder max 100 échanges
            await self.client.expire(key, 86400 * 7)  # Expire après 7 jours
            
            logger.debug(
                "Exchange added to session history",
                session_id=session_id,
                redis_key=key
            )
            
        except Exception as e:
            logger.error("Error adding to session history", error=str(e), session_id=session_id)
    
    async def clear_session_history(self, session_id: str):
        """
        Nettoie l'historique Redis d'une session
        
        Args:
            session_id: ID de la session à nettoyer
        """
        if not self.client:
            await self.connect()
        
        try:
            key = f"session:{session_id}:history"
            await self.client.delete(key)
            logger.info("Session history cleared", session_id=session_id)
        except Exception as e:
            logger.error("Error clearing session history", error=str(e), session_id=session_id)
    
    async def set_session_data(
        self,
        session_id: str,
        key: str,
        value: any,
        ttl: int = 3600
    ):
        """Stocke des données de session"""
        if not self.client:
            await self.connect()
        
        try:
            full_key = f"session:{session_id}:{key}"
            await self.client.setex(
                full_key,
                ttl,
                json.dumps(value) if not isinstance(value, str) else value
            )
        except Exception as e:
            logger.error("Error setting session data", error=str(e))
    
    async def get_session_data(
        self,
        session_id: str,
        key: str
    ) -> Optional[any]:
        """Récupère des données de session"""
        if not self.client:
            await self.connect()
        
        try:
            full_key = f"session:{session_id}:{key}"
            value = await self.client.get(full_key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error("Error getting session data", error=str(e))
            return None

