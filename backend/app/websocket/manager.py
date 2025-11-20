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
        # Si une connexion existe déjà pour ce session_id, la fermer d'abord
        if session_id in self.active_connections:
            old_websocket = self.active_connections[session_id]
            try:
                await old_websocket.close(code=1000, reason="Replaced by new connection")
            except Exception as e:
                logger.debug("Error closing old WebSocket connection", error=str(e), session_id=session_id)
            del self.active_connections[session_id]
            logger.info("Replaced existing WebSocket connection", session_id=session_id)
        
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.debug("WebSocket connected", session_id=session_id)
    
    def disconnect(self, session_id: str):
        """Ferme une connexion"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            # Logs WebSocket réduits
    
    async def send_message(self, websocket: WebSocket, message: dict):
        """Envoie un message via WebSocket avec gestion robuste des erreurs"""
        try:
            # Vérifier l'état de la connexion avant d'envoyer
            if websocket.client_state.name != "CONNECTED":
                logger.debug(
                    "WebSocket not connected, skipping message",
                    state=websocket.client_state.name
                )
                return
            
            await websocket.send_json(message)
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
            await self.send_message(
                self.active_connections[session_id],
                message
            )

