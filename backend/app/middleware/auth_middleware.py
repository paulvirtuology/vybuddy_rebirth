"""
Middleware d'authentification pour FastAPI
Vérifie les tokens JWT dans les requêtes
"""
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import structlog

from app.services.auth_service import AuthService

logger = structlog.get_logger()
security = HTTPBearer()


async def verify_token(request: Request) -> Optional[dict]:
    """
    Vérifie le token JWT dans la requête
    
    Args:
        request: Requête FastAPI
        
    Returns:
        Informations utilisateur ou None si non authentifié
    """
    auth_service = AuthService()
    
    # Récupérer le token depuis le header Authorization
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    
    try:
        # Extraire le token (format: "Bearer <token>")
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            return None
        
        # Vérifier le token
        user_info = await auth_service.verify_token(token)
        return user_info
        
    except ValueError:
        # Format invalide
        return None
    except Exception as e:
        logger.warning("Token verification failed", error=str(e))
        return None


async def get_current_user(request: Request) -> dict:
    """
    Récupère l'utilisateur actuel depuis le token
    
    Args:
        request: Requête FastAPI
        
    Returns:
        Informations utilisateur
        
    Raises:
        HTTPException: Si non authentifié
    """
    user_info = await verify_token(request)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non authentifié. Token invalide ou manquant.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_info

