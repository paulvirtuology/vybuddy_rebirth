"""
Classificateur de types de demandes basé sur un LLM.

Ce module classe les demandes utilisateur dans des catégories IT prédéfinies
en utilisant un LLM pour une classification contextuelle précise.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional

import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import settings

logger = structlog.get_logger()

SUPPORTED_TYPES = [
    "installation_logiciel",
    "wifi_probleme",
    "acces_drive",
    "creation_email",
    "licence",
    "probleme_macbook",
    "probleme_timesheet",
    "acces_monday",
    "acces_salle",
]


class RequestClassifier:
    """
    Classifie les demandes utilisateur dans des catégories IT prédéfinies.
    
    Utilise un LLM pour analyser le contexte (message, historique, agent utilisé)
    et retourner la catégorie la plus pertinente.
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            api_key=settings.OPENAI_API_KEY,
        )

    async def classify(
        self,
        message: str,
        history: List[Dict[str, str]],
        agent_used: Optional[str] = None,
    ) -> str:
        """
        Classe la demande dans une catégorie IT.
        
        Args:
            message: Le dernier message de l'utilisateur
            history: L'historique récent de la conversation
            agent_used: Le nom de l'agent qui a géré cette demande (optionnel)
        
        Returns:
            Le type de demande classifié, ou une chaîne vide si non classifié
        """
        try:
            # Construire le contexte historique
            history_text = "\n".join(
                f"Utilisateur: {m.get('user', '')}\nAgent: {m.get('bot', '')}"
                for m in history[-3:]
            ) if history else "Aucun historique"

            # Prompt structuré inspiré de l'exemple fourni
            prompt = f"""Tu es un classificateur IT. Classe ce message dans un type de demande IT.

MESSAGE:
{message}

L'agent qui a géré cette demande:
{agent_used or "Non spécifié"}

Historique récent de la conversation:
{history_text}

Réponds uniquement avec un identifiant de cette liste :
{', '.join(SUPPORTED_TYPES + ['unknown'])}

Si aucune catégorie ne correspond exactement, réponds 'unknown'.
"""

            response = await self.llm.ainvoke([
                SystemMessage(
                    content="Tu es un classificateur de requêtes IT. Réponds uniquement par un identifiant de type, sans explication ni texte supplémentaire."
                ),
                HumanMessage(content=prompt.strip()),
            ])

            candidate = response.content.strip().lower()
            
            # Nettoyer la réponse (enlever les guillemets, espaces, etc.)
            candidate = candidate.strip('"\'')
            
            if candidate in SUPPORTED_TYPES:
                logger.info(
                    "Request classified",
                    message_preview=message[:50],
                    category=candidate,
                    agent_used=agent_used,
                )
                return candidate
            
            logger.warning(
                "LLM returned unknown or invalid category",
                llm_output=candidate,
                message_preview=message[:50],
            )
            return ""
            
        except Exception as err:
            logger.warning("Request classification failed", error=str(err), message_preview=message[:50])
            return ""

