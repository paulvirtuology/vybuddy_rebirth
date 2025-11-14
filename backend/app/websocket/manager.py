"""
Gestionnaire de connexions WebSocket
"""
from fastapi import WebSocket
from typing import Dict
import structlog

logger = structlog.get_logger()


class ConnectionManager:
    """Gère les connexions WebSocket actives"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Établit une nouvelle connexion"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info("Connection established", session_id=session_id)
    
    def disconnect(self, session_id: str):
        """Ferme une connexion"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info("Connection closed", session_id=session_id)
    
    async def send_message(self, websocket: WebSocket, message: dict):
        """Envoie un message via WebSocket"""
        try:
            # Vérifier l'état de la connexion avant d'envoyer
            if websocket.client_state.name != "CONNECTED":
                logger.warning(
                    "WebSocket not connected, skipping message",
                    state=websocket.client_state.name
                )
                return
            
            await websocket.send_json(message)
        except RuntimeError as e:
            # Erreur si le WebSocket est fermé
            if "close message has been sent" in str(e) or "Cannot call" in str(e):
                logger.warning("WebSocket closed, cannot send message", error=str(e))
                return
            raise
        except Exception as e:
            logger.error("Error sending message", error=str(e))
            # Ne pas lever l'exception pour éviter de casser le flux
            return
    
    async def broadcast(self, session_id: str, message: dict):
        """Diffuse un message à une session spécifique"""
        if session_id in self.active_connections:
            await self.send_message(
                self.active_connections[session_id],
                message
            )

