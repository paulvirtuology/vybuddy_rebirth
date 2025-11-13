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
    Endpoint WebSocket pour le chat en temps réel
    """
    await manager.connect(websocket, session_id)
    logger.info("WebSocket connection established", session_id=session_id)
    
    try:
        while True:
            # Réception du message
            data = await websocket.receive_json()
            message = data.get("message", "")
            user_id = data.get("user_id", "unknown")
            
            logger.info(
                "Message received",
                session_id=session_id,
                user_id=user_id,
                message_preview=message[:50]
            )
            
            # Orchestration de la requête
            response = await orchestrator.process_request(
                message=message,
                session_id=session_id,
                user_id=user_id
            )
            
            # Envoi de la réponse
            await manager.send_message(
                websocket,
                {
                    "type": "response",
                    "message": response["message"],
                    "agent": response.get("agent"),
                    "metadata": response.get("metadata", {})
                }
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
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "message": "Une erreur est survenue. Veuillez réessayer."
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

