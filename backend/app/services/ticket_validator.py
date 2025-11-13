"""
Validateur de tickets - Détermine si un ticket doit être créé
"""
from typing import Dict, Any, List
import structlog
from langchain_openai import ChatOpenAI

from app.core.config import settings

logger = structlog.get_logger()


class TicketValidator:
    """Valide si un ticket doit être créé basé sur le contexte"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-5",
            temperature=0.2,
            api_key=settings.OPENAI_API_KEY
        )
    
    async def should_create_ticket(
        self,
        message: str,
        agent_response: str,
        agent_used: str,
        history: List[Dict[str, str]] = None,
        needs_ticket_suggested: bool = False
    ) -> Dict[str, Any]:
        """
        Évalue si un ticket doit être créé
        
        Args:
            message: Message original de l'utilisateur
            agent_response: Réponse de l'agent
            agent_used: Agent qui a traité la demande
            history: Historique de la conversation
            needs_ticket_suggested: Si l'agent a suggéré un ticket
            
        Returns:
            Dict avec 'should_create' (bool) et 'reason' (str)
        """
        # Construire le contexte de la conversation
        history_context = ""
        if history:
            history_context = "\n".join([
                f"User: {h.get('user', '')}\nBot: {h.get('bot', '')}"
                for h in history[-5:]
            ])
        
        # Cas où on ne crée PAS de ticket
        exclusion_keywords = [
            "salutation",
            "bonjour",
            "hello",
            "hi",
            "merci",
            "thanks",
            "au revoir",
            "goodbye",
            "question simple",
            "information générale",
            "déjà résolu",
            "problème résolu",
            "ça fonctionne",
            "c'est bon",
            "ok",
            "parfait"
        ]
        
        message_lower = message.lower()
        response_lower = agent_response.lower()
        
        # Vérifier les exclusions évidentes
        for keyword in exclusion_keywords:
            if keyword in message_lower or keyword in response_lower:
                return {
                    "should_create": False,
                    "reason": f"Message exclu: {keyword}",
                    "confidence": 0.9
                }
        
        # Si le message est très court et n'est pas un problème technique
        if len(message.split()) <= 3 and not any(tech_word in message_lower for tech_word in ["wifi", "réseau", "connexion", "problème", "erreur", "bug"]):
            return {
                "should_create": False,
                "reason": "Message trop court et non technique",
                "confidence": 0.8
            }
        
        # Prompt pour l'évaluation LLM
        evaluation_prompt = f"""Vous êtes un validateur de tickets de support IT. Votre rôle est de déterminer si un ticket doit être créé dans Odoo.

Règles de validation:
1. Créer un ticket SEULEMENT si:
   - Le problème technique n'a pas pu être résolu après diagnostic
   - L'utilisateur demande explicitement un ticket
   - Le problème nécessite une intervention humaine (ex: accès, permissions, matériel)
   - Le problème est complexe et nécessite une escalade
   - L'agent a épuisé toutes les solutions possibles

2. NE PAS créer de ticket si:
   - Le problème a été résolu
   - C'est une simple question d'information
   - C'est une salutation ou un message court
   - L'utilisateur demande juste des informations générales
   - Le problème peut être résolu par l'utilisateur avec les instructions données

Message utilisateur: {message}

Réponse de l'agent ({agent_used}): {agent_response}

Historique récent:
{history_context if history_context else "Aucun historique"}

L'agent a-t-il suggéré un ticket? {needs_ticket_suggested}

Analysez la situation et répondez au format JSON:
{{
    "should_create": true/false,
    "reason": "Explication détaillée de la décision",
    "confidence": 0.0-1.0
}}

Répondez UNIQUEMENT avec le JSON, sans texte supplémentaire."""

        try:
            response = await self.llm.ainvoke(evaluation_prompt)
            response_text = response.content.strip()
            
            # Extraire le JSON de la réponse
            import json
            import re
            
            # Chercher le JSON dans la réponse
            json_match = re.search(r'\{[^{}]*"should_create"[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # Essayer de parser toute la réponse
                result = json.loads(response_text)
            
            logger.info(
                "Ticket validation result",
                should_create=result.get("should_create", False),
                reason=result.get("reason", ""),
                confidence=result.get("confidence", 0.5),
                agent=agent_used
            )
            
            return {
                "should_create": result.get("should_create", False),
                "reason": result.get("reason", "Évaluation par LLM"),
                "confidence": result.get("confidence", 0.5)
            }
            
        except Exception as e:
            logger.error("Ticket validation error", error=str(e))
            # En cas d'erreur, être conservateur: ne créer un ticket que si explicitement suggéré
            return {
                "should_create": needs_ticket_suggested and len(message.split()) > 5,
                "reason": f"Erreur de validation: {str(e)}. Décision conservatrice basée sur suggestion.",
                "confidence": 0.5
            }

