"""
FastAPI Gateway - Point d'entrée principal de l'API
Orchestre les requêtes et gère les WebSockets
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.health_check import HealthChecker
from app.api.v1.router import api_router
from app.websocket.manager import ConnectionManager
from app.services.orchestrator import OrchestratorService

# Configuration du logging
setup_logging()
logger = structlog.get_logger()

# Gestionnaire de connexions WebSocket
manager = ConnectionManager()

# Service d'orchestration
orchestrator = OrchestratorService()

# Health checker
health_checker = HealthChecker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    logger.info("Starting VyBuddy Rebirth API")
    
    # Vérification de santé des services au démarrage
    if settings.ENVIRONMENT != "test":
        try:
            results = await health_checker.check_all()
            all_ok = health_checker.print_results(results)
            
            if not all_ok:
                logger.warning(
                    "Some services failed health checks",
                    results=results
                )
        except Exception as e:
            logger.error(
                "Health check failed with exception",
                error=str(e),
                exc_info=True
            )
    
    yield
    logger.info("Shutting down VyBuddy Rebirth API")


app = FastAPI(
    title="VyBuddy Rebirth API",
    description="Système multi-agents de support IT",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes API REST
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Health check"""
    return {"status": "ok", "service": "VyBuddy Rebirth API"}


@app.get("/health")
async def health():
    """Health check détaillé avec statut des services"""
    try:
        results = await health_checker.check_all()
        all_ok = all(
            r.get("status") == "ok" or r.get("status") == "warning"
            for r in results.values()
        )
        
        return {
            "status": "healthy" if all_ok else "degraded",
            "service": "VyBuddy Rebirth API",
            "version": "1.0.0",
            "services": results
        }
    except Exception as e:
        logger.error("Health check error", error=str(e))
        return {
            "status": "error",
            "service": "VyBuddy Rebirth API",
            "version": "1.0.0",
            "error": str(e)
        }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    Endpoint WebSocket pour le chat en temps réel avec streaming
    """
    # Vérifier l'authentification via query parameter
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return
    
    # Vérifier le token
    from app.services.auth_service import AuthService
    auth_service = AuthService()
    user_info = await auth_service.verify_token(token)
    
    if not user_info:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return
    
    await manager.connect(websocket, session_id)
    logger.info(
        "WebSocket connection established",
        session_id=session_id,
        user_email=user_info.get("email")
    )
    
    try:
        while True:
            # Réception du message
            data = await websocket.receive_json()
            message = data.get("message", "")
            user_id_from_data = data.get("user_id", "unknown")
            
            # Utiliser l'email de l'utilisateur authentifié
            user_id = user_info.get("email", user_id_from_data)
            
            logger.info(
                "Message received",
                session_id=session_id,
                user_id=user_id,
                message_preview=message[:50]
            )
            
            # Sauvegarder le message utilisateur dans Supabase
            from app.database.supabase_client import SupabaseClient
            supabase = SupabaseClient()
            await supabase.save_message(
                session_id=session_id,
                user_id=user_id,
                message_type="user",
                content=message
            )
            
            # Variable pour accumuler la réponse complète
            agent_used = "processing"
            metadata = {}
            stream_started = False
            
            # Callback pour le streaming (appelé APRÈS génération complète)
            async def stream_callback(token: str):
                """Envoie chaque token au client via WebSocket"""
                nonlocal stream_started
                
                # Vérifier l'état du WebSocket avant d'envoyer
                if websocket.client_state.name != "CONNECTED":
                    logger.debug("WebSocket not connected, skipping stream token")
                    return
                
                # Envoyer stream_start au premier token
                if not stream_started:
                    stream_started = True
                    try:
                        if websocket.client_state.name == "CONNECTED":
                            await websocket.send_json({
                                "type": "stream_start",
                                "agent": "processing"  # "processing" pendant le streaming visuel
                            })
                    except RuntimeError as e:
                        if "close message has been sent" in str(e) or "Cannot call" in str(e):
                            logger.debug("WebSocket closed during stream_start, stopping streaming")
                            return
                        logger.warning("Error sending stream_start", error=str(e))
                    except Exception as e:
                        logger.warning("Error sending stream_start", error=str(e))
                
                try:
                    if websocket.client_state.name == "CONNECTED":
                        await websocket.send_json({
                            "type": "stream",
                            "token": token,
                            "agent": "processing"  # Garder "processing" pendant le streaming
                        })
                except RuntimeError as e:
                    if "close message has been sent" in str(e) or "Cannot call" in str(e):
                        logger.debug("WebSocket closed during streaming, stopping")
                        return
                    logger.warning("Error sending stream token", error=str(e))
                except Exception as e:
                    logger.warning("Error sending stream token", error=str(e))
            
            # Orchestration de la requête avec streaming
            # La réponse complète est générée d'abord, puis streamée via le callback
            response = await orchestrator.process_request(
                message=message,
                session_id=session_id,
                user_id=user_id,
                stream_callback=stream_callback
            )
            
            # Mise à jour des métadonnées APRÈS avoir reçu la réponse
            agent_used = response.get("agent", "unknown")
            metadata = response.get("metadata", {})
            
            # Vérifier que le WebSocket est toujours connecté avant d'envoyer les messages finaux
            if websocket.client_state.name != "CONNECTED":
                logger.warning("WebSocket closed before sending final message", session_id=session_id)
                # Sauvegarder quand même la réponse dans Supabase
                await supabase.save_message(
                    session_id=session_id,
                    user_id=user_id,
                    message_type="bot",
                    content=response["message"],
                    agent_used=agent_used,
                    metadata=metadata
                )
                return
            
            # Si aucun streaming n'a eu lieu (pas de callback), envoyer stream_start puis stream_end
            if not stream_started:
                await manager.send_message(
                    websocket,
                    {
                        "type": "stream_start",
                        "agent": agent_used
                    }
                )
                await manager.send_message(
                    websocket,
                    {
                        "type": "stream",
                        "token": response["message"],
                        "agent": agent_used
                    }
                )
            
            # Envoi du message final avec la réponse complète et le bon agent
            await manager.send_message(
                websocket,
                {
                    "type": "stream_end",
                    "message": response["message"],
                    "agent": agent_used,
                    "metadata": metadata
                }
            )
            
            # Sauvegarder la réponse du bot dans Supabase
            await supabase.save_message(
                session_id=session_id,
                user_id=user_id,
                message_type="bot",
                content=response["message"],
                agent_used=agent_used,
                metadata=metadata
            )
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info("WebSocket disconnected", session_id=session_id)
    except Exception as e:
        logger.error(
            "WebSocket error",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
        try:
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "message": "Une erreur est survenue. Veuillez réessayer."
                }
            )
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

