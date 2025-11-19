"""
Service de bridge humain (VyBuddy <-> Slack)
Gère les escalades vers l'équipe support et la synchronisation des messages
"""
import structlog
from datetime import datetime
from typing import Optional, Dict, Any

from app.services.slack_service import SlackService
from app.database.redis_client import RedisClient
from app.database.supabase_client import SupabaseClient
from app.core.config import settings
from app.websocket.manager_instance import manager

logger = structlog.get_logger()


class HumanSupportService:
    """Service centralisé pour les escalades vers le support humain"""

    SESSION_KEY = "human_support"
    THREAD_KEY_PREFIX = "human_support_thread"
    DEFAULT_TTL = 60 * 60 * 12  # 12h

    def __init__(self):
        self.slack = SlackService()
        self.redis = RedisClient()
        self.supabase = SupabaseClient()
        self.support_channel = getattr(settings, "SLACK_SUPPORT_CHANNEL", "")

    def _thread_key(self, channel: str, thread_ts: str) -> str:
        return f"{self.THREAD_KEY_PREFIX}:{channel}:{thread_ts}"

    async def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retourne l'état d'escalade d'une session"""
        try:
            return await self.redis.get_session_data(session_id, self.SESSION_KEY)
        except Exception as e:
            logger.error("Error getting human support state", error=str(e), session_id=session_id)
            return None

    async def is_session_escalated(self, session_id: str) -> bool:
        """Indique si la session est actuellement gérée par le support humain"""
        state = await self.get_session_state(session_id)
        return bool(state and state.get("status") == "open")

    async def start_escalation(
        self,
        session_id: str,
        user_id: str,
        user_name: Optional[str],
        initial_message: str
    ) -> Dict[str, Any]:
        """
        Lance une escalade vers le support humain
        """
        if not self.support_channel:
            raise ValueError("SLACK_SUPPORT_CHANNEL is not configured")

        if await self.is_session_escalated(session_id):
            logger.info("Human support already active", session_id=session_id)
            return {"already_active": True, "session_id": session_id}

        # Message formaté pour Slack
        slack_message = (
            "🚨 *Nouvelle demande d'escalade VyBuddy*\n"
            f"*Utilisateur* : {user_name or user_id}\n"
            f"*Email* : {user_id}\n"
            f"*Session* : `{session_id}`\n"
            f"*Message* : {initial_message}\n\n"
            "_Répondez dans ce fil pour parler avec la personne._"
        )

        response = await self.slack.send_message(
            channel=self.support_channel,
            text=slack_message
        )

        thread_ts = response["ts"]
        channel = response["channel"]

        state = {
            "status": "open",
            "session_id": session_id,
            "user_id": user_id,
            "user_name": user_name or user_id,
            "channel": channel,
            "thread_ts": thread_ts,
            "started_at": datetime.utcnow().isoformat(),
            "last_activity_at": datetime.utcnow().isoformat()
        }

        await self.redis.set_session_data(
            session_id,
            self.SESSION_KEY,
            state,
            ttl=self.DEFAULT_TTL
        )

        if not self.redis.client:
            await self.redis.connect()

        await self.redis.client.setex(
            self._thread_key(channel, thread_ts),
            self.DEFAULT_TTL,
            session_id
        )

        logger.info(
            "Human support escalation started",
            session_id=session_id,
            channel=channel,
            thread_ts=thread_ts
        )

        # Envoyer le premier message utilisateur dans le thread Slack
        await self.slack.send_message(
            channel=channel,
            text=f"*{user_name or user_id}* : {initial_message}",
            thread_ts=thread_ts
        )

        return {"already_active": False, "session_id": session_id, "state": state}

    async def stop_escalation(self, session_id: str):
        """Clôture l'escalade"""
        state = await self.get_session_state(session_id)
        if not state:
            return

        state["status"] = "closed"
        state["closed_at"] = datetime.utcnow().isoformat()

        await self.redis.set_session_data(
            session_id,
            self.SESSION_KEY,
            state,
            ttl=self.DEFAULT_TTL
        )

        if not self.redis.client:
            await self.redis.connect()

        await self.redis.client.delete(self._thread_key(state["channel"], state["thread_ts"]))

        logger.info("Human support escalation closed", session_id=session_id)

    async def forward_user_message(
        self,
        session_id: str,
        user_id: str,
        user_name: Optional[str],
        text: str
    ) -> bool:
        """Transfère un message utilisateur vers Slack"""
        state = await self.get_session_state(session_id)
        if not state or state.get("status") != "open":
            return False

        await self.slack.send_message(
            channel=state["channel"],
            text=f"*{user_name or user_id}* : {text}",
            thread_ts=state["thread_ts"]
        )

        state["last_activity_at"] = datetime.utcnow().isoformat()
        await self.redis.set_session_data(session_id, self.SESSION_KEY, state, ttl=self.DEFAULT_TTL)
        return True

    async def get_session_by_thread(self, channel: str, thread_ts: str) -> Optional[str]:
        """Retrouve la session associée à un thread Slack"""
        if not self.redis.client:
            await self.redis.connect()
        return await self.redis.client.get(self._thread_key(channel, thread_ts))

    async def handle_slack_reply(
        self,
        channel: str,
        thread_ts: str,
        slack_user_id: str,
        text: str
    ) -> bool:
        """Traite une réponse humaine depuis Slack"""
        session_id = await self.get_session_by_thread(channel, thread_ts)
        if not session_id:
            return False

        state = await self.get_session_state(session_id)
        if not state:
            return False

        user_info = await self.slack.get_user_info(slack_user_id)
        responder_name = user_info.get("real_name") if user_info else slack_user_id
        responder_email = user_info.get("profile", {}).get("email") if user_info else None

        # Sauvegarder dans Supabase comme message "human"
        await self.supabase.save_message(
            session_id=session_id,
            user_id=responder_email or f"slack_{slack_user_id}",
            message_type="human",
            content=text,
            metadata={
                "platform": "slack",
                "slack_channel": channel,
                "slack_thread_ts": thread_ts,
                "slack_user": slack_user_id,
                "slack_user_name": responder_name,
                "human_support": True
            }
        )

        # Notifier le frontend via WebSocket
        await manager.broadcast(
            session_id,
            {
                "type": "stream_end",
                "message": text,
                "agent": "human_support",
                "metadata": {
                    "human_support": True,
                    "responder": responder_name,
                    "responder_email": responder_email
                }
            }
        )

        state["last_activity_at"] = datetime.utcnow().isoformat()
        await self.redis.set_session_data(session_id, self.SESSION_KEY, state, ttl=self.DEFAULT_TTL)

        logger.info(
            "Human support reply forwarded",
            session_id=session_id,
            responder=responder_name
        )

        return True


