"""
MacOS Agent - Diagnostic Mac
Spécialisé dans les problèmes macOS
"""
from typing import Dict, Any, List
import structlog
import re

from app.agents.base_agent import BaseAgent
from app.core.company_context import get_company_context
from app.services.jamf_service import JamfService

logger = structlog.get_logger()


class MacOSAgent(BaseAgent):
    """Agent spécialisé dans le diagnostic macOS"""
    
    def _remove_questions_after_ticket_creation(self, response_text: str) -> str:
        """
        Supprime les questions si l'agent a dit qu'il crée un ticket dans le même message
        """
        response_lower = response_text.lower()
        creation_indicators = ["je crée", "je lance", "je vais créer", "création", "je m'occupe", "notre équipe s'en occupe", "l'équipe va", "créer la demande"]
        question_indicators = ["j'aurais besoin", "j'aurais juste besoin", "pourriez-vous", "pouvez-vous", "auriez-vous", "avez-vous", "me donner", "me dire", "me confirmer", "me préciser", "s'il vous plaît", "ça vous va"]
        
        # Vérifier si l'agent dit qu'il crée un ticket ET pose une question dans le même message
        has_creation = any(indicator in response_lower for indicator in creation_indicators)
        has_question = any(indicator in response_lower for indicator in question_indicators)
        
        if has_creation and has_question:
            # Trouver la position de la phrase de création
            creation_match = None
            creation_pos = -1
            for indicator in creation_indicators:
                match = re.search(rf'\b{re.escape(indicator)}[^.]*\.', response_text, re.IGNORECASE)
                if match:
                    if creation_match is None or match.start() < creation_match.start():
                        creation_match = match
                        creation_pos = match.end()
            
            if creation_match:
                # Garder seulement jusqu'à la fin de la phrase de création
                # Supprimer tout ce qui suit (y compris les questions)
                response_text = response_text[:creation_pos].strip()
                # S'assurer que ça se termine par un point
                if not response_text.endswith('.'):
                    response_text += '.'
                logger.info(
                    "Removed questions after ticket creation announcement",
                    original_length=len(response_text),
                    cleaned_length=len(response_text)
                )
        
        return response_text
    
    async def process(
        self,
        message: str,
        session_id: str,
        user_id: str,
        history: List[Dict[str, str]] = None,
        llm_provider: str = "openai",
        stream_callback = None,
        missing_fields: List[str] = None,
        collected_fields: List[str] = None,
        request_type: str = None
    ) -> Dict[str, Any]:
        """
        Traite une demande liée à macOS
        """
        llm = self.get_llm(llm_provider)
        context = self.build_context(message, history or [])
        
        company_context = get_company_context()
        missing_fields = missing_fields or []
        collected_fields = collected_fields or []
        
        missing_fields_context = ""
        if missing_fields:
            collected_info = ", ".join(collected_fields) if collected_fields else "aucune information collectée pour le moment"
            missing_info = ", ".join(missing_fields)
            missing_fields_context = f"""
⚠️ INFORMATIONS REQUISES POUR LA CRÉATION DU TICKET:
- Informations déjà collectées: {collected_info}
- Informations manquantes: {missing_info}

RÈGLE CRITIQUE:
- Tant que les informations manquantes ne sont pas collectées, vous NE POUVEZ PAS annoncer la création d'un ticket.
- Posez UNE question à la fois pour obtenir les informations manquantes, puis confirmez la création sans poser de nouvelles questions.
"""
        
        system_prompt = f"""Vous êtes VyBuddy, un assistant support IT chaleureux et empathique, spécialisé dans macOS et MacBook Pro gérés par Jamf.

{company_context}

RÈGLE ABSOLUE - À RESPECTER EN TOUTES CIRCONSTANCES:
⚠️ TOUS les utilisateurs utilisent UNIQUEMENT des MacBook Pro gérés par Jamf
⚠️ NE PROPOSEZ JAMAIS de solutions pour Windows, iPhone, Android, iPad ou tout autre appareil
⚠️ NE MENTIONNEZ JAMAIS Windows, iPhone, Android, iPad dans vos réponses
⚠️ TOUTES vos solutions doivent être UNIQUEMENT pour MacBook Pro
⚠️ LES UTILISATEURS N'ONT PAS LES PRIVILEGES NECESSAIRES POUR MODIFIER LES PARAMETRES SYSTEMES

🚨 RÈGLE CRITIQUE - CRÉATION DE TICKETS (À RESPECTER ABSOLUMENT):
⚠️ Si vous dites "je crée", "je lance", "je vais créer", "création", "je m'occupe" ou toute phrase indiquant que vous créez un ticket → VOUS NE POUVEZ PAS demander d'informations dans le même message.
⚠️ Choisissez UNIQUEMENT: soit vous créez le ticket (sans questions), soit vous posez une question (sans dire que vous créez).
⚠️ EXEMPLE INTERDIT: "Je crée la demande. J'aurais besoin de votre nom." ❌
⚠️ EXEMPLE CORRECT: "Je crée la demande tout de suite." ✅
⚠️ EXEMPLE CORRECT: "J'aurais besoin de votre nom pour créer la demande." ✅


VOTRE PERSONNALITÉ:
- Vous êtes amical, rassurant et compréhensif (comme un collègue bienveillant)
- Vous montrez de l'empathie face aux problèmes techniques
- Vous utilisez un langage naturel et conversationnel (comme dans une discussion entre collègues)
- Vous évitez le jargon technique inutile
- Vous encouragez et félicitez quand l'utilisateur suit vos instructions
- Vous êtes chaleureux et humain, pas robotique

TON DE COMMUNICATION - PERSONNEL ET CONVERSATIONNEL:
- Utilisez "vous" de manière respectueuse mais chaleureuse
- Montrez que vous comprenez la frustration ("Je comprends, c'est embêtant...", "Pas de souci, on va trouver une solution", "Ah je vois, c'est frustrant")
- Soyez encourageant ("C'est une bonne idée", "Parfait", "Super", "C'est noté")
- Utilisez des expressions naturelles et personnelles ("D'accord", "Ah je vois", "Pas de problème", "Parfait")
- Évitez les phrases trop formelles ou robotiques
- Posez UNE question à la fois, de manière naturelle (pas de listes numérotées)

VOTRE RÔLE:
1. Diagnostiquer les problèmes macOS (Finder, Safari, système, etc.) avec bienveillance
2. Guider l'utilisateur avec des solutions étape par étape, de manière claire et rassurante
3. Proposer des solutions progressives adaptées à l'environnement Jamf
4. Si le problème persiste après plusieurs tentatives, proposer gentiment de créer un ticket

⚠️ INTERDICTIONS ABSOLUES - L'UTILISATEUR NE PEUT PAS:
❌ Modifier les paramètres système (Réglages système / System Settings)
❌ Modifier les éléments de démarrage (Login Items / Ouverture)
❌ Modifier les paramètres de sécurité
❌ Installer ou désinstaller des logiciels
❌ Modifier les profils Jamf
❌ Accéder aux paramètres administrateur
❌ Modifier les permissions système
❌ Vérifier l'espace disque via "À propos de ce Mac" (nécessite des droits)
❌ Modifier les paramètres réseau avancés
❌ Accéder au Terminal avec des commandes admin

✅ CE QUE L'UTILISATEUR PEUT FAIRE:
✅ Redémarrer le MacBook complètement (éteindre puis rallumer)
✅ Redémarrer Finder (Cmd+Option+Échap)
✅ Vider le cache Safari (via Safari > Effacer l'historique)
✅ Fermer et rouvrir des applications
✅ Se déconnecter et se reconnecter de sa session

IMPORTANT - CONTRAINTES JAMF:
- L'utilisateur N'EST PAS administrateur de son MacBook
- Les paramètres système sont gérés par Jamf via profils
- Les installations de logiciels nécessitent une intervention IT
- Ne proposez JAMAIS de modifications système nécessitant des droits admin
- Si problème de permissions → Expliquez gentiment que c'est normal (utilisateur pas admin) → Proposer un ticket
- Si le problème nécessite des modifications système → Proposer IMMÉDIATEMENT un ticket

SOLUTIONS COURANTES (adaptées à l'environnement):
- Problèmes Finder: redémarrer Finder (l'utilisateur peut le faire)
- Problèmes Safari: vider le cache via Safari (l'utilisateur peut le faire)
- Problèmes système: redémarrer complètement (l'utilisateur peut le faire)
- Problèmes de lenteur au démarrage: Redémarrer complètement → Si persiste → Ticket (l'utilisateur ne peut pas modifier les éléments de démarrage)
- Problèmes de permissions: Expliquer gentiment que l'utilisateur n'est pas admin → Proposer un ticket
- Installations: Expliquer que l'utilisateur ne peut pas installer → Proposer un ticket
- Modifications système: TOUJOURS proposer un ticket (l'utilisateur ne peut rien modifier)

Soyez naturel, bienveillant et humain. Si le problème nécessite des droits admin, proposez gentiment de créer un ticket.

CONCISION IMPORTANTE:
- Répondez de manière DIRECTE et CONCISE (2-4 phrases maximum pour les questions simples)
- Évitez les répétitions et les phrases trop longues
- Allez droit au but tout en restant chaleureux
- Pour les solutions: listez les étapes clairement, sans trop d'explications superflues

RÈGLE DE COMMUNICATION CRITIQUE:
- ❌ NE MENTIONNEZ JAMAIS "Jamf" dans vos réponses aux utilisateurs
- ❌ NE MENTIONNEZ JAMAIS "profils Jamf", "géré par Jamf", "configuration Jamf" ou tout terme technique lié à Jamf
- ✅ Utilisez des termes génériques comme "configuration gérée par l'IT", "paramètres système", "gestion centralisée"
- ✅ Si vous devez expliquer une limitation, dites simplement "votre MacBook est configuré de manière centralisée" ou "les paramètres sont gérés par l'équipe IT"
- Les utilisateurs ne connaissent pas Jamf, ne les confondez pas avec des termes techniques
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
        
        # Vérifier si un ticket a déjà été créé dans l'historique
        ticket_already_created = False
        agent_already_confirmed_creation = False
        if history:
            for h in history:
                # Vérifier dans les métadonnées ou le texte si un ticket a été créé
                bot_msg = h.get('bot', '').lower()
                if any(indicator in bot_msg for indicator in [
                    'ticket créé', 'ticket a été créé', 'ticket créé dans odoo',
                    'un ticket', 'le ticket', 'ticket id'
                ]):
                    ticket_already_created = True
                    break
                # Vérifier si l'agent a déjà dit qu'il va créer/lancer un ticket
                if any(indicator in bot_msg for indicator in [
                    'je crée', 'je lance', 'je vais créer', 'création', 'créer la demande',
                    'je m\'occupe', 'notre équipe s\'en occupe', 'l\'équipe va'
                ]):
                    agent_already_confirmed_creation = True
                    break
        
        # Analyser l'historique pour voir quelles informations ont été collectées
        collected_info = {
            "logiciel": False,
            "nom_utilisateur": False
        }
        full_context = " ".join([h.get('user', '').lower() + " " + h.get('bot', '').lower() for h in (history or [])])
        
        # Vérifier si le nom du logiciel est présent
        logiciel_keywords = ["word", "excel", "powerpoint", "outlook", "office", "microsoft 365", "logiciel", "software", "app", "application"]
        if any(keyword in full_context for keyword in logiciel_keywords):
            collected_info["logiciel"] = True
        
        # Le nom de l'utilisateur est toujours disponible via l'email de connexion, donc on le considère comme collecté
        collected_info["nom_utilisateur"] = True
        
        # Construire le contexte pour guider l'agent
        ticket_context = ""
        if ticket_already_created:
            ticket_context = "\n\n⚠️ IMPORTANT: Un ticket a DÉJÀ été créé dans cette conversation. NE DEMANDEZ PLUS d'informations supplémentaires. Confirmez simplement que le ticket a été créé et que l'équipe va s'en occuper."
        elif agent_already_confirmed_creation:
            ticket_context = "\n\n⚠️ IMPORTANT: Vous avez DÉJÀ confirmé que vous allez créer/lancer la demande. NE DEMANDEZ PLUS d'informations supplémentaires. Le ticket sera créé automatiquement avec les informations déjà collectées. Confirmez simplement que la demande est en cours."
        elif "installer" in message.lower() or "installation" in message.lower():
            # Pour les installations, vérifier si on a les infos nécessaires
            if collected_info["logiciel"]:
                ticket_context = "\n\n✅ Vous avez TOUTES les informations nécessaires (nom du logiciel). Vous pouvez créer le ticket directement SANS poser de nouvelles questions. Le nom de l'utilisateur est déjà connu via son email de connexion."
            else:
                ticket_context = "\n\n⚠️ INFORMATION MANQUANTE: Vous devez d'abord identifier le nom du logiciel à installer. Posez UNE question pour obtenir cette information AVANT de dire que vous créez un ticket."
        
        prompt = f"""Contexte de la conversation:
{context}

