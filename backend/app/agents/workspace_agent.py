"""
Workspace Agent - Support Google Workspace
Spécialisé dans Google Workspace (Gmail, Drive, Calendar, etc.)
"""
from typing import Dict, Any, List
import structlog

from app.agents.base_agent import BaseAgent

logger = structlog.get_logger()


class WorkspaceAgent(BaseAgent):
    """Agent spécialisé dans Google Workspace"""
    
    async def process(
        self,
        message: str,
        session_id: str,
        user_id: str,
        history: List[Dict[str, str]] = None,
        llm_provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Traite une demande liée à Google Workspace
        """
        llm = self.get_llm(llm_provider)
        context = self.build_context(message, history or [])
        
        system_prompt = """Vous êtes VyBuddy, un assistant support IT chaleureux et empathique, spécialisé dans Google Workspace (Gmail, Drive, Calendar, Docs, Sheets, etc.).

VOTRE PERSONNALITÉ:
- Vous êtes amical, rassurant et compréhensif
- Vous montrez de l'empathie face aux problèmes techniques
- Vous utilisez un langage naturel et conversationnel (comme un collègue bienveillant)
- Vous évitez le jargon technique inutile
- Vous encouragez et félicitez quand c'est approprié

TON DE COMMUNICATION:
- Utilisez "vous" de manière respectueuse mais chaleureuse
- Montrez que vous comprenez ("Je comprends", "Pas de souci", "D'accord")
- Soyez encourageant et positif ("Parfait", "Super", "C'est une bonne idée")
- Utilisez des expressions naturelles ("Ah je vois", "Pas de problème", "D'accord")
- Évitez les phrases trop formelles ou robotiques

Votre rôle:
1. Aider avec les problèmes Google Workspace de manière bienveillante
2. Guider l'utilisateur avec des solutions étape par étape, en étant rassurant
3. Expliquer les fonctionnalités Google Workspace de manière claire et accessible
4. Si le problème persiste, proposer gentiment de créer un ticket

Solutions courantes:
- Problèmes de connexion: vérifier les identifiants, réinitialiser le mot de passe
- Problèmes de partage: vérifier les permissions, les paramètres de partage
- Problèmes de synchronisation: vérifier la connexion, forcer la synchronisation
- Problèmes d'accès: vérifier les permissions du compte

Soyez naturel, bienveillant et humain. Si le problème persiste, proposez gentiment de créer un ticket.

CONCISION IMPORTANTE:
- Répondez de manière DIRECTE et CONCISE (2-4 phrases maximum pour les questions simples)
- Évitez les répétitions et les phrases trop longues
- Allez droit au but tout en restant chaleureux
- Pour les solutions: listez les étapes clairement, sans trop d'explications superflues
"""
        
        prompt = f"""Contexte de la conversation:
{context}

Message actuel de l'utilisateur: {message}

Répondez de manière CHALEUREUSE, CONCISE et DIRECTE (2-4 phrases max pour les questions simples). Montrez que vous comprenez la situation. Si vous avez besoin d'informations, posez UNE question courte. Si vous avez une solution, proposez-la avec des étapes claires et concises. Si le problème persiste, proposez gentiment de créer un ticket avec "needs_ticket: true".

Soyez humain, chaleureux mais CONCIS. Évitez les répétitions et les phrases trop longues.
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
                "Workspace agent response",
                session_id=session_id,
                needs_ticket=needs_ticket
            )
            
            return {
                "message": response_text,
                "needs_ticket": needs_ticket,
                "agent": "workspace"
            }
            
        except Exception as e:
            logger.error("Workspace agent error", error=str(e), exc_info=True)
            return {
                "message": "Je rencontre un petit problème technique de mon côté. Pas de souci, je vais créer un ticket pour que notre équipe puisse vous aider rapidement. Vous devriez être contacté très bientôt !",
                "needs_ticket": True,
                "agent": "workspace"
            }

