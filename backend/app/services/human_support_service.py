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
from datetime import datetime, timedelta

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
        is_escalated = bool(state and state.get("status") == "open")
        logger.debug(
            "Checking escalation status",
            session_id=session_id,
            has_state=bool(state),
            status=state.get("status") if state else None,
            is_escalated=is_escalated
        )
        return is_escalated

    async def start_escalation(
        self,
        session_id: str,
        user_id: str,
        user_name: Optional[str],
        initial_message: str
    ) -> Dict[str, Any]:
        """
        Lance une escalade vers le support humain
        
        Raises:
            ValueError: Si SLACK_SUPPORT_CHANNEL n'est pas configuré
            SlackApiError: Si le bot n'a pas accès au canal (doit être invité)
        """
        if not self.support_channel:
            raise ValueError("SLACK_SUPPORT_CHANNEL is not configured")

        if await self.is_session_escalated(session_id):
            logger.info("Human support already active", session_id=session_id)
            return {"already_active": True, "session_id": session_id}

        # Récupérer les infos du bot pour les messages d'erreur
        bot_info = await self.slack.get_bot_info()
        bot_name = bot_info.get("bot_user_name", "VyBuddy Live Support") if bot_info else "VyBuddy Live Support"
        bot_id = bot_info.get("bot_user_id", "") if bot_info else ""
        
        # Vérifier que le canal existe et que le bot y a accès
        channel_info = await self.slack.get_channel_info(self.support_channel)
        if not channel_info:
            logger.warning(
                "Cannot access Slack channel - attempting to join",
                channel=self.support_channel,
                bot_name=bot_name,
                bot_id=bot_id,
                hint=f"If this fails, invite the bot manually: /invite @{bot_name} or use bot ID: {bot_id}"
            )
            # Tenter de rejoindre le canal automatiquement (fonctionne pour les canaux publics)
            joined = await self.slack.join_channel(self.support_channel)
            if not joined:
                # Instructions détaillées pour inviter le bot
                invite_instructions = [
                    f"1. Dans le canal #support-it, tapez: /invite @{bot_name}",
                    f"2. OU utilisez l'ID du bot: /invite <@{bot_id}>" if bot_id else "",
                    "3. OU via l'interface: Cliquez sur le nom du canal → Membres → Ajouter des personnes",
                    f"4. Recherchez '{bot_name}' ou utilisez l'ID: {bot_id}" if bot_id else f"4. Recherchez '{bot_name}'"
                ]
                logger.error(
                    "Failed to join Slack channel - bot must be invited manually",
                    channel=self.support_channel,
                    bot_name=bot_name,
                    bot_id=bot_id,
                    instructions=invite_instructions
                )

        # Message formaté pour Slack
        slack_message = (
            "🚨 *Nouvelle demande d'escalade VyBuddy*\n"
            f"*Utilisateur* : {user_name or user_id}\n"
            f"*Email* : {user_id}\n"
            f"*Session* : `{session_id}`\n"
            f"*Message* : {initial_message}\n\n"
            "_Répondez dans ce fil pour parler avec la personne._"
        )

        try:
            response = await self.slack.send_message(
                channel=self.support_channel,
                text=slack_message
            )
        except Exception as e:
            logger.error(
                "Failed to send escalation message to Slack",
                channel=self.support_channel,
                session_id=session_id,
                error=str(e),
                hint="Ensure the bot is invited to the channel: /invite @VyBuddy Live Support"
            )
            raise

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

        # Sauvegarder dans Supabase comme message "bot" avec agent "human_support"
        # (le frontend attend "bot" pour afficher les messages du support)
        saved_message = await self.supabase.save_message(
            session_id=session_id,
            user_id=state.get("user_id", responder_email or f"slack_{slack_user_id}"),
            message_type="bot",
            content=text,
            agent_used="human_support",
            metadata={
                "platform": "slack",
                "slack_channel": channel,
                "slack_thread_ts": thread_ts,
                "slack_user": slack_user_id,
                "slack_user_name": responder_name,
                "human_support": True,
                "responder": responder_name,
                "responder_email": responder_email
            }
        )

        # Notifier le frontend via WebSocket
        message_data = {
            "type": "stream_end",
            "message": text,
            "agent": "human_support",
            "metadata": {
                "human_support": True,
                "responder": responder_name,
                "responder_email": responder_email
            }
        }
        
        # Ajouter l'ID du message si disponible (pour le feedback)
        if saved_message and saved_message.get("id"):
            message_data["id"] = saved_message["id"]
        
        # STRATÉGIE: File d'attente Redis + Envoi immédiat si connexion active
        # 1. Sauvegarder dans Supabase (pour l'historique)
        # 2. Ajouter à la file d'attente Redis (pour l'envoi différé)
        # 3. Essayer d'envoyer immédiatement si connexion active
        # 4. Si pas de connexion, le message sera envoyé automatiquement à la prochaine reconnexion
        
        user_id = state.get("user_id")
        has_connection = session_id in manager.active_connections
        
        logger.info(
            "Processing human support message",
            session_id=session_id,
            user_id=user_id,
            has_connection=has_connection,
            message_preview=text[:50]
        )
        
        # Ajouter à la file d'attente Redis (même si connexion active, pour garantir la livraison)
        queue_key = f"human_support_queue:{session_id}"
        try:
            import json
            queue_item = {
                "message_data": message_data,
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message_id": saved_message.get("id") if saved_message else None
            }
            if not self.redis.client:
                await self.redis.connect()
            await self.redis.client.lpush(queue_key, json.dumps(queue_item))
            await self.redis.client.expire(queue_key, 3600)  # Expire après 1 heure
            logger.debug(
                "Message added to Redis queue",
                session_id=session_id,
                queue_key=queue_key
            )
        except Exception as e:
            logger.warning(
                "Failed to add message to Redis queue",
                session_id=session_id,
                error=str(e)
            )
        
        # Essayer d'envoyer immédiatement si connexion active
        # IMPORTANT: On ne retire JAMAIS le message de la file, même si envoyé immédiatement
        # Car la connexion peut se fermer avant que le frontend ne le reçoive
        # La file garantit la livraison à la prochaine reconnexion
        sent_immediately = False
        try:
            if has_connection:
                try:
                    await manager.broadcast(session_id, message_data)
                    sent_immediately = True
                    logger.info(
                        "Human support message sent immediately via WebSocket (still in queue for safety)",
                        session_id=session_id,
                        message_preview=text[:50]
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to send immediately, will retry on reconnect",
                        session_id=session_id,
                        error=str(e)
                    )
            
            # Essayer aussi via user_id (au cas où la session spécifique n'est pas active)
            if not sent_immediately and user_id:
                try:
                    await manager.broadcast_to_user(user_id, message_data)
                    sent_immediately = True
                    logger.info(
                        "Human support message sent immediately via user WebSocket (still in queue for safety)",
                        user_id=user_id,
                        message_preview=text[:50]
                    )
                except Exception as e:
                    logger.debug(
                        "Could not send via user WebSocket, will retry on reconnect",
                        user_id=user_id,
                        error=str(e)
                    )
            
            # Le message reste dans la file d'attente pour garantir la livraison
            # même s'il a été envoyé immédiatement (la connexion peut se fermer)
            if sent_immediately:
                logger.debug(
                    "Message sent immediately but kept in queue for delivery guarantee",
                    session_id=session_id
                )
            else:
                logger.info(
                    "Message queued for delivery on next WebSocket connection",
                    session_id=session_id,
                    user_id=user_id
                )
                
        except Exception as e:
            logger.error(
                "Error processing human support message",
                session_id=session_id,
                error=str(e),
                exc_info=True
            )

        state["last_activity_at"] = datetime.utcnow().isoformat()
        await self.redis.set_session_data(session_id, self.SESSION_KEY, state, ttl=self.DEFAULT_TTL)

        logger.info(
            "Human support reply forwarded",
            session_id=session_id,
            responder=responder_name
        )

        return True
    
    async def send_pending_messages_on_reconnect(self, session_id: str, user_id: str) -> int:
        """
        Envoie les messages en attente du support humain depuis la file d'attente Redis.
        Cette méthode est appelée automatiquement lors de la reconnexion WebSocket.
        
        Returns:
            Nombre de messages envoyés
        """
        try:
            # Vérifier que la session est en mode support humain
            state = await self.get_session_state(session_id)
            if not state or state.get("status") != "open":
                logger.debug(
                    "Session not in human support mode, skipping pending messages",
                    session_id=session_id
                )
                return 0
            
            queue_key = f"human_support_queue:{session_id}"
            
            if not self.redis.client:
                await self.redis.connect()
            
            # Récupérer tous les messages de la file d'attente
            queue_length = await self.redis.client.llen(queue_key)
            
            if queue_length == 0:
                logger.debug(
                    "No pending messages in queue",
                    session_id=session_id
                )
                return 0
            
            logger.info(
                "Processing queued human support messages",
                session_id=session_id,
                user_id=user_id,
                queue_length=queue_length
            )
            
            sent_count = 0
            failed_count = 0
            
            # STRATÉGIE: Lire tous les messages sans les retirer, puis retirer seulement ceux envoyés
            # On utilise lrange pour lire sans retirer, puis ltrim pour retirer seulement les envoyés
            
            # Lire tous les messages de la file (sans les retirer)
            all_items = await self.redis.client.lrange(queue_key, 0, -1)
            
            if not all_items:
                logger.debug(
                    "No items in queue (after lrange)",
                    session_id=session_id
                )
                return 0
            
            logger.info(
                "Found items in queue",
                session_id=session_id,
                queue_length=len(all_items)
            )
            
            sent_items_indices = []  # Indices des messages envoyés avec succès
            
            # Traiter chaque message (du plus ancien au plus récent)
            for idx, queue_item_json in enumerate(all_items):
                try:
                    import json
                    queue_item = json.loads(queue_item_json)
                    message_data = queue_item.get("message_data")
                    message_timestamp = queue_item.get("timestamp")
                    message_id = queue_item.get("message_id")
                    
                    if not message_data:
                        logger.warning(
                            "Invalid queue item (missing message_data)",
                            session_id=session_id,
                            index=idx
                        )
                        continue
                    
                    # NOTE: On ne vérifie plus si le message est trop récent
                    # La déduplication se fait côté frontend via l'ID du message
                    # Cela garantit que tous les messages sont envoyés, même s'ils sont récents
                    
                    # Essayer d'envoyer via WebSocket
                    message_sent = False
                    
                    # Essayer d'abord via session_id
                    if session_id in manager.active_connections:
                        try:
                            await manager.broadcast(session_id, message_data)
                            message_sent = True
                            logger.debug(
                                "Sent queued message via session WebSocket",
                                session_id=session_id,
                                message_id=message_id,
                                index=idx
                            )
                        except Exception as e:
                            logger.warning(
                                "Failed to send via session WebSocket",
                                session_id=session_id,
                                error=str(e)
                            )
                    
                    # Si pas envoyé, essayer via user_id
                    if not message_sent and user_id:
                        try:
                            await manager.broadcast_to_user(user_id, message_data)
                            message_sent = True
                            logger.debug(
                                "Sent queued message via user WebSocket",
                                user_id=user_id,
                                message_id=message_id,
                                index=idx
                            )
                        except Exception as e:
                            logger.warning(
                                "Failed to send via user WebSocket",
                                user_id=user_id,
                                error=str(e)
                            )
                    
                    if message_sent:
                        # Message envoyé avec succès, on le marque pour retrait
                        sent_items_indices.append(idx)
                        sent_count += 1
                    else:
                        # Message non envoyé, on le garde dans la file
                        failed_count += 1
                        logger.debug(
                            "Could not send queued message, keeping in queue",
                            session_id=session_id,
                            message_id=message_id,
                            index=idx
                        )
                        # Continuer avec les autres messages
                        
                except json.JSONDecodeError as e:
                    logger.error(
                        "Failed to parse queue item",
                        session_id=session_id,
                        error=str(e),
                        queue_item_preview=queue_item_json[:100] if queue_item_json else "None",
                        index=idx
                    )
                    failed_count += 1
                except Exception as e:
                    logger.error(
                        "Error processing queue item",
                        session_id=session_id,
                        error=str(e),
                        exc_info=True,
                        index=idx
                    )
                    failed_count += 1
            
            # Retirer de la file les messages envoyés avec succès
            # IMPORTANT: On retire immédiatement après l'envoi réussi
            # Le frontend gère la déduplication via l'ID du message
            # Même si la connexion se ferme après, le message a été envoyé
            if sent_items_indices and sent_count > 0:
                # Créer une nouvelle liste sans les messages envoyés
                items_to_keep = [
                    item for idx, item in enumerate(all_items)
                    if idx not in sent_items_indices
                ]
                
                # Supprimer la file actuelle et la recréer avec les messages restants
                await self.redis.client.delete(queue_key)
                if items_to_keep:
                    # Remettre les messages non envoyés dans la file
                    for item in items_to_keep:
                        await self.redis.client.lpush(queue_key, item)
                    await self.redis.client.expire(queue_key, 3600)
                
                logger.info(
                    "Removed sent messages from queue",
                    session_id=session_id,
                    removed_count=len(sent_items_indices),
                    remaining_count=len(items_to_keep)
                )
            
            if sent_count > 0:
                logger.info(
                    "Sent queued human support messages on reconnect",
                    session_id=session_id,
                    user_id=user_id,
                    sent_count=sent_count,
                    failed_count=failed_count,
                    remaining_in_queue=await self.redis.client.llen(queue_key)
                )
            elif failed_count > 0:
                logger.warning(
                    "Could not send any queued messages (connection may have closed)",
                    session_id=session_id,
                    user_id=user_id,
                    failed_count=failed_count,
                    remaining_in_queue=await self.redis.client.llen(queue_key),
                    has_session_connection=session_id in manager.active_connections,
                    has_user_sessions=user_id in manager.user_sessions if user_id else False
                )
            else:
                # Aucun message envoyé et aucun échec - cela ne devrait pas arriver
                logger.warning(
                    "No pending messages were sent (connection may have closed too quickly)",
                    session_id=session_id,
                    user_id=user_id,
                    queue_length_before=queue_length,
                    has_session_connection=session_id in manager.active_connections,
                    has_user_sessions=user_id in manager.user_sessions if user_id else False,
                    remaining_in_queue=await self.redis.client.llen(queue_key)
                )
            
            return sent_count
            
        except Exception as e:
            logger.error(
                "Error sending pending messages from queue",
                session_id=session_id,
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            return 0