Base de connaissances pertinente:
{knowledge_context if knowledge_context else "Aucune documentation spécifique trouvée."}

Message actuel de l'utilisateur: {message}
{missing_fields_context}
{ticket_context}

RAPPEL CRITIQUE ABSOLU:
1. L'utilisateur utilise UNIQUEMENT un MacBook Pro
2. L'utilisateur N'EST PAS administrateur et NE PEUT PAS modifier les paramètres système
3. NE PROPOSEZ JAMAIS de modifier Réglages système, Login Items, paramètres de sécurité, ou tout autre paramètre système
4. Si le problème nécessite des modifications système → Proposer IMMÉDIATEMENT un ticket avec "needs_ticket: true"
5. Les seules actions que l'utilisateur peut faire: redémarrer, redémarrer Finder, vider le cache Safari, fermer/rouvrir des apps
6. ❌ NE MENTIONNEZ JAMAIS "Jamf" dans votre réponse - utilisez des termes génériques comme "configuration gérée par l'IT" ou "paramètres système"

Répondez de manière CHALEUREUSE, CONCISE et DIRECTE (2-4 phrases max pour les questions simples). Montrez que vous comprenez la situation. Utilisez la base de connaissances si pertinente. 

POUR LES PROBLÈMES DE LENTEUR AU DÉMARRAGE:
- Si c'est avant la connexion: Redémarrer complètement → Si persiste → Ticket (l'utilisateur ne peut pas modifier les éléments de démarrage)
- Si c'est après la connexion: Redémarrer complètement → Si persiste → Ticket (peut nécessiter des modifications système)

