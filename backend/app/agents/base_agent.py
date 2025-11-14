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
    
    async def stream_response(
        self,
        llm,
        system_prompt: str,
        user_prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Stream une réponse du LLM et appelle le callback pour chaque token
        
        Args:
            llm: Le LLM à utiliser
            system_prompt: Le prompt système
            user_prompt: Le prompt utilisateur
            stream_callback: Callback appelé pour chaque token reçu
            
        Returns:
            La réponse complète
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        full_response = ""
        
        try:
            async for chunk in llm.astream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    token = chunk.content
                    full_response += token
                    if stream_callback:
                        await stream_callback(token)
        except Exception as e:
            # Si le streaming échoue, essayer avec ainvoke en fallback
            logger.warning("Streaming failed, falling back to ainvoke", error=str(e))
            response = await llm.ainvoke(messages)
            full_response = response.content
            if stream_callback:
                # Envoyer la réponse complète d'un coup
                await stream_callback(full_response)
        
        return full_response
    
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

