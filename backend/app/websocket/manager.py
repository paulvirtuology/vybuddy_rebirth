"""
Gestionnaire de connexions WebSocket
"""
from fastapi import WebSocket
from typing import Dict, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class ConnectionInfo:
    """Informations sur une connexion WebSocket"""
    websocket: WebSocket
    user_id: str  # Email de l'utilisateur


class ConnectionManager:
    """Gère les connexions WebSocket actives"""
    
    def __init__(self):
        # session_id -> ConnectionInfo
        self.active_connections: Dict[str, ConnectionInfo] = {}
        # user_id -> set de session_ids
        self.user_sessions: Dict[str, set] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str, user_id: Optional[str] = None):
        """Établit une nouvelle connexion"""
        # Si une connexion existe déjà pour ce session_id, la fermer d'abord
        if session_id in self.active_connections:
            old_connection = self.active_connections[session_id]
            try:
                await old_connection.websocket.close(code=1000, reason="Replaced by new connection")
            except Exception as e:
                logger.debug("Error closing old WebSocket connection", error=str(e), session_id=session_id)
            
            # Retirer de user_sessions si applicable
            if old_connection.user_id and old_connection.user_id in self.user_sessions:
                self.user_sessions[old_connection.user_id].discard(session_id)
                if not self.user_sessions[old_connection.user_id]:
                    del self.user_sessions[old_connection.user_id]
            
            del self.active_connections[session_id]
            logger.info("Replaced existing WebSocket connection", session_id=session_id)
        
        await websocket.accept()
        connection_info = ConnectionInfo(websocket=websocket, user_id=user_id or "unknown")
        self.active_connections[session_id] = connection_info
        
        # Ajouter à user_sessions si user_id est fourni
        if user_id:
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_id)
        
        logger.debug("WebSocket connected", session_id=session_id, user_id=user_id)
    
    def disconnect(self, session_id: str):
        """Ferme une connexion"""
        if session_id in self.active_connections:
            connection_info = self.active_connections[session_id]
            
            # Retirer de user_sessions
            if connection_info.user_id and connection_info.user_id in self.user_sessions:
                self.user_sessions[connection_info.user_id].discard(session_id)
                if not self.user_sessions[connection_info.user_id]:
                    del self.user_sessions[connection_info.user_id]
            
            del self.active_connections[session_id]
            # Logs WebSocket réduits
    
    async def send_message(self, websocket: WebSocket, message: dict):
        """Envoie un message via WebSocket avec gestion robuste des erreurs"""
        try:
            # Vérifier l'état de la connexion avant d'envoyer
            if websocket.client_state.name != "CONNECTED":
                logger.warning(
                    "WebSocket not connected, skipping message",
                    state=websocket.client_state.name,
                    message_type=message.get("type", "unknown")
                )
                return
            
            await websocket.send_json(message)
            logger.debug(
                "WebSocket message sent successfully",
                message_type=message.get("type", "unknown"),
                state=websocket.client_state.name
            )
        except RuntimeError as e:
            # Erreur si le WebSocket est fermé (plusieurs variations possibles)
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in [
                "close message has been sent",
                "cannot call",
                "websocket is not connected",
                "need to call \"accept\" first"
            ]):
                logger.debug("WebSocket closed, cannot send message", error=str(e))
                return
            # Autre RuntimeError, lever l'exception
            raise
        except (ConnectionError, BrokenPipeError, OSError) as e:
            # Erreurs de connexion réseau
            logger.debug("WebSocket connection error", error=str(e))
            return
        except Exception as e:
            # Autres erreurs - logger mais ne pas lever pour éviter de casser le flux
            logger.debug("Error sending message", error=str(e))
            return
    
    async def broadcast(self, session_id: str, message: dict):
        """Diffuse un message à une session spécifique"""
        if session_id in self.active_connections:
            connection_info = self.active_connections[session_id]
            await self.send_message(connection_info.websocket, message)
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        """Diffuse un message à toutes les sessions actives d'un utilisateur"""
        if user_id not in self.user_sessions:
            logger.warning(
                "No active sessions for user - message will not be delivered via WebSocket",
                user_id=user_id,
                message_type=message.get("type", "unknown"),
                hint="Message is saved in Supabase and will be fetched on next page load"
            )
            return
        
        session_ids = list(self.user_sessions[user_id])
        sent_count = 0
        failed_count = 0
        
        for session_id in session_ids:
            if session_id in self.active_connections:
                try:
                    connection_info = self.active_connections[session_id]
                    await self.send_message(connection_info.websocket, message)
                    sent_count += 1
                except Exception as e:
                    failed_count += 1
                    logger.warning(
                        "Error sending message to session",
                        session_id=session_id,
                        user_id=user_id,
                        error=str(e),
                        message_type=message.get("type", "unknown")
                    )
            else:
                logger.debug(
                    "Session not in active connections",
                    session_id=session_id,
                    user_id=user_id
                )
        
        logger.info(
            "Broadcasted message to user sessions",
            user_id=user_id,
            total_sessions=len(session_ids),
            sent_count=sent_count,
            failed_count=failed_count,
            message_type=message.get("type", "unknown")
        )