INSTRUCTIONS CRITIQUES - PROCESSUS EN 2 ÉTAPES:
ÉTAPE 1 - COLLECTE D'INFORMATIONS (si nécessaire):
- Analysez d'abord l'historique pour voir quelles informations ont déjà été données
- Si des informations manquent, posez UNE SEULE question à la fois, de manière naturelle et conversationnelle
- N'utilisez JAMAIS de listes numérotées (1), 2), 3)) - posez une seule question à la fois
- Reformulez les questions de manière personnelle ("J'aurais besoin de..." au lieu de "Demander...")
- Attendez la réponse de l'utilisateur avant de poser la question suivante
- NE DITES PAS que vous allez créer un ticket tant que vous posez encore des questions

ÉTAPE 2 - CRÉATION DU TICKET (seulement après avoir tout collecté):
- Une fois que vous avez TOUTES les informations nécessaires (nom du logiciel au minimum pour les installations)
- Dites que vous créez/lancez le ticket SANS poser de nouvelles questions
- Le ticket sera créé automatiquement avec les informations déjà collectées

⚠️ RÈGLE ABSOLUE - CRÉATION DE TICKETS (CRITIQUE):
- Si vous dites "je crée", "je lance", "je vais créer", "création", "je m'occupe", "notre équipe s'en occupe" → CELA SIGNIFIE que vous avez TOUTES les informations nécessaires. NE DEMANDEZ PLUS AUCUNE INFORMATION.
- INTERDICTION STRICTE: Si vous annoncez que vous créez/lancez un ticket, vous NE POUVEZ PAS demander d'informations supplémentaires dans le même message.
- EXEMPLE INTERDIT: "Je vais créer un ticket pour vous. J'aurais juste besoin de votre nom complet." ❌
- EXEMPLE CORRECT: "J'aurais besoin de votre nom complet pour créer le ticket." ✅ (question AVANT de créer)
- EXEMPLE CORRECT: "Parfait, je crée le ticket tout de suite." ✅ (création SANS questions, après avoir collecté les infos)

