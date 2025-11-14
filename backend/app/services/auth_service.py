"""
Service d'authentification pour le backend
Vérifie les tokens JWT et valide les sessions
"""
import structlog
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from app.database.supabase_client import SupabaseClient
from app.core.config import settings

logger = structlog.get_logger()


class AuthService:
    """Service pour gérer l'authentification backend"""
    
    def __init__(self):
        self.supabase = SupabaseClient()
        self.jwt_secret = settings.NEXTAUTH_SECRET or settings.SECRET_KEY or "fallback-secret-key-change-in-production"
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Vérifie un token JWT et retourne les informations de l'utilisateur
        
        Args:
            token: Token JWT à vérifier
            
        Returns:
            Dictionnaire avec les infos utilisateur ou None si invalide
        """
        try:
            # Décoder le token
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"],
                options={"verify_signature": True}
            )
            
            # Vérifier que l'utilisateur existe et est actif
            email = payload.get("email")
            if not email:
                return None
            
            client = self.supabase._get_client()
            result = client.rpc(
                "is_user_authorized",
                {"user_email": email}
            ).execute()
            
            if not result.data:
                return None
            
            # Retourner les infos utilisateur
            return {
                "email": email,
                "name": payload.get("name"),
                "picture": payload.get("picture"),
            }
            
        except ExpiredSignatureError:
            logger.warning("Token expired", token_preview=token[:20])
            return None
        except InvalidTokenError as e:
            logger.warning("Invalid token", error=str(e))
            return None
        except Exception as e:
            logger.error("Token verification error", error=str(e))
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations d'un utilisateur par email
        
        Args:
            email: Email de l'utilisateur
            
        Returns:
            Dictionnaire avec les infos utilisateur ou None
        """
        try:
            client = self.supabase._get_client()
            result = client.rpc(
                "get_user_by_email",
                {"user_email": email}
            ).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None
    
    async def create_session(
        self,
        user_id: str,
        session_token: str,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Crée une session utilisateur
        
        Args:
            user_id: ID de l'utilisateur
            session_token: Token de session
            expires_at: Date d'expiration
            ip_address: Adresse IP
            user_agent: User agent
            
        Returns:
            True si créé avec succès
        """
        try:
            client = self.supabase._get_client()
            client.table("user_sessions").insert({
                "user_id": user_id,
                "session_token": session_token,
                "expires_at": expires_at.isoformat(),
                "ip_address": ip_address,
                "user_agent": user_agent
            }).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Nettoie les sessions expirées
        
        Returns:
            Nombre de sessions supprimées
        """
        try:
            client = self.supabase._get_client()
            result = client.rpc("cleanup_expired_sessions").execute()
            return result.data if result.data else 0
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
            return 0

