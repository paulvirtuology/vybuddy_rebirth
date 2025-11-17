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
        
        # Cas où on ne crée PAS de ticket (seulement si c'est une simple salutation/merci sans contexte)
        exclusion_keywords = [
            "salutation",
            "bonjour",
            "hello",
            "hi",
            "au revoir",
            "goodbye",
            "question simple",
            "information générale",
            "déjà résolu",
            "problème résolu",
            "ça fonctionne",
            "c'est bon",
            "ok"
        ]
        
        message_lower = message.lower()
        response_lower = agent_response.lower()
        
        # Vérifier les exclusions évidentes (mais pas "merci" ou "parfait" car ils peuvent être dans un contexte de création de ticket)
        for keyword in exclusion_keywords:
            # Ne pas exclure si le message contient des mots-clés de demande (création, accès, etc.)
            if keyword in message_lower or keyword in response_lower:
                # Si c'est juste une salutation simple sans contexte, exclure
                if keyword in ["salutation", "bonjour", "hello", "hi"] and len(message.split()) <= 2:
                    return {
                        "should_create": False,
                        "reason": f"Message exclu: {keyword}",
                        "confidence": 0.9
                    }
                # Pour les autres mots, vérifier s'il y a un contexte de demande
                if keyword not in ["salutation", "bonjour", "hello", "hi"]:
                    # Ne pas exclure si l'agent indique qu'il va créer/faire quelque chose
                    action_indicators = ["je m'occupe", "je vais créer", "je vais faire", "je crée", "je fais", "création", "créer", "faire"]
                    if not any(action in response_lower for action in action_indicators):
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
        
        # Vérifier si l'agent pose encore des questions (ne pas créer de ticket si c'est le cas)
        question_indicators = [
            "?", "pouvez-vous", "pourriez-vous", "auriez-vous", "avez-vous", "j'aurais besoin",
            "quel est", "quelle est", "quels sont", "quelles sont", "comment", "où", "quand",
            "pouvez vous", "pourriez vous", "auriez vous", "avez vous", "j aurais besoin",
            "vous avez", "vous les avez", "vous pouvez", "vous pourriez", "me donner",
            "me dire", "me confirmer", "me préciser", "me renseigner", "me fournir"
        ]
        
        agent_response_lower = agent_response.lower()
        is_asking_question = any(indicator in agent_response_lower for indicator in question_indicators)
        
        # Vérifier si l'agent indique qu'il va créer/faire quelque chose (signe que toutes les infos sont collectées)
        action_indicators = [
            "je m'occupe", "je vais créer", "je vais faire", "je crée", "je fais",
            "création", "créer", "faire", "je vous confirme", "je confirme",
            "notre équipe", "l'équipe va", "on va créer", "on va faire",
            "un ticket va être créé", "je vais créer un ticket", "créer un ticket",
            "ticket sera créé", "ticket va être créé", "notre équipe s'en occupe"
        ]
        is_taking_action = any(indicator in agent_response_lower for indicator in action_indicators)
        
        # Si l'agent pose une question ET ne prend pas d'action, ne PAS créer de ticket
        if is_asking_question and not is_taking_action:
            return {
                "should_create": False,
                "reason": "L'agent pose encore des questions pour obtenir les informations nécessaires. Attendre la réponse de l'utilisateur avant de créer un ticket.",
                "confidence": 0.95
            }
        
        # Si l'agent indique qu'il va créer/faire quelque chose, c'est un signe fort qu'un ticket doit être créé
        # (car le système ne peut pas créer ces choses lui-même)
        if is_taking_action and not is_asking_question:
            # Vérifier si c'est une demande qui nécessite une intervention humaine
            human_intervention_keywords = [
                "créer", "boucle", "adresse email", "compte", "accès", "licence",
                "installation", "logiciel", "ticket", "odoo"
            ]
            if any(keyword in agent_response_lower or keyword in message_lower for keyword in human_intervention_keywords):
                return {
                    "should_create": True,
                    "reason": "L'agent indique qu'il va créer/faire quelque chose qui nécessite une intervention humaine. Toutes les informations semblent collectées. Un ticket doit être créé.",
                    "confidence": 0.9
                }
        
        # Prompt pour l'évaluation LLM
        evaluation_prompt = f"""Vous êtes un validateur de tickets de support IT. Votre rôle est de déterminer si un ticket doit être créé dans Odoo.

Règles de validation CRITIQUES:
1. Créer un ticket OBLIGATOIREMENT si:
   - L'agent dit qu'il va "créer", "faire", "s'occuper de" quelque chose qui nécessite une intervention humaine (ex: "Je m'occupe de créer la boucle", "Je vais créer le compte", "Je crée le ticket")
   - TOUTES les informations nécessaires ont été collectées ET l'agent confirme qu'il va procéder
   - Le problème nécessite une intervention humaine (création de compte, boucle email, accès, permissions, matériel, installation logiciel)
   - L'utilisateur demande explicitement un ticket
   - Le problème technique n'a pas pu être résolu après diagnostic
   - Le problème est complexe et nécessite une escalade
   - L'agent a épuisé toutes les solutions possibles

2. NE PAS créer de ticket si:
   - Le problème a été résolu
   - C'est une simple question d'information
   - C'est une salutation ou un message court (sans contexte de demande)
   - L'utilisateur demande juste des informations générales
   - Le problème peut être résolu par l'utilisateur avec les instructions données
   - L'agent pose encore des questions pour obtenir des informations (sans indiquer qu'il va créer/faire quelque chose)
   - Des informations essentielles manquent (nom, email, détails du problème, etc.)

CAS SPÉCIFIQUES IMPORTANTS:
- Si l'agent dit "Je m'occupe de créer...", "Je vais créer...", "Je crée..." → CRÉER UN TICKET (le système ne peut pas créer ces choses lui-même)
- Si l'agent dit "Parfait" ou "Merci" APRÈS avoir collecté toutes les infos et indiqué qu'il va créer quelque chose → CRÉER UN TICKET
- Si l'agent dit "Parfait" ou "Merci" SANS contexte de création/action → NE PAS créer de ticket

Message utilisateur: {message}

Réponse de l'agent ({agent_used}): {agent_response}

Historique récent:
{history_context if history_context else "Aucun historique"}

L'agent a-t-il suggéré un ticket? {needs_ticket_suggested}

IMPORTANT: 
- Si l'agent indique qu'il va créer/faire quelque chose (ex: "Je m'occupe de créer..."), CRÉER UN TICKET car le système ne peut pas faire ces actions lui-même.
- Si l'agent pose encore des questions SANS indiquer qu'il va créer/faire quelque chose, NE PAS créer de ticket.

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