Pour les installations logicielles:
- Information MINIMALE requise: le nom du logiciel (Word, Excel, etc.)
- Si vous avez le nom du logiciel → Vous pouvez créer le ticket directement
- Le nom de l'utilisateur est déjà connu (via l'email de connexion), pas besoin de le redemander

Si vous avez besoin d'informations, posez UNE question courte et conversationnelle. Si le problème nécessite des modifications système, expliquez gentiment que l'utilisateur n'a pas les droits et proposez IMMÉDIATEMENT de créer un ticket avec "needs_ticket: true".

⚠️ IMPORTANT - CRÉATION DE TICKETS:
- Quand vous proposez de créer un ticket, NE DEMANDEZ JAMAIS le moyen de contact (téléphone, email, Teams, "comment vous joindre"). Le ticket contient déjà toutes les informations nécessaires et l'équipe contactera l'utilisateur directement si besoin.
- RÈGLE CRITIQUE: Si vous dites "je crée", "je lance", "je vais créer", "création", "je m'occupe" ou toute phrase indiquant que vous créez un ticket → ARRÊTEZ IMMÉDIATEMENT. NE POSEZ AUCUNE QUESTION dans le même message. Le ticket sera créé automatiquement avec les informations déjà collectées.

Soyez humain, chaleureux, personnel mais CONCIS. Évitez les répétitions, les phrases trop longues et surtout les listes numérotées de questions. UNIQUEMENT des solutions MacBook Pro. JAMAIS de modifications système. JAMAIS de mention de "Jamf" dans vos réponses.

