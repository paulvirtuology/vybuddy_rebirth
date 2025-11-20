"""
FastAPI Gateway - Point d'entrée principal de l'API
Orchestre les requêtes et gère les WebSockets
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.health_check import HealthChecker
from app.api.v1.router import api_router
from app.websocket.manager_instance import manager
from app.services.orchestrator import OrchestratorService
from app.services.human_support_service import HumanSupportService

# Configuration du logging
setup_logging(log_level=settings.LOG_LEVEL)
logger = structlog.get_logger()

# Services principaux
orchestrator = OrchestratorService()
human_support = HumanSupportService()

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

# Middleware personnalisé pour forcer les headers CORS sur toutes les requêtes
class ForceCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Logger TOUTES les requêtes (pour voir si elles arrivent au middleware)
        # Spécialement important pour les requêtes OPTIONS qui échouent
        if request.method == "OPTIONS":
            logger.error(
                "🔴 OPTIONS request reached middleware",
                path=request.url.path,
                raw_path=str(request.url),
                method=request.method,
                origin=request.headers.get("origin")
            )
        
        # Logger TOUTES les requêtes OPTIONS pour le débogage (même celles qui échouent)
        if request.method == "OPTIONS":
            logger.warning(
                "OPTIONS preflight request received",
                path=request.url.path,
                raw_path=str(request.url),
                query_string=str(request.url.query),
                origin=request.headers.get("origin"),
                access_control_request_method=request.headers.get("access-control-request-method"),
                access_control_request_headers=request.headers.get("access-control-request-headers"),
                host=request.headers.get("host"),
                user_agent=request.headers.get("user-agent")
            )
        
        # Gérer les requêtes OPTIONS (preflight) explicitement AVANT tout autre traitement
        if request.method == "OPTIONS":
            logger.info(
                "OPTIONS preflight request intercepted",
                path=request.url.path,
                raw_path=str(request.url),
                origin=request.headers.get("origin"),
                access_control_request_method=request.headers.get("access-control-request-method"),
                access_control_request_headers=request.headers.get("access-control-request-headers")
            )
            # Créer une réponse OPTIONS avec tous les headers CORS
            origin = request.headers.get("origin")
            allowed_origin = None
            if origin and origin in settings.CORS_ORIGINS:
                allowed_origin = origin
            elif settings.CORS_ORIGINS:
                allowed_origin = settings.CORS_ORIGINS[0]
            else:
                allowed_origin = "*"
            
            response = Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": allowed_origin,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                    "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept, X-Requested-With",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Max-Age": "3600",
                }
            )
            logger.info("OPTIONS response sent", headers=dict(response.headers))
            return response
        
        # Pour les autres méthodes, appeler la route normale puis ajouter les headers CORS
        response = await call_next(request)
        
        # Ajouter les headers CORS à toutes les réponses
        origin = request.headers.get("origin")
        if origin and origin in settings.CORS_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
        elif settings.CORS_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = settings.CORS_ORIGINS[0]
        else:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, X-Requested-With"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "3600"
        
        return response

# CORS - Middleware personnalisé unique (gère toutes les requêtes OPTIONS et ajoute les headers CORS)
# C'est la seule source de vérité pour CORS dans l'application
app.add_middleware(ForceCORSMiddleware)

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
    # Logs WebSocket réduits - seulement en cas d'erreur
    
    try:
        while True:
            # Réception du message
            data = await websocket.receive_json()
            message = data.get("message", "")
            user_id_from_data = data.get("user_id", "unknown")
            
            # Utiliser l'email de l'utilisateur authentifié
            user_id = user_info.get("email", user_id_from_data)
            
            # Logs réduits pour les messages reçus
            
            # Sauvegarder le message utilisateur dans Supabase
            from app.database.supabase_client import SupabaseClient
            supabase = SupabaseClient()
            await supabase.save_message(
                session_id=session_id,
                user_id=user_id,
                message_type="user",
                content=message
            )

            # Si la session est en mode support humain, l'orchestrator gérera le forwarding
            # et retournera un message silencieux pour éviter la duplication
            # On laisse l'orchestrator gérer ça complètement
            
            # Variable pour accumuler la réponse complète
            agent_used = "processing"
            metadata = {}
            stream_started = False
            
            # Callback pour le streaming en temps réel
            async def stream_callback(token: str):
                """Envoie chaque token au client via WebSocket en temps réel"""
                nonlocal stream_started
                
                # Envoyer stream_start au premier token
                if not stream_started:
                    stream_started = True
                    try:
                        # Utiliser manager.send_message qui gère déjà les erreurs
                        await manager.send_message(
                            websocket,
                            {
                                "type": "stream_start",
                                "agent": "processing"
                            }
                        )
                    except Exception as e:
                        logger.debug("Error sending stream_start (likely WebSocket closed)", error=str(e))
                        return
                
                # Envoyer le token via le manager qui gère les erreurs WebSocket
                try:
                    await manager.send_message(
                        websocket,
                        {
                            "type": "stream",
                            "token": token,
                            "agent": "processing"
                        }
                    )
                except Exception as e:
                    # Si erreur, arrêter le streaming (WebSocket probablement fermé)
                    logger.debug("Error sending stream token (likely WebSocket closed)", error=str(e))
                    # Ne pas lever d'exception, le manager gère déjà les erreurs silencieusement
                    # Le streaming continuera côté LLM mais les messages ne seront plus envoyés
            
            # Orchestration de la requête avec streaming
            # La réponse complète est générée d'abord, puis streamée via le callback
            response = await orchestrator.process_request(
                message=message,
                session_id=session_id,
                user_id=user_id,
                user_name=user_info.get("name"),
                stream_callback=stream_callback
            )
            
            # Mise à jour des métadonnées APRÈS avoir reçu la réponse
            agent_used = response.get("agent", "unknown")
            metadata = response.get("metadata", {})
            
            # Si c'est un message silencieux (forwarded sans confirmation), ne rien faire
            if metadata.get("silent") and not response.get("message", "").strip():
                continue  # Passer au message suivant sans envoyer de stream_end
            
            # S'assurer que stream_end est TOUJOURS envoyé, même en cas d'erreur
            try:
                # Sauvegarder la réponse du bot dans Supabase AVANT d'envoyer stream_end pour avoir l'ID
                saved_message = await supabase.save_message(
                    session_id=session_id,
                    user_id=user_id,
                    message_type="bot",
                    content=response["message"],
                    agent_used=agent_used,
                    metadata=metadata
                )
                
                # Ajouter l'ID du message sauvegardé dans les métadonnées pour que le frontend puisse charger le feedback
                if saved_message and saved_message.get("id"):
                    if not metadata:
                        metadata = {}
                    else:
                        metadata = metadata.copy()  # Copier pour ne pas modifier l'original
                    metadata["message_id"] = saved_message["id"]
                
                # Vérifier que le WebSocket est toujours connecté avant d'envoyer les messages finaux
                if websocket.client_state.name != "CONNECTED":
                    logger.debug("WebSocket closed before sending final message", session_id=session_id)
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
                
                # Envoi du message final avec la réponse complète, le bon agent et l'ID du message
                # IMPORTANT: Toujours envoyer stream_end pour que le frontend arrête le loading
                stream_end_data = {
                    "type": "stream_end",
                    "message": response["message"],
                    "agent": agent_used,
                    "metadata": metadata
                }
                # Ajouter l'ID directement si disponible
                if saved_message and saved_message.get("id"):
                    stream_end_data["id"] = saved_message["id"]
                
                await manager.send_message(websocket, stream_end_data)
                
            except Exception as final_error:
                # Même en cas d'erreur, essayer d'envoyer stream_end pour éviter le loading infini
                logger.error(
                    "Error in final message handling, attempting to send stream_end anyway",
                    error=str(final_error),
                    session_id=session_id
                )
                try:
                    if websocket.client_state.name == "CONNECTED":
                        await manager.send_message(
                            websocket,
                            {
                                "type": "stream_end",
                                "message": response.get("message", ""),
                                "agent": agent_used,
                                "metadata": metadata
                            }
                        )
                except Exception:
                    pass  # Si on ne peut pas envoyer stream_end, le frontend utilisera le timeout
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.debug("WebSocket disconnected", session_id=session_id)
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

