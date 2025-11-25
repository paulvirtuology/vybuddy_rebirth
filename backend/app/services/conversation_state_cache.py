"""
Cache Redis pour ConversationState.

Permet de persister l'état de la conversation entre les appels,
évitant de re-classifier et re-extraire les champs à chaque message.
"""
from __future__ import annotations

import json
from typing import Optional
import structlog

from app.database.redis_client import RedisClient
from .ticket_state import ConversationState, ProcedureDefinition, TicketStep

logger = structlog.get_logger()


class ConversationStateCache:
    """
    Cache Redis pour ConversationState.
    
    Permet de:
    - Sauvegarder l'état de la conversation après chaque validation
    - Récupérer l'état précédent pour éviter de re-traiter
    - Invalider le cache après création de ticket
    """

    CACHE_KEY_PREFIX = "ticket_state"
    DEFAULT_TTL = 3600  # 1 heure par défaut

    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.redis = redis_client or RedisClient()

    async def get_state(
        self, session_id: str, user_id: Optional[str] = None
    ) -> Optional[ConversationState]:
        """
        Récupère l'état de la conversation depuis Redis.
        
        Args:
            session_id: ID de la session
            user_id: ID de l'utilisateur (optionnel, pour validation)
        
        Returns:
            ConversationState ou None si non trouvé
        """
        try:
            cache_key = self._build_cache_key(session_id, user_id)
            cached_data = await self.redis.get_session_data(session_id, cache_key)
            
            if not cached_data:
                logger.debug("No cached state found", session_id=session_id)
                return None
            
            # Désérialiser depuis JSON
            state = self._deserialize_state(cached_data)
            
            logger.info(
                "State retrieved from cache",
                session_id=session_id,
                request_type=state.request_type,
                collected_fields_count=len(state.collected_fields),
            )
            
            return state
            
        except Exception as e:
            logger.warning(
                "Failed to retrieve state from cache",
                session_id=session_id,
                error=str(e),
            )
            return None

    async def save_state(
        self,
        state: ConversationState,
        session_id: str,
        user_id: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Sauvegarde l'état de la conversation dans Redis.
        
        Args:
            state: ConversationState à sauvegarder
            session_id: ID de la session
            user_id: ID de l'utilisateur (optionnel)
            ttl: Time to live en secondes (défaut: DEFAULT_TTL)
        
        Returns:
            True si sauvegardé avec succès, False sinon
        """
        try:
            cache_key = self._build_cache_key(session_id, user_id)
            serialized = self._serialize_state(state)
            
            await self.redis.set_session_data(
                session_id=session_id,
                key=cache_key,
                value=serialized,
                ttl=ttl or self.DEFAULT_TTL,
            )
            
            logger.info(
                "State saved to cache",
                session_id=session_id,
                request_type=state.request_type,
                collected_fields_count=len(state.collected_fields),
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to save state to cache",
                session_id=session_id,
                error=str(e),
            )
            return False

    async def invalidate_state(
        self, session_id: str, user_id: Optional[str] = None
    ) -> bool:
        """
        Invalide le cache pour une session (après création de ticket).
        
        Args:
            session_id: ID de la session
            user_id: ID de l'utilisateur (optionnel)
        
        Returns:
            True si invalidé avec succès
        """
        try:
            cache_key = self._build_cache_key(session_id, user_id)
            
            # Utiliser set_session_data avec une valeur None et TTL=1 pour invalider
            # Ou utiliser directement le client Redis pour supprimer
            if not self.redis.client:
                await self.redis.connect()
            
            full_key = f"session:{session_id}:{cache_key}"
            await self.redis.client.delete(full_key)
            
            logger.info("State cache invalidated", session_id=session_id)
            return True
            
        except Exception as e:
            logger.warning(
                "Failed to invalidate state cache",
                session_id=session_id,
                error=str(e),
            )
            return False

    async def update_state_partial(
        self,
        session_id: str,
        updates: dict,
        user_id: Optional[str] = None,
    ) -> Optional[ConversationState]:
        """
        Met à jour partiellement l'état en cache.
        
        Utile pour mettre à jour seulement certains champs sans recharger tout.
        
        Args:
            session_id: ID de la session
            updates: Dict avec les champs à mettre à jour
            user_id: ID de l'utilisateur (optionnel)
        
        Returns:
            ConversationState mis à jour ou None si non trouvé
        """
        state = await self.get_state(session_id, user_id)
        if not state:
            return None
        
        # Appliquer les mises à jour
        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)
        
        # Sauvegarder l'état mis à jour
        await self.save_state(state, session_id, user_id)
        
        return state

    def _build_cache_key(self, session_id: str, user_id: Optional[str] = None) -> str:
        """Construit la clé de cache."""
        if user_id:
            return f"{self.CACHE_KEY_PREFIX}:{user_id}"
        return f"{self.CACHE_KEY_PREFIX}"

    def _serialize_state(self, state: ConversationState) -> dict:
        """
        Sérialise ConversationState en dict JSON-compatible.
        
        Gère la sérialisation des dataclasses et enums.
        """
        return {
            "message": state.message,
            "history": state.history,
            "request_type": state.request_type,
            "procedure": self._serialize_procedure(state.procedure) if state.procedure else None,
            "collected_fields": state.collected_fields,
            "completed_steps": state.completed_steps,
            "needs_human_action": state.needs_human_action,
            "agent_confirmed_action": state.agent_confirmed_action,
            "question_signals": state.question_signals,
        }

    def _deserialize_state(self, data: dict) -> ConversationState:
        """
        Désérialise un dict en ConversationState.
        
        Reconstruit les dataclasses et enums.
        """
        procedure = None
        if data.get("procedure"):
            procedure = self._deserialize_procedure(data["procedure"])
        
        return ConversationState(
            message=data.get("message", ""),
            history=data.get("history", []),
            request_type=data.get("request_type"),
            procedure=procedure,
            collected_fields=data.get("collected_fields", {}),
            completed_steps=data.get("completed_steps", []),
            needs_human_action=data.get("needs_human_action", False),
            agent_confirmed_action=data.get("agent_confirmed_action", False),
            question_signals=data.get("question_signals", []),
        )

    def _serialize_procedure(self, procedure: ProcedureDefinition) -> dict:
        """Sérialise ProcedureDefinition en dict."""
        return {
            "request_type": procedure.request_type,
            "required_fields": procedure.required_fields,
            "diagnostic_steps": procedure.diagnostic_steps,
            "escalation_rules": procedure.escalation_rules,
            "requires_human_action": procedure.requires_human_action,
        }

    def _deserialize_procedure(self, data: dict) -> ProcedureDefinition:
        """Désérialise un dict en ProcedureDefinition."""
        return ProcedureDefinition(
            request_type=data.get("request_type", ""),
            required_fields=data.get("required_fields", []),
            diagnostic_steps=data.get("diagnostic_steps", []),
            escalation_rules=data.get("escalation_rules", {}),
            requires_human_action=data.get("requires_human_action", True),
        )

