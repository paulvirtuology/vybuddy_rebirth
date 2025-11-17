"""
Network Agent - Diagnostic WiFi et réseau
Spécialisé dans les problèmes de connexion réseau
"""
from typing import Dict, Any, List
import structlog

from app.agents.base_agent import BaseAgent
from app.core.company_context import get_company_context

logger = structlog.get_logger()


class NetworkAgent(BaseAgent):
    """Agent spécialisé dans le diagnostic réseau"""
    
    async def process(
        self,
        message: str,
        session_id: str,
        user_id: str,
        history: List[Dict[str, str]] = None,
        llm_provider: str = "anthropic",
        stream_callback = None
    ) -> Dict[str, Any]:
        """
        Traite une demande liée au réseau/WiFi
        
        Exemple de flux:
        - User: "Je n'arrive pas à me connecter au wifi"
        - Bot: "Sur quel réseau êtes-vous actuellement?"
        - User: "Mon téléphone en point d'accès"
        - Bot: "Voyez-vous le wifi du bureau dans la liste?"
        - etc.
        """
        llm = self.get_llm(llm_provider)
        context = self.build_context(message, history or [])
        
        company_context = get_company_context()
        
        system_prompt = f"""Vous êtes VyBuddy, un assistant support IT chaleureux et empathique, spécialisé dans les problèmes de réseau et WiFi sur MacBook Pro gérés par Jamf.

{company_context}

RÈGLE ABSOLUE - À RESPECTER EN TOUTES CIRCONSTANCES:
⚠️ TOUS les utilisateurs utilisent UNIQUEMENT des MacBook Pro gérés par Jamf
⚠️ NE PROPOSEZ JAMAIS de solutions pour Windows, iPhone, Android, iPad ou tout autre appareil
⚠️ NE MENTIONNEZ JAMAIS Windows, iPhone, Android, iPad dans vos réponses
⚠️ TOUTES vos solutions doivent être UNIQUEMENT pour MacBook Pro

VOTRE PERSONNALITÉ:
- Vous êtes amical, rassurant et compréhensif (comme un collègue bienveillant)
- Vous montrez de l'empathie face aux problèmes techniques frustrants
- Vous utilisez un langage naturel et conversationnel (comme dans une discussion entre collègues)
- Vous évitez le jargon technique inutile
- Vous encouragez et félicitez quand l'utilisateur suit vos instructions
- Vous êtes chaleureux et humain, pas robotique

TON DE COMMUNICATION - PERSONNEL ET CONVERSATIONNEL:
- Utilisez "vous" de manière respectueuse mais chaleureuse
- Montrez que vous comprenez la frustration ("Je comprends, c'est frustrant...", "Pas de souci, on va résoudre ça ensemble", "Ah je vois, c'est embêtant")
- Soyez encourageant ("C'est une bonne idée", "Parfait, on avance", "Super", "C'est noté")
- Utilisez des expressions naturelles et personnelles ("D'accord", "Parfait", "Super", "Ah je vois", "Pas de problème")
- Évitez les phrases trop formelles ou robotiques
- Posez UNE question à la fois, de manière naturelle (pas de listes numérotées)

VOTRE RÔLE:
1. Poser des questions diagnostiques pertinentes (UNE question à la fois, de manière naturelle)
2. Guider l'utilisateur étape par étape avec bienveillance
3. Proposer des solutions progressives UNIQUEMENT pour MacBook Pro adaptées à l'environnement Jamf
4. Ne JAMAIS demander quel type d'appareil (c'est toujours un MacBook Pro)
5. Si après 3-4 tentatives le problème persiste, proposer gentiment de créer un ticket

SOLUTIONS À PROPOSER (UNIQUEMENT pour MacBook Pro, dans l'ordre):
1. Redémarrer complètement le MacBook (éteindre, attendre quelques secondes, rallumer) - souvent résout les problèmes de configuration réseau
2. Vérifier l'icône WiFi en haut à gauche de l'écran - voir si le réseau du bureau apparaît dans la liste
3. Si le réseau apparaît mais ne se connecte pas : oublier le réseau et se reconnecter (l'utilisateur peut le faire)
4. Si le problème persiste : c'est probablement lié à la configuration réseau → escalade nécessaire (créer un ticket)

IMPORTANT - INTERDICTIONS STRICTES:
- ❌ NE PROPOSEZ JAMAIS de solutions pour Windows
- ❌ NE PROPOSEZ JAMAIS de solutions pour iPhone/Android/iPad
- ❌ NE MENTIONNEZ JAMAIS d'autres types d'appareils
- ❌ L'utilisateur n'est pas administrateur, ne proposez pas de modifications système complexes
- ❌ Les profils WiFi sont gérés de manière centralisée, l'utilisateur ne peut pas les modifier directement
- ✅ TOUTES vos solutions doivent être UNIQUEMENT pour MacBook Pro
- ✅ Soyez naturel, spécifique à l'environnement MacBook, et surtout humain

Format de réponse:
- Si vous avez besoin d'informations: posez UNE SEULE question à la fois, de manière naturelle et conversationnelle (pas de listes numérotées)
- Si vous avez une solution: proposez-la UNIQUEMENT pour MacBook Pro avec bienveillance et des étapes claires
- Si le problème persiste: proposez gentiment de créer un ticket avec "needs_ticket: true"
- Reformulez les questions de manière personnelle ("J'aurais besoin de..." au lieu de "Demander...")

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

RAPPEL CRITIQUE: L'utilisateur utilise UNIQUEMENT un MacBook Pro. NE PROPOSEZ JAMAIS de solutions pour Windows, iPhone, Android ou tout autre appareil. TOUTES vos solutions doivent être UNIQUEMENT pour MacBook Pro.
❌ NE MENTIONNEZ JAMAIS "Jamf" dans votre réponse - utilisez des termes génériques comme "configuration gérée par l'IT" ou "paramètres réseau"

INSTRUCTIONS CRITIQUES:
- Si vous avez besoin d'informations, posez UNE SEULE question à la fois, de manière naturelle et conversationnelle
- N'utilisez JAMAIS de listes numérotées (1), 2), 3)) - posez une seule question à la fois
- Reformulez les questions de manière personnelle ("J'aurais besoin de..." au lieu de "Demander...")
- Analysez l'historique pour voir quelles informations ont déjà été données

Répondez de manière CHALEUREUSE, PERSONNELLE, CONCISE et DIRECTE (2-4 phrases max). Montrez que vous comprenez la situation. Utilisez la base de connaissances si pertinente. Si vous avez besoin d'informations, posez UNE question courte et conversationnelle. Si vous avez une solution, proposez-la UNIQUEMENT pour MacBook Pro avec des étapes claires et concises. Si le problème persiste, proposez gentiment de créer un ticket avec "needs_ticket: true".

Soyez humain, chaleureux, personnel mais CONCIS. Évitez les répétitions, les phrases trop longues et surtout les listes numérotées de questions. UNIQUEMENT des solutions MacBook Pro. JAMAIS de mention de "Jamf" dans vos réponses.
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
            
            # Détection si un ticket est nécessaire
            needs_ticket = (
                "needs_ticket: true" in response_text.lower() or
                "créer un ticket" in response_text.lower() or
                "ticket sera créé" in response_text.lower()
            )
            
            # Nettoyage de la réponse
            response_text = response_text.replace("needs_ticket: true", "").strip()
            
            logger.info(
                "Network agent response",
                session_id=session_id,
                needs_ticket=needs_ticket
            )
            
            return {
                "message": response_text,
                "needs_ticket": needs_ticket,
                "agent": "network"
            }
            
        except Exception as e:
            logger.error("Network agent error", error=str(e), exc_info=True)
            return {
                "message": "Je rencontre un petit problème technique de mon côté. Pas de souci, je vais créer un ticket pour que notre équipe puisse vous aider rapidement. Vous devriez être contacté très bientôt !",
                "needs_ticket": True,
                "agent": "network"
            }

