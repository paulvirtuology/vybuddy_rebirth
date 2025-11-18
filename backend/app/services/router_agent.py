"""
Router Agent - Analyse l'intention et choisit le LLM approprié
"""
import structlog
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from app.agents.gemini_wrapper import GeminiChatWrapper

from app.core.config import settings

logger = structlog.get_logger()


class RouterAgent:
    """Agent de routage intelligent"""
    
    def __init__(self):
        # Initialisation des LLMs pour l'analyse
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
    
    async def analyze_and_route(
        self,
        message: str,
        history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Analyse l'intention et route vers le bon agent/LLM
        
        Args:
            message: Message de l'utilisateur
            history: Historique de la conversation
            
        Returns:
            Décision de routage avec intent, llm, et agent
        """
        history_context = ""
        if history:
            history_context = "\n".join([
                f"User: {h.get('user', '')}\nBot: {h.get('bot', '')}"
                for h in history[-5:]  # Derniers 5 échanges
            ])
        
        # Prompt d'analyse d'intention
        analysis_prompt = f"""Analysez l'intention de l'utilisateur et déterminez:
1. Le type de problème (wifi, macos, workspace, knowledge, autre)
2. Le LLM le plus adapté (openai, anthropic, gemini)
3. L'agent spécialisé à utiliser

Règles de routage:
- Problèmes WiFi/Réseau → Network Agent avec Anthropic (raisonnement diagnostique)
- Problèmes MacOS → MacOS Agent avec OpenAI (connaissance technique)
- Problèmes Google Workspace → Workspace Agent avec Gemini (intégration Google)
- Problèmes Timesheet (application web) → Knowledge Agent avec Anthropic (procédure)
- Questions procédures/connaissances → Knowledge Agent avec Anthropic (RAG)
- Autres → Knowledge Agent avec OpenAI (général, fallback)

IMPORTANT: Les problèmes de timesheet sont des problèmes d'application web, PAS des problèmes MacBook. Router vers Knowledge Agent, jamais vers MacOS Agent.

Message utilisateur: {message}

Historique récent:
{history_context if history_context else "Aucun historique"}

Répondez au format JSON:
{{
    "intent": "wifi|macos|workspace|knowledge|other",
    "llm": "openai|anthropic|gemini",
    "agent": "network|macos|workspace|knowledge",
    "confidence": 0.0-1.0
}}
"""
        
        try:
            # Utilisation d'OpenAI pour l'analyse (rapide et fiable)
            response = await self.openai_llm.ainvoke(analysis_prompt)
            
            # Parsing de la réponse (simplifié, en production utiliser un parser JSON)
            import json
            import re
            
            # Extraction du JSON de la réponse
            json_match = re.search(r'\{[^}]+\}', response.content, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group())
            else:
                # Fallback: analyse basique par mots-clés
                decision = self._fallback_routing(message)
            
            logger.info(
                "Routing decision made",
                intent=decision.get("intent"),
                llm=decision.get("llm"),
                agent=decision.get("agent")
            )
            
            return decision
            
        except Exception as e:
            logger.error("Routing error", error=str(e))
            return self._fallback_routing(message)
    
    def _fallback_routing(self, message: str) -> Dict[str, Any]:
        """Routage de secours basé sur des mots-clés"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["wifi", "réseau", "connexion", "internet"]):
            return {
                "intent": "wifi",
                "llm": "anthropic",
                "agent": "network",
                "confidence": 0.7
            }
        elif any(word in message_lower for word in ["timesheet", "feuille de temps", "temps de travail"]):
            # Timesheet = application web, router vers Knowledge Agent (pas MacOS)
            return {
                "intent": "knowledge",
                "llm": "anthropic",
                "agent": "knowledge",
                "confidence": 0.8
            }
        elif any(word in message_lower for word in ["mac", "macbook", "macos", "safari", "finder"]):
            # Exclure timesheet des problèmes MacOS (timesheet = web app)
            if "timesheet" not in message_lower:
                return {
                    "intent": "macos",
                    "llm": "openai",
                    "agent": "macos",
                    "confidence": 0.7
                }
        elif any(word in message_lower for word in ["google", "workspace", "gmail", "drive", "calendar"]):
            return {
                "intent": "workspace",
                "llm": "gemini",
                "agent": "workspace",
                "confidence": 0.7
            }
        elif any(word in message_lower for word in ["procédure", "comment", "guide", "documentation"]):
            return {
                "intent": "knowledge",
                "llm": "anthropic",
                "agent": "knowledge",
                "confidence": 0.7
            }
        else:
            return {
                "intent": "other",
                "llm": "openai",
                "agent": "knowledge",  # Utiliser knowledge comme fallback au lieu de router
                "confidence": 0.5
            }

