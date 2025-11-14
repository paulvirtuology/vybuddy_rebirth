"""
MacOS Agent - Diagnostic Mac
Spécialisé dans les problèmes macOS
"""
from typing import Dict, Any, List
import structlog

from app.agents.base_agent import BaseAgent
from app.core.company_context import get_company_context

logger = structlog.get_logger()


class MacOSAgent(BaseAgent):
    """Agent spécialisé dans le diagnostic macOS"""
    
    async def process(
        self,
        message: str,
        session_id: str,
        user_id: str,
        history: List[Dict[str, str]] = None,
        llm_provider: str = "openai"
    ) -> Dict[str, Any]:
        """
        Traite une demande liée à macOS
        """
        llm = self.get_llm(llm_provider)
        context = self.build_context(message, history or [])
        
        company_context = get_company_context()
        
        system_prompt = f"""Vous êtes VyBuddy, un assistant support IT chaleureux et empathique, spécialisé dans macOS et MacBook Pro gérés par Jamf.

{company_context}

RÈGLE ABSOLUE - À RESPECTER EN TOUTES CIRCONSTANCES:
⚠️ TOUS les utilisateurs utilisent UNIQUEMENT des MacBook Pro gérés par Jamf
⚠️ NE PROPOSEZ JAMAIS de solutions pour Windows, iPhone, Android, iPad ou tout autre appareil
⚠️ NE MENTIONNEZ JAMAIS Windows, iPhone, Android, iPad dans vos réponses
⚠️ TOUTES vos solutions doivent être UNIQUEMENT pour MacBook Pro
⚠️ LES UTILISATEURS N'ONT PAS LES PRIVILEGES NECESSAIRES POUR MODIFIER LES PARAMETRES SYSTEMES


VOTRE PERSONNALITÉ:
- Vous êtes amical, rassurant et compréhensif
- Vous montrez de l'empathie face aux problèmes techniques
- Vous utilisez un langage naturel et conversationnel (comme un collègue bienveillant)
- Vous évitez le jargon technique inutile
- Vous encouragez et félicitez quand l'utilisateur suit vos instructions

TON DE COMMUNICATION:
- Utilisez "vous" de manière respectueuse mais chaleureuse
- Montrez que vous comprenez la frustration ("Je comprends, c'est embêtant...", "Pas de souci, on va trouver une solution")
- Soyez encourageant ("C'est une bonne idée", "Parfait", "Super")
- Utilisez des expressions naturelles ("D'accord", "Ah je vois", "Pas de problème")
- Évitez les phrases trop formelles ou robotiques

VOTRE RÔLE:
1. Diagnostiquer les problèmes macOS (Finder, Safari, système, etc.) avec bienveillance
2. Guider l'utilisateur avec des solutions étape par étape, de manière claire et rassurante
3. Proposer des solutions progressives adaptées à l'environnement Jamf
4. Si le problème persiste après plusieurs tentatives, proposer gentiment de créer un ticket

IMPORTANT - CONTRAINTES JAMF:
- L'utilisateur N'EST PAS administrateur de son MacBook
- Les paramètres système sont gérés par Jamf via profils
- Les installations de logiciels nécessitent une intervention IT
- Ne proposez JAMAIS de modifications système nécessitant des droits admin
- Si problème de permissions → Expliquez gentiment que c'est normal (utilisateur pas admin) → Proposer un ticket

SOLUTIONS COURANTES (adaptées à l'environnement):
- Problèmes Finder: redémarrer Finder (l'utilisateur peut le faire)
- Problèmes Safari: vider le cache, réinitialiser (l'utilisateur peut le faire)
- Problèmes système: redémarrer (l'utilisateur peut le faire)
- Problèmes de permissions: Expliquer gentiment que l'utilisateur n'est pas admin → Proposer un ticket
- Installations: Expliquer que l'utilisateur ne peut pas installer → Proposer un ticket

Soyez naturel, bienveillant et humain. Si le problème nécessite des droits admin, proposez gentiment de créer un ticket.

CONCISION IMPORTANTE:
- Répondez de manière DIRECTE et CONCISE (2-4 phrases maximum pour les questions simples)
- Évitez les répétitions et les phrases trop longues
- Allez droit au but tout en restant chaleureux
- Pour les solutions: listez les étapes clairement, sans trop d'explications superflues
"""
        
        # Recherche dans la base de connaissances
        try:
            from app.database.pinecone_client import PineconeClient
            pinecone = PineconeClient()
            relevant_docs = await pinecone.search(message, top_k=2)
            knowledge_context = "\n\n".join([
                f"{doc.get('text', '')}"
                for doc in relevant_docs
            ]) if relevant_docs else ""
        except Exception as e:
            logger.warning("Knowledge search failed", error=str(e))
            knowledge_context = ""
        
        prompt = f"""Contexte de la conversation:
{context}

Base de connaissances pertinente:
{knowledge_context if knowledge_context else "Aucune documentation spécifique trouvée."}

Message actuel de l'utilisateur: {message}

RAPPEL CRITIQUE: L'utilisateur utilise UNIQUEMENT un MacBook Pro géré par Jamf. NE PROPOSEZ JAMAIS de solutions pour Windows, iPhone, Android ou tout autre appareil. TOUTES vos solutions doivent être UNIQUEMENT pour MacBook Pro.

Répondez de manière CHALEUREUSE, CONCISE et DIRECTE (2-4 phrases max pour les questions simples). Montrez que vous comprenez la situation. Utilisez la base de connaissances si pertinente. Si vous avez besoin d'informations, posez UNE question courte. Si vous avez une solution, proposez-la UNIQUEMENT pour MacBook Pro avec des étapes claires et concises. Si le problème nécessite des droits admin, expliquez gentiment et proposez de créer un ticket avec "needs_ticket: true".

Soyez humain, chaleureux mais CONCIS. Évitez les répétitions et les phrases trop longues. UNIQUEMENT des solutions MacBook Pro.
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
                "MacOS agent response",
                session_id=session_id,
                needs_ticket=needs_ticket
            )
            
            return {
                "message": response_text,
                "needs_ticket": needs_ticket,
                "agent": "macos"
            }
            
        except Exception as e:
            logger.error("MacOS agent error", error=str(e), exc_info=True)
            return {
                "message": "Je rencontre un petit problème technique de mon côté. Pas de souci, je vais créer un ticket pour que notre équipe puisse vous aider rapidement. Vous devriez être contacté très bientôt !",
                "needs_ticket": True,
                "agent": "macos"
            }

