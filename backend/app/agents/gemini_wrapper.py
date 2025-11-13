"""
Wrapper pour Google Gemini compatible avec LangChain
"""
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from pydantic import Field
from typing import Any, List, Optional
import google.generativeai as genai


class GeminiChatWrapper(BaseChatModel):
    """Wrapper pour Google Gemini compatible avec LangChain"""
    
    model_name: str = Field(default="gemini-2.5-pro")  
    temperature: float = Field(default=0.3)
    google_api_key: str = Field()
    client: Any = Field(default=None, exclude=True)
    
    def __init__(self, model: str, temperature: float, google_api_key: str, **kwargs):
        # Configurer Gemini
        genai.configure(api_key=google_api_key)
        client = genai.GenerativeModel(model_name=model)
        
        # Initialiser avec Pydantic
        super().__init__(
            model_name=model,
            temperature=temperature,
            google_api_key=google_api_key,
            client=client,
            **kwargs
        )
    
    @property
    def _llm_type(self) -> str:
        return "gemini"
    
    def _generate(
        self,
        messages: List,
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ):
        """Génère une réponse"""
        # Convertir les messages LangChain en format Gemini
        prompt = ""
        for msg in messages:
            if hasattr(msg, 'content'):
                prompt += msg.content + "\n"
            else:
                prompt += str(msg) + "\n"
        
        response = self.client.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=self.temperature
            )
        )
        
        from langchain_core.outputs import ChatGeneration, ChatResult
        
        # Gérer les différents finish_reason
        # 1 = STOP (normal), 2 = MAX_TOKENS, 3 = SAFETY, 4 = RECITATION
        text = ""
        
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            finish_reason = candidate.finish_reason
            
            # Essayer d'obtenir le texte
            try:
                text = response.text
            except Exception:
                # Si response.text n'est pas disponible, essayer d'extraire depuis les parts
                if candidate.content and candidate.content.parts:
                    text = "".join([part.text for part in candidate.content.parts if hasattr(part, 'text')])
                
                # Si toujours vide et finish_reason est SAFETY, indiquer le blocage
                if not text and finish_reason == 3:
                    text = "[Réponse bloquée par les filtres de sécurité]"
                elif not text:
                    text = f"[Réponse non disponible - finish_reason: {finish_reason}]"
        else:
            text = "[Aucune réponse générée]"
        
        message = HumanMessage(content=text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])
    
    async def _agenerate(
        self,
        messages: List,
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ):
        """Génère une réponse de manière asynchrone"""
        return self._generate(messages, stop, run_manager, **kwargs)

