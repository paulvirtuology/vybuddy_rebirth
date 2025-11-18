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
import json
import re

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
    
    def clean_response(self, response_text: str) -> str:
        """
        Nettoie la réponse du LLM pour enlever tout JSON ou formatage interne
        
        Args:
            response_text: Texte brut de la réponse du LLM
            
        Returns:
            Texte nettoyé sans JSON ni formatage interne
        """
        if not response_text:
            return response_text
        
        cleaned_text = response_text
        
        # Méthode robuste : trouver tous les blocs JSON en comptant les accolades/crochets
        def find_json_blocks(text: str):
            """Trouve tous les blocs JSON valides dans le texte"""
            blocks = []
            i = 0
            while i < len(text):
                # Chercher une accolade ouvrante {
                if text[i] == '{':
                    start = i
                    depth = 0
                    in_string = False
                    escape_next = False
                    
                    for j in range(i, len(text)):
                        char = text[j]
                        
                        if escape_next:
                            escape_next = False
                            continue
                        
                        if char == '\\':
                            escape_next = True
                            continue
                        
                        if char == '"' and not escape_next:
                            in_string = not in_string
                            continue
                        
                        if not in_string:
                            if char == '{':
                                depth += 1
                            elif char == '}':
                                depth -= 1
                                if depth == 0:
                                    # Bloc JSON complet trouvé
                                    json_block = text[start:j+1]
                                    try:
                                        json.loads(json_block)
                                        blocks.append((start, j+1, json_block))
                                    except (json.JSONDecodeError, ValueError):
                                        pass
                                    i = j + 1
                                    break
                        if j == len(text) - 1:
                            # Fin du texte sans fermer le bloc
                            i = j + 1
                            break
                    else:
                        i += 1
                else:
                    i += 1
            
            return blocks
        
        # Supprimer tous les blocs JSON détectés (en ordre inverse pour garder les indices)
        json_blocks = find_json_blocks(cleaned_text)
        for start, end, block in reversed(json_blocks):
            # Vérifier que c'est bien un JSON structurel (avec des clés comme needs_ticket, ticket_info, etc.)
            if any(keyword in block.lower() for keyword in ['needs_ticket', 'ticket_info', 'ticket_id', 'priority', 'description', 'title']):
                cleaned_text = cleaned_text[:start] + cleaned_text[end:]
        
        # Enlever les balises markdown de code JSON si présentes
        cleaned_text = re.sub(r'```json\s*\n.*?\n```', '', cleaned_text, flags=re.DOTALL | re.IGNORECASE)
        cleaned_text = re.sub(r'```\s*\n.*?\n```', '', cleaned_text, flags=re.DOTALL)
        
        # Enlever "needs_ticket: true" si présent (sous différentes formes)
        cleaned_text = re.sub(r'needs_ticket\s*:\s*true', '', cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r'needs_ticket\s*:\s*false', '', cleaned_text, flags=re.IGNORECASE)
        
        # Enlever les lignes contenant uniquement des accolades ou des structures JSON partielles
        lines = cleaned_text.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            # Ignorer les lignes qui sont clairement du JSON
            if stripped.startswith('{') and stripped.endswith('}') and any(keyword in stripped.lower() for keyword in ['needs_ticket', 'ticket', 'priority']):
                continue
            if stripped.startswith('}') or stripped.startswith('{') and len(stripped) < 10:
                continue
            cleaned_lines.append(line)
        
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Nettoyer les espaces multiples et les sauts de ligne
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)  # Max 2 sauts de ligne consécutifs
        cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)  # Espaces multiples -> un seul espace
        cleaned_text = cleaned_text.strip()
        
        return cleaned_text
    
    async def generate_and_stream_response(
        self,
        llm,
        system_prompt: str,
        user_prompt: str,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Génère la réponse complète, puis la stream vers le frontend pour l'affichage progressif
        
        Flux:
        1. Requête utilisateur
        2. Traitement -> génération complète de la réponse
        3. Récupération de la réponse complète
        4. Streaming vers le frontend (pour l'effet visuel uniquement)
        
        Args:
            llm: Le LLM à utiliser
            system_prompt: Le prompt système
            user_prompt: Le prompt utilisateur
            stream_callback: Callback appelé pour streamer la réponse complète par petits morceaux
            
        Returns:
            La réponse complète nettoyée
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            # ÉTAPE 1-2: Générer la réponse COMPLÈTE d'abord (traitement)
            logger.debug("Generating complete response before streaming")
            response = await llm.ainvoke(messages)
            full_response = response.content if hasattr(response, 'content') else str(response)
            
            # ÉTAPE 3: Nettoyer la réponse complète pour enlever tout JSON ou formatage interne
            full_response = self.clean_response(full_response)
            
            # ÉTAPE 4: Streamer la réponse complète vers le frontend (pour l'effet visuel)
            if stream_callback and full_response:
                import asyncio
                # Streamer par petits morceaux pour un effet visuel progressif
                chunk_size = 10  # Environ 10 caractères à la fois
                for i in range(0, len(full_response), chunk_size):
                    token = full_response[i:i+chunk_size]
                    try:
                        await stream_callback(token)
                    except Exception as e:
                        # Si le callback échoue (ex: WebSocket fermé), arrêter le streaming
                        logger.debug("Stream callback error (likely WebSocket closed)", error=str(e))
                        break
                    # Délai minimal pour l'effet visuel (5ms)
                    await asyncio.sleep(0.005)
            
            return full_response
            
        except Exception as e:
            logger.error("Error generating response", error=str(e), exc_info=True)
            # En cas d'erreur, retourner un message d'erreur
            error_message = "Je rencontre un problème technique. Veuillez réessayer."
            if stream_callback:
                try:
                    await stream_callback(error_message)
                except:
                    pass  # Ignorer les erreurs du callback en cas d'erreur principale
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

