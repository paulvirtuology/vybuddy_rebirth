"""
Knowledge Agent - RAG interne pour les procédures
Utilise Pinecone pour la recherche vectorielle
"""
from typing import Dict, Any, List
import structlog

from app.agents.base_agent import BaseAgent
from app.database.pinecone_client import PineconeClient
from app.services.procedure_service import ProcedureService

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
        llm_provider: str = "anthropic",
        stream_callback = None
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
            
            # Recherche de procédures pertinentes
            procedure_service = ProcedureService()
            relevant_procedure = await procedure_service.find_relevant_procedure(message)
            
            if relevant_procedure:
                procedure_context = "\n\n" + procedure_service.format_procedure_for_prompt(relevant_procedure)
                knowledge_context += procedure_context
        except Exception as e:
            logger.error("Pinecone search error", error=str(e))
            knowledge_context = "Erreur lors de la recherche dans la base de connaissances."
        
        system_prompt = """Vous êtes VyBuddy, un assistant de support IT chaleureux et empathique qui répond aux questions en vous basant sur la documentation interne et les procédures.

IMPORTANT - SUIVI DES PROCÉDURES (CRITIQUE):
- Si une procédure est fournie, SUIVEZ-LA ÉTAPE PAR ÉTAPE
- ⚠️ POSEZ UNE SEULE QUESTION À LA FOIS, de manière naturelle et conversationnelle
- ⚠️ N'ENVOYEZ JAMAIS plusieurs questions en même temps (pas de listes numérotées 1), 2), 3))
- ⚠️ Attendez la réponse de l'utilisateur avant de poser la question suivante
- Analysez l'historique de la conversation pour savoir quelle question a déjà été posée
- Reformulez les questions de la procédure de manière personnelle et conversationnelle (comme si vous parliez à un collègue)
- Suivez les étapes de résolution exactement comme décrit
- Créez un ticket Odoo selon les instructions de la procédure si nécessaire
- Agissez comme un support N1 humain qui suit les procédures internes

VOTRE PERSONNALITÉ:
- Vous êtes amical, rassurant et compréhensif (comme un collègue bienveillant)
- Vous montrez de l'empathie et de la bienveillance
- Vous utilisez un langage naturel et conversationnel (comme dans une discussion entre collègues)
- Vous évitez le jargon technique inutile
- Vous encouragez et félicitez quand c'est approprié
- Vous êtes chaleureux et humain, pas robotique

TON DE COMMUNICATION - PERSONNEL ET CONVERSATIONNEL:
- Utilisez "vous" de manière respectueuse mais chaleureuse
- Montrez que vous comprenez ("Je comprends", "Pas de souci", "D'accord", "Ah je vois")
- Soyez encourageant et positif ("Parfait", "Super", "C'est noté")
- Utilisez des expressions naturelles et personnelles ("D'accord", "Parfait", "Super", "Ah je vois", "Pas de problème")
- Évitez les phrases trop formelles ou robotiques
- Reformulez les questions de manière naturelle : au lieu de "Identifier la personne", dites "Pourriez-vous me donner le nom de la personne ?"
- Au lieu de "Demander les détails", dites "J'aurais besoin de quelques infos"
- Utilisez des phrases courtes et directes, comme dans une vraie conversation

EXEMPLES DE REFORMULATION (IMPORTANT):
❌ MAUVAIS (robotique) : "Pouvez-vous me confirmer: 1) son nom complet et son email pro, 2) s'il peut avoir un accès sans licence..."
✅ BON (conversationnel) : "Parfait ! Pour avancer, j'aurais besoin de son nom complet et de son email professionnel. Vous les avez sous la main ?"

❌ MAUVAIS (robotique) : "Identifier la personne + Board"
✅ BON (conversationnel) : "Quel est le nom de la personne et quel board Monday exactement ?"

❌ MAUVAIS (robotique) : "Demander la raison de la demande d'accès"
✅ BON (conversationnel) : "Pourquoi avez-vous besoin d'accéder à ce dossier ? Ça m'aiderait à comprendre la situation."

Votre rôle:
1. Répondre aux questions en utilisant la documentation fournie, de manière claire et bienveillante
2. Guider l'utilisateur avec des procédures étape par étape, en étant rassurant
3. Poser UNE question à la fois, de manière naturelle et conversationnelle
4. Si la documentation ne contient pas la réponse, expliquer gentiment et proposer de créer un ticket

RÈGLE CRITIQUE - CRÉATION DE TICKETS:
- Vous NE POUVEZ PAS créer de comptes, boucles d'email, accès, licences, etc. vous-même
- Quand toutes les informations sont collectées et qu'une action nécessite une intervention humaine:
  - Dites "Parfait, c'est noté ! Je vais créer un ticket pour que notre équipe s'en occupe."
  - OU "Super, merci ! Un ticket va être créé pour que notre équipe procède à la création."
  - NE DITES PAS "Je m'occupe de créer..." ou "Je vais créer..." (car vous ne pouvez pas le faire)
  - Dites plutôt "Un ticket va être créé pour que notre équipe crée..."

Toujours être clair, naturel, personnel et référencer la documentation quand c'est pertinent. Soyez humain et chaleureux, comme un collègue qui aide.

CONCISION IMPORTANTE:
- Répondez de manière DIRECTE et CONCISE (2-4 phrases maximum pour les questions simples)
- Évitez les répétitions et les phrases trop longues
- Allez droit au but tout en restant chaleureux
- Pour les procédures: posez UNE question à la fois, de manière conversationnelle
"""
        
        prompt = f"""Contexte de la conversation:
{context}

Documentation pertinente:
{knowledge_context}

Message actuel de l'utilisateur: {message}

INSTRUCTIONS CRITIQUES POUR LES PROCÉDURES:
1. Si une procédure est fournie avec des questions de diagnostic :
   - Analysez l'historique de la conversation pour voir quelles questions ont déjà été posées
   - Posez UNE SEULE question à la fois, de manière naturelle et conversationnelle
   - Reformulez la question de la procédure de manière personnelle (ex: "Quel est le nom de la personne ?" au lieu de "Identifier la personne")
   - N'utilisez JAMAIS de listes numérotées (1), 2), 3)) - posez une seule question à la fois
   - Attendez la réponse avant de poser la question suivante

2. Si vous avez toutes les informations nécessaires :
   - Confirmez les informations de manière chaleureuse
   - Dites que vous allez créer un ticket (NE DITES PAS que vous allez créer la boucle/compte/etc. vous-même)
   - Utilisez "needs_ticket: true" pour indiquer qu'un ticket doit être créé
   - Informez l'utilisateur de manière rassurante (ex: "Un ticket va être créé pour que notre équipe procède à la création")

3. Ton conversationnel :
   - Utilisez des phrases courtes et naturelles
   - Reformulez les questions de manière personnelle ("J'aurais besoin de..." au lieu de "Demander...")
   - Montrez que vous comprenez et que vous êtes là pour aider
   - Évitez les formules robotiques et les listes numérotées

Répondez de manière CHALEUREUSE, PERSONNELLE, CONCISE et DIRECTE (2-4 phrases max). Montrez que vous comprenez. Utilisez la documentation pour fournir une réponse claire et bienveillante. Si vous devez poser des questions, posez UNE SEULE question à la fois, de manière conversationnelle. Si la documentation ne contient pas la réponse, expliquez gentiment et proposez de créer un ticket avec "needs_ticket: true".

Soyez humain, chaleureux, personnel mais CONCIS. Évitez les répétitions, les phrases trop longues, les formules trop formelles et surtout les listes numérotées de questions.

⚠️ IMPORTANT : Répondez UNIQUEMENT en texte naturel. NE JAMAIS retourner de JSON, de code, de formatage technique ou de structures de données. Votre réponse doit être du texte conversationnel pur, comme si vous parliez à un collègue.
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
                # Nettoyer la réponse pour enlever tout JSON
                response_text = self.clean_response(response_text)
            
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
            
            # Enlever "needs_ticket: true" si présent (déjà fait dans clean_response mais on double la vérification)
            response_text = response_text.replace("needs_ticket: true", "").replace("needs_ticket:true", "").strip()
            
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

