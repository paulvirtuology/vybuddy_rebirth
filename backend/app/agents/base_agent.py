"""
Agent de base avec fonctionnalités communes
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable, Optional, AsyncIterator
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.gemini_wrapper import GeminiChatWrapper

from app.core.config import settings
import structlog

logger = structlog.get_logger()


class BaseAgent(ABC):
    """Classe de base pour tous les agents"""
    
    def __init__(self):
        self.openai_llm = ChatOpenAI(
            model="gpt-5",
            temperature=0.3,
            api_key=settings.OPENAI_API_KEY,
            streaming=True
        )
        self.anthropic_llm = ChatAnthropic(
            model="claude-sonnet-4-5",  # Claude Sonnet 4.5 (alias) - Modèle le plus récent
            temperature=0.3,
            api_key=settings.ANTHROPIC_API_KEY,
            streaming=True
        )
        self.gemini_llm = GeminiChatWrapper(
            model="gemini-2.5-pro",  # Modèle actuel (gemini-pro est obsolète)
            temperature=0.3,
            google_api_key=settings.GOOGLE_API_KEY
        )
    
    def get_llm(self, provider: str):
        """Retourne le LLM approprié"""
        if provider == "openai":
            return self.openai_llm
        elif provider == "anthropic":
            return self.anthropic_llm
        elif provider == "gemini":
            return self.gemini_llm
        else:
            return self.openai_llm  # Fallback
    
    def build_context(self, message: str, history: List[Dict[str, str]]) -> str:
        """Construit le contexte de conversation"""
        context = ""
        if history:
            context = "\n".join([
                f"Utilisateur: {h.get('user', '')}\nAssistant: {h.get('bot', '')}"
                for h in history[-5:]
            ])
        return context
    
    async def generate_and_stream_response(
        self,
        llm,
        system_prompt: str,
        user_prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Génère d'abord la réponse complète, puis la stream au frontend pour l'effet visuel
        
        Args:
            llm: Le LLM à utiliser
            system_prompt: Le prompt système
            user_prompt: Le prompt utilisateur
            stream_callback: Callback appelé pour chaque token streamé (après génération)
            
        Returns:
            La réponse complète
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        # Étape 1: Générer la réponse complète d'abord (sans streaming)
        try:
            response = await llm.ainvoke(messages)
            full_response = response.content
            
            # Étape 2: Si un callback est fourni, streamer la réponse complète token par token
            if stream_callback and full_response:
                import asyncio
                # Streamer la réponse mot par mot pour un effet visuel fluide
                words = full_response.split(' ')
                for i, word in enumerate(words):
                    token = word + (' ' if i < len(words) - 1 else '')
                    await stream_callback(token)
                    # Petit délai pour l'effet visuel (peut être ajusté)
                    await asyncio.sleep(0.02)  # 20ms entre les mots
            
            return full_response
            
        except Exception as e:
            logger.error("Error generating response", error=str(e), exc_info=True)
            # En cas d'erreur, retourner un message d'erreur
            error_message = "Je rencontre un problème technique. Veuillez réessayer."
            if stream_callback:
                await stream_callback(error_message)
            return error_message
    
    async def stream_response(
        self,
        llm,
        system_prompt: str,
        user_prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Méthode legacy - utilise maintenant generate_and_stream_response
        """
        return await self.generate_and_stream_response(llm, system_prompt, user_prompt, stream_callback)
    
    @abstractmethod
    async def process(
        self,
        message: str,
        session_id: str,
        user_id: str,
        history: List[Dict[str, str]] = None,
        llm_provider: str = "openai",
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Traite un message et retourne une réponse"""
        pass

