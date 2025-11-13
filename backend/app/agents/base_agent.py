"""
Agent de base avec fonctionnalités communes
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
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
            api_key=settings.OPENAI_API_KEY
        )
        self.anthropic_llm = ChatAnthropic(
            model="claude-sonnet-4-5",  # Claude Sonnet 4.5 (alias) - Modèle le plus récent
            temperature=0.3,
            api_key=settings.ANTHROPIC_API_KEY
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
    
    @abstractmethod
    async def process(
        self,
        message: str,
        session_id: str,
        user_id: str,
        history: List[Dict[str, str]] = None,
        llm_provider: str = "openai"
    ) -> Dict[str, Any]:
        """Traite un message et retourne une réponse"""
        pass