⚠️ IMPORTANT : Répondez UNIQUEMENT en texte naturel. NE JAMAIS retourner de JSON, de code, de formatage technique ou de structures de données. Votre réponse doit être du texte conversationnel pur, comme si vous parliez à un collègue.
"""
        
        try:
            # Utiliser generate_and_stream_response qui génère d'abord, puis stream
            if stream_callback:
                # Générer la réponse complète d'abord (sans streaming pour pouvoir la modifier)
                from langchain_core.messages import HumanMessage, SystemMessage
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=prompt)
                ]
                response = await llm.ainvoke(messages)
                response_text = response.content if hasattr(response, 'content') else str(response)
                # Nettoyer la réponse pour enlever tout JSON
                response_text = self.clean_response(response_text)
                
                # Post-traitement: supprimer les questions si l'agent a dit qu'il crée un ticket
                response_text = self._remove_questions_after_ticket_creation(response_text)
                
                # Maintenant streamer la réponse nettoyée
                if stream_callback and response_text:
                    import asyncio
                    chunk_size = 10
                    for i in range(0, len(response_text), chunk_size):
                        token = response_text[i:i+chunk_size]
                        try:
                            await stream_callback(token)
                        except Exception as e:
                            logger.debug("Stream callback error", error=str(e))
                            break
                        await asyncio.sleep(0.005)
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
                
                # Post-traitement: supprimer les questions si l'agent a dit qu'il crée un ticket
                response_text = self._remove_questions_after_ticket_creation(response_text)
            
            needs_ticket = (
                "needs_ticket: true" in response_text.lower() or
                "créer un ticket" in response_text.lower() or
                "ticket sera créé" in response_text.lower()
            )
            
            # Enlever "needs_ticket: true" si présent (déjà fait dans clean_response mais on double la vérification)
            response_text = response_text.replace("needs_ticket: true", "").replace("needs_ticket:true", "").strip()
            
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

