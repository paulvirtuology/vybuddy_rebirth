"""
Knowledge Agent - RAG interne pour les procédures
Utilise Pinecone pour la recherche vectorielle
"""
from typing import Dict, Any, List
import structlog

from app.agents.base_agent import BaseAgent
from app.database.pinecone_client import PineconeClient

logger = structlog.get_logger()


class KnowledgeAgent(BaseAgent):
    """Agent spécialisé dans la recherche de connaissances (RAG)"""
    
    def __init__(self):
        super().__init__()
        self.pinecone = PineconeClient()
    
    async def process(
        self,
        message: str,
        session_id: str,
        user_id: str,
        history: List[Dict[str, str]] = None,
        llm_provider: str = "anthropic"
    ) -> Dict[str, Any]:
        """
        Traite une demande de connaissances/procédures avec RAG
        """
        llm = self.get_llm(llm_provider)
        context = self.build_context(message, history or [])
        
        # Recherche vectorielle dans Pinecone
        try:
            relevant_docs = await self.pinecone.search(message, top_k=3)
            knowledge_context = "\n\n".join([
                f"Document {i+1}: {doc.get('text', '')}"
                for i, doc in enumerate(relevant_docs)
            ]) if relevant_docs else "Aucune documentation pertinente trouvée."
        except Exception as e:
            logger.error("Pinecone search error", error=str(e))
            knowledge_context = "Erreur lors de la recherche dans la base de connaissances."
        
        system_prompt = """Vous êtes VyBuddy, un assistant de support IT chaleureux et empathique qui répond aux questions en vous basant sur la documentation interne et les procédures.

VOTRE PERSONNALITÉ:
- Vous êtes amical, rassurant et compréhensif
- Vous montrez de l'empathie et de la bienveillance
- Vous utilisez un langage naturel et conversationnel (comme un collègue bienveillant)
- Vous évitez le jargon technique inutile
- Vous encouragez et félicitez quand c'est approprié

TON DE COMMUNICATION:
- Utilisez "vous" de manière respectueuse mais chaleureuse
- Montrez que vous comprenez ("Je comprends", "Pas de souci", "D'accord")
- Soyez encourageant et positif
- Utilisez des expressions naturelles ("Parfait", "Super", "Ah je vois")
- Évitez les phrases trop formelles ou robotiques

Votre rôle:
1. Répondre aux questions en utilisant la documentation fournie, de manière claire et bienveillante
2. Guider l'utilisateur avec des procédures étape par étape, en étant rassurant
3. Si la documentation ne contient pas la réponse, expliquer gentiment et proposer de créer un ticket

Toujours être clair, naturel, et référencer la documentation quand c'est pertinent. Soyez humain et chaleureux.
"""
        
        prompt = f"""Contexte de la conversation:
{context}

Documentation pertinente:
{knowledge_context}

Question de l'utilisateur: {message}

Répondez de manière chaleureuse, naturelle et empathique. Montrez que vous comprenez la question de l'utilisateur. Utilisez la documentation pour fournir une réponse claire et bienveillante. Si la documentation ne contient pas la réponse, expliquez gentiment et proposez de créer un ticket avec "needs_ticket: true".

Soyez humain, chaleureux et rassurant dans votre réponse. Évitez les phrases trop formelles.
"""
        
        try:
            response = await llm.ainvoke(prompt)
            response_text = response.content
            
            # Ne pas créer de ticket pour des messages trop courts ou des salutations
            is_simple_message = len(message.strip().split()) <= 3
            
            needs_ticket = (
                not is_simple_message and (
                    "needs_ticket: true" in response_text.lower() or
                    "créer un ticket" in response_text.lower() or
                    "ticket sera créé" in response_text.lower() or
                    (not relevant_docs and len(message.strip()) > 10)  # Seulement si message significatif
                )
            )
            
            response_text = response_text.replace("needs_ticket: true", "").strip()
            
            logger.info(
                "Knowledge agent response",
                session_id=session_id,
                needs_ticket=needs_ticket,
                docs_found=len(relevant_docs) if relevant_docs else 0
            )
            
            return {
                "message": response_text,
                "needs_ticket": needs_ticket,
                "agent": "knowledge",
                "metadata": {
                    "docs_used": len(relevant_docs) if relevant_docs else 0
                }
            }
            
        except Exception as e:
            logger.error("Knowledge agent error", error=str(e), exc_info=True)
            return {
                "message": "Je rencontre un petit problème technique de mon côté. Pas de souci, je vais créer un ticket pour que notre équipe puisse vous aider rapidement. Vous devriez être contacté très bientôt !",
                "needs_ticket": True,
                "agent": "knowledge"
            }

