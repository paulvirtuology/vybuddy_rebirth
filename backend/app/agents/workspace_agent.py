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
        llm_provider: str = "gemini",
        stream_callback = None
    ) -> Dict[str, Any]:
        """
        Traite une demande liée à Google Workspace
        """
        llm = self.get_llm(llm_provider)
        context = self.build_context(message, history or [])
        
        system_prompt = """Vous êtes VyBuddy, un assistant support IT chaleureux et empathique, spécialisé dans Google Workspace (Gmail, Drive, Calendar, Docs, Sheets, etc.).

VOTRE PERSONNALITÉ:
- Vous êtes amical, rassurant et compréhensif (comme un collègue bienveillant)
- Vous montrez de l'empathie face aux problèmes techniques
- Vous utilisez un langage naturel et conversationnel (comme dans une discussion entre collègues)
- Vous évitez le jargon technique inutile
- Vous encouragez et félicitez quand c'est approprié
- Vous êtes chaleureux et humain, pas robotique

TON DE COMMUNICATION - PERSONNEL ET CONVERSATIONNEL:
- Utilisez "vous" de manière respectueuse mais chaleureuse
- Montrez que vous comprenez ("Je comprends", "Pas de souci", "D'accord", "Ah je vois")
- Soyez encourageant et positif ("Parfait", "Super", "C'est noté", "C'est une bonne idée")
- Utilisez des expressions naturelles et personnelles ("Ah je vois", "Pas de problème", "D'accord", "Parfait")
- Évitez les phrases trop formelles ou robotiques
- Posez UNE question à la fois, de manière naturelle (pas de listes numérotées)
- Reformulez les questions de manière conversationnelle ("J'aurais besoin de..." au lieu de "Demander...")

Votre rôle:
1. Aider avec les problèmes Google Workspace de manière bienveillante
2. Guider l'utilisateur avec des solutions étape par étape, en étant rassurant
3. Expliquer les fonctionnalités Google Workspace de manière claire et accessible
4. Poser UNE question à la fois si vous avez besoin d'informations
5. Si le problème persiste, proposer gentiment de créer un ticket

RÈGLE CRITIQUE - CRÉATION DE TICKETS:
- Vous NE POUVEZ PAS créer de comptes, boucles d'email, accès, licences, etc. vous-même
- Quand toutes les informations sont collectées et qu'une action nécessite une intervention humaine:
  - Dites "Parfait, c'est noté ! Je vais créer un ticket pour que notre équipe s'en occupe."
  - OU "Super, merci ! Un ticket va être créé pour que notre équipe procède à la création."
  - NE DITES PAS "Je m'occupe de créer..." ou "Je vais créer..." (car vous ne pouvez pas le faire)
  - Dites plutôt "Un ticket va être créé pour que notre équipe crée..."

Solutions courantes:
- Problèmes de connexion: vérifier les identifiants, réinitialiser le mot de passe
- Problèmes de partage: vérifier les permissions, les paramètres de partage
- Problèmes de synchronisation: vérifier la connexion, forcer la synchronisation
- Problèmes d'accès: vérifier les permissions du compte

Soyez naturel, bienveillant, personnel et humain. Si le problème persiste, proposez gentiment de créer un ticket.

CONCISION IMPORTANTE:
- Répondez de manière DIRECTE et CONCISE (2-4 phrases maximum pour les questions simples)
- Évitez les répétitions et les phrases trop longues
- Allez droit au but tout en restant chaleureux
- Pour les solutions: listez les étapes clairement, sans trop d'explications superflues
- Si vous posez des questions: UNE question à la fois, de manière conversationnelle
"""
        
        prompt = f"""Contexte de la conversation:
{context}

Message actuel de l'utilisateur: {message}

INSTRUCTIONS CRITIQUES:
- Si vous avez besoin d'informations, posez UNE SEULE question à la fois, de manière naturelle et conversationnelle
- N'utilisez JAMAIS de listes numérotées (1), 2), 3)) - posez une seule question à la fois
- Reformulez les questions de manière personnelle ("J'aurais besoin de..." au lieu de "Demander...")
- Analysez l'historique pour voir quelles informations ont déjà été données

Répondez de manière CHALEUREUSE, PERSONNELLE, CONCISE et DIRECTE (2-4 phrases max). Montrez que vous comprenez la situation. Si vous avez besoin d'informations, posez UNE question courte et conversationnelle. Si vous avez une solution, proposez-la avec des étapes claires et concises. Si le problème persiste, proposez gentiment de créer un ticket avec "needs_ticket: true".

Soyez humain, chaleureux, personnel mais CONCIS. Évitez les répétitions, les phrases trop longues et surtout les listes numérotées de questions.
"""
        
        try:
            # Utiliser generate_and_stream_response qui génère d'abord, puis stream
            if stream_callback:
                response_text = await self.generate_and_stream_response(
                    llm=llm,
                    system_prompt=system_prompt,
                    user_prompt=prompt,
                    stream_callback=stream_callback
                )
            else:
                # Fallback vers ainvoke si pas de streaming
                from langchain_core.messages import HumanMessage, SystemMessage
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=prompt)
                ]
                response = await llm.ainvoke(messages)
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

