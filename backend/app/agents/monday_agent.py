"""
Monday Agent - Support Monday.com
Spécialisé dans les problèmes liés à Monday.com
Exemple d'agent pour illustrer comment ajouter un nouvel agent
"""
from typing import Dict, Any, List
import structlog

from app.agents.base_agent import BaseAgent

logger = structlog.get_logger()


class MondayAgent(BaseAgent):
    """Agent spécialisé dans Monday.com"""
    
    async def process(
        self,
        message: str,
        session_id: str,
        user_id: str,
        history: List[Dict[str, str]] = None,
        llm_provider: str = "openai"
    ) -> Dict[str, Any]:
        """
        Traite une demande liée à Monday.com
        
        Exemple d'utilisation:
        - User: "Je n'arrive pas à accéder à mon board Monday"
        - Bot: "Pouvez-vous me dire quel message d'erreur vous voyez?"
        """
        llm = self.get_llm(llm_provider)
        context = self.build_context(message, history or [])
        
        system_prompt = """Vous êtes un expert en support IT spécialisé dans Monday.com.

Votre rôle:
1. Aider avec les problèmes d'accès à Monday.com
2. Expliquer comment utiliser les fonctionnalités de Monday
3. Résoudre les problèmes de permissions et de partage
4. Guider l'utilisateur étape par étape
5. Si le problème persiste après plusieurs tentatives, indiquer qu'un ticket sera créé

Solutions courantes:
- Problèmes de connexion: vérifier les identifiants, réinitialiser le mot de passe
- Problèmes de permissions: vérifier les droits d'accès au board
- Problèmes de synchronisation: vérifier la connexion, forcer la synchronisation
- Problèmes d'intégration: vérifier les webhooks et les intégrations
- Problèmes d'affichage: vider le cache, vérifier le navigateur

Toujours être professionnel et clair. Si le problème persiste, indiquez qu'un ticket sera créé.
"""
        
        prompt = f"""Contexte de la conversation:
{context}

Message actuel de l'utilisateur: {message}

Analysez le problème Monday.com et répondez de manière appropriée. Si vous avez besoin d'informations, posez UNE question à la fois. Si vous avez une solution, proposez-la clairement avec des étapes.
"""
        
        try:
            response = await llm.ainvoke(prompt)
            response_text = response.content
            
            needs_ticket = (
                "needs_ticket: true" in response_text.lower() or
                "créer un ticket" in response_text.lower() or
                "ticket sera créé" in response_text.lower()
            )
            
            response_text = response_text.replace("needs_ticket: true", "").strip()
            
            logger.info(
                "Monday agent response",
                session_id=session_id,
                needs_ticket=needs_ticket
            )
            
            return {
                "message": response_text,
                "needs_ticket": needs_ticket,
                "agent": "monday"
            }
            
        except Exception as e:
            logger.error("Monday agent error", error=str(e), exc_info=True)
            return {
                "message": "Une erreur est survenue lors du diagnostic Monday.com. Un ticket va être créé.",
                "needs_ticket": True,
                "agent": "monday"
            }

