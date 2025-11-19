"""
Service d'orchestration principal
Coordonne les agents et gère le flux de traitement
"""
import structlog
from typing import Dict, Any, List, Optional

from app.services.router_agent import RouterAgent
from app.services.langgraph_swarm import LangGraphSwarm
from app.database.redis_client import RedisClient
from app.database.supabase_client import SupabaseClient
from app.services.human_support_service import HumanSupportService

logger = structlog.get_logger()


class OrchestratorService:
    """Service principal d'orchestration"""
    
    def __init__(self):
        self.router_agent = RouterAgent()
        self.swarm = LangGraphSwarm()
        self.redis = RedisClient()
        self.supabase = SupabaseClient()
        self.human_support = HumanSupportService()
    
    async def process_request(
        self,
        message: str,
        session_id: str,
        user_id: str,
        user_name: str = None,
        stream_callback = None
    ) -> Dict[str, Any]:
        """
        Traite une requête utilisateur complète
        
        Args:
            message: Message de l'utilisateur
            session_id: ID de la session
            user_id: ID de l'utilisateur
            
        Returns:
            Réponse avec message, agent utilisé et métadonnées
        """
        try:
            # Détection des questions sur l'identité du bot
            identity_response = self._check_identity_question(message)
            if identity_response:
                # Pour les réponses système, on peut streamer si un callback est fourni
                if stream_callback:
                    # Streamer la réponse rapidement par petits morceaux
                    import asyncio
                    chunk_size = 15  # Environ 15 caractères à la fois
                    for i in range(0, len(identity_response), chunk_size):
                        token = identity_response[i:i+chunk_size]
                        try:
                            await stream_callback(token)
                        except Exception:
                            break  # WebSocket fermé, arrêter
                        await asyncio.sleep(0.01)  # Délai réduit à 10ms
                
                # Sauvegarde de l'historique
                await self.redis.add_to_session_history(
                    session_id=session_id,
                    user_message=message,
                    bot_response=identity_response
                )
                
                # Logging dans Supabase
                await self.supabase.log_interaction(
                    session_id=session_id,
                    user_id=user_id,
                    user_message=message,
                    bot_response=identity_response,
                    agent_used="system",
                    metadata={"type": "identity"}
                )
                
                return {
                    "message": identity_response,
                    "agent": "system",
                    "metadata": {"type": "identity"}
                }
            
            # Vérifier si une escalade humaine est déjà en cours
            if await self.human_support.is_session_escalated(session_id):
                await self.human_support.forward_user_message(
                    session_id=session_id,
                    user_id=user_id,
                    user_name=user_name,
                    text=message
                )
                return {
                    "message": "Je transmets votre message à notre équipe support. Un collègue humain vous répondra directement ici.",
                    "agent": "human_support",
                    "metadata": {"human_support": True, "status": "forwarded"}
                }

            # Détection d'une demande de support humain
            if self._check_human_support_request(message):
                escalation = await self.human_support.start_escalation(
                    session_id=session_id,
                    user_id=user_id,
                    user_name=user_name,
                    initial_message=message
                )

                return {
                    "message": "Pas de souci, je vous mets en relation avec un collègue humain. Il reviendra vers vous dans ce chat très rapidement.",
                    "agent": "human_support",
                    "metadata": {
                        "human_support": True,
                        "status": "started",
                        "already_active": escalation.get("already_active", False)
                    }
                }

            # Détection des salutations simples
            greeting_response = self._check_greeting(message)
            if greeting_response:
                # Pour les réponses système, on peut streamer si un callback est fourni
                if stream_callback:
                    # Streamer la réponse rapidement par petits morceaux
                    import asyncio
                    chunk_size = 15  # Environ 15 caractères à la fois
                    for i in range(0, len(greeting_response), chunk_size):
                        token = greeting_response[i:i+chunk_size]
                        try:
                            await stream_callback(token)
                        except Exception:
                            break  # WebSocket fermé, arrêter
                        await asyncio.sleep(0.01)  # Délai réduit à 10ms
                
                # Sauvegarde de l'historique
                await self.redis.add_to_session_history(
                    session_id=session_id,
                    user_message=message,
                    bot_response=greeting_response
                )
                
                # Logging dans Supabase
                await self.supabase.log_interaction(
                    session_id=session_id,
                    user_id=user_id,
                    user_message=message,
                    bot_response=greeting_response,
                    agent_used="system",
                    metadata={"type": "greeting"}
                )
                
                return {
                    "message": greeting_response,
                    "agent": "system",
                    "metadata": {"type": "greeting"}
                }
            
            # Récupération de l'historique de la session
            history = await self.redis.get_session_history(session_id)
            
            # Vérifier si on attend un choix de l'utilisateur (human_support vs ticket)
            pending_choice = await self.redis.get_session_data(session_id, "pending_escalation_choice")
            if pending_choice:
                # L'utilisateur répond à la question de choix
                choice = self._parse_escalation_choice(message)
                if choice == "human":
                    # Démarrer l'escalade humaine
                    escalation = await self.human_support.start_escalation(
                        session_id=session_id,
                        user_id=user_id,
                        user_name=user_name,
                        initial_message=pending_choice.get("original_message", message)
                    )
                    # Nettoyer l'état en attente
                    await self.redis.set_session_data(session_id, "pending_escalation_choice", None, ttl=1)
                    
                    return {
                        "message": "Parfait ! Je vous mets en relation avec un collègue humain. Il reviendra vers vous dans ce chat très rapidement.",
                        "agent": "human_support",
                        "metadata": {
                            "human_support": True,
                            "status": "started",
                            "already_active": escalation.get("already_active", False)
                        }
                    }
                elif choice == "ticket":
                    # Créer un ticket directement
                    await self.redis.set_session_data(session_id, "pending_escalation_choice", None, ttl=1)
                    # Continuer le traitement normal mais forcer la création de ticket
                    return await self._process_with_forced_ticket(
                        message=pending_choice.get("original_message", message),
                        session_id=session_id,
                        user_id=user_id,
                        history=history,
                        stream_callback=stream_callback
                    )
                else:
                    # Choix non reconnu, redemander
                    return {
                        "message": "Je n'ai pas bien compris. Préférez-vous que je vous passe un collègue directement ou que je crée un ticket de support ? (Répondez 'collègue' ou 'ticket')",
                        "agent": "system",
                        "metadata": {"pending_choice": True}
                    }
            
            # Analyse de l'intention et sélection du LLM
            routing_decision = await self.router_agent.analyze_and_route(
                message=message,
                history=history
            )
            
            logger.info(
                "Routing decision",
                session_id=session_id,
                intent=routing_decision["intent"],
                selected_llm=routing_decision["llm"],
                agent=routing_decision["agent"]
            )
            
            # Traitement par le swarm d'agents
            response = await self.swarm.process(
                message=message,
                session_id=session_id,
                user_id=user_id,
                routing_decision=routing_decision,
                history=history,
                stream_callback=stream_callback
            )
            
            # Vérifier si on doit proposer le choix (diagnostic long + ticket suggéré)
            needs_ticket = response.get("needs_ticket", False)
            is_long_diagnostic = self._is_long_diagnostic(history, response)
            
            if needs_ticket and is_long_diagnostic:
                # Proposer le choix à l'utilisateur
                choice_message = (
                    "Je vois que votre demande nécessite une intervention. "
                    "Souhaitez-vous que je vous passe directement un de mes collègues humains "
                    "pour discuter en temps réel, ou préférez-vous que je crée un ticket de support ?\n\n"
                    "Répondez 'collègue' pour parler à un humain, ou 'ticket' pour créer un ticket."
                )
                
                # Stocker l'état en attente
                await self.redis.set_session_data(
                    session_id,
                    "pending_escalation_choice",
                    {
                        "original_message": message,
                        "agent_response": response.get("message", ""),
                        "agent_used": response.get("agent", "unknown")
                    },
                    ttl=3600  # 1 heure
                )
                
                # Sauvegarder la réponse originale dans l'historique
                await self.redis.add_to_session_history(
                    session_id=session_id,
                    user_message=message,
                    bot_response=response["message"]
                )
                
                return {
                    "message": choice_message,
                    "agent": "system",
                    "metadata": {
                        "pending_escalation_choice": True,
                        "original_response": response.get("message", "")
                    }
                }
            
            # Sauvegarde de l'historique
            await self.redis.add_to_session_history(
                session_id=session_id,
                user_message=message,
                bot_response=response["message"]
            )
            
            # NOTE: Ne plus appeler log_interaction ici car les messages sont déjà sauvegardés
            # dans main.py via save_message. Cela évite la double sauvegarde et réduit les requêtes.
            # Les messages user et bot sont sauvegardés séparément dans main.py pour avoir leur UUID.
            
            return response
            
        except Exception as e:
            logger.error(
                "Orchestration error",
                session_id=session_id,
                error=str(e),
                exc_info=True
            )
            return {
                "message": "Je rencontre un petit problème technique de mon côté. Pouvez-vous réessayer dans quelques instants ? Si le problème persiste, n'hésitez pas à créer un nouveau chat ou à contacter le support directement.",
                "agent": "system",
                "metadata": {"error": str(e)}
            }
    
    def _check_identity_question(self, message: str) -> str:
        """
        Vérifie si la question concerne l'identité du bot
        
        Args:
            message: Message de l'utilisateur
            
        Returns:
            Réponse si c'est une question d'identité, None sinon
        """
        message_lower = message.lower().strip()
        
        # Mots-clés pour détecter les questions sur l'identité
        identity_keywords = [
            "qui es-tu",
            "qui êtes-vous",
            "quel est ton nom",
            "quel est votre nom",
            "comment tu t'appelles",
            "comment vous appelez-vous",
            "c'est quoi ton nom",
            "c'est quoi votre nom",
            "tu es qui",
            "vous êtes qui",
            "présente-toi",
            "présentez-vous",
            "qui es tu",
            "qui êtes vous",
            "ton nom",
            "votre nom",
            "t'appelles",
            "vous appelez",
            "identité",
            "qui est vybuddy",
            "c'est quoi vybuddy",
            "vybuddy",
            "vygeek"
        ]
        
        # Vérifier si le message contient des mots-clés d'identité
        for keyword in identity_keywords:
            if keyword in message_lower:
                return "Bonjour ! 👋 Je suis **VyBuddy**, votre assistant support IT de **VyGeek**. Je suis là pour vous aider à résoudre vos problèmes techniques avec bienveillance et efficacité. Que ce soit pour des problèmes de connexion réseau, des soucis avec votre MacBook, des questions sur Google Workspace, ou toute autre demande de support, je suis à votre écoute ! Comment puis-je vous aider aujourd'hui ?"
        
        return None
    
    def _check_greeting(self, message: str) -> str:
        """
        Vérifie si le message est une simple salutation
        
        Args:
            message: Message de l'utilisateur
            
        Returns:
            Réponse si c'est une salutation, None sinon
        """
        message_lower = message.lower().strip()
        
        # Salutations simples (un seul mot ou très court)
        simple_greetings = [
            "hello",
            "hi",
            "bonjour",
            "salut",
            "hey",
            "coucou",
            "bonsoir",
            "bonne journée",
            "bonjour !",
            "hello !",
            "hi !",
            "salut !"
        ]
        
        # Vérifier si c'est exactement une salutation simple
        if message_lower in simple_greetings:
            return "Bonjour ! 👋 Je suis **VyBuddy**, votre assistant support IT de **VyGeek**. Je suis ravi de vous aider ! Comment puis-je vous assister aujourd'hui ?"
        
        # Salutations avec quelques mots supplémentaires (mais toujours principalement une salutation)
        greeting_patterns = [
            "bonjour comment",
            "hello how",
            "hi how",
            "salut comment",
            "bonjour, comment",
            "hello, how",
            "hi, how"
        ]
        
        for pattern in greeting_patterns:
            if message_lower.startswith(pattern) and len(message_lower.split()) <= 5:
                return "Bonjour ! Je suis **VyBuddy**, votre agent de support IT de **VyGeek**. Comment puis-je vous aider aujourd'hui ?"
        
        return None

    def _check_human_support_request(self, message: str) -> bool:
        """
        Détecte si l'utilisateur demande à parler à un humain
        """
        message_lower = message.lower().strip()
        
        # Mots-clés complets (exact match)
        exact_keywords = [
            "parler à une vraie personne",
            "parler à quelqu'un",
            "parler à un humain",
            "assistant humain",
            "besoin d'un humain",
            "besoin d'une vraie personne",
            "transférer à un humain",
            "support humain",
            "humain s'il te plaît",
            "puis-je parler à un conseiller",
            "j'aimerais parler à un agent"
        ]
        
        # Vérifier les mots-clés exacts d'abord
        if any(keyword in message_lower for keyword in exact_keywords):
            return True
        
        # Détection flexible : combinaisons de mots-clés
        # "parler" + ("personne" ou "humain" ou "quelqu'un" ou "agent" ou "conseiller")
        parler_keywords = ["parler", "discuter", "échanger", "contacter"]
        human_keywords = ["personne", "humain", "quelqu'un", "agent", "conseiller", "collègue", "vraie personne"]
        
        has_parler = any(kw in message_lower for kw in parler_keywords)
        has_human = any(kw in message_lower for kw in human_keywords)
        
        # Si les deux sont présents, c'est probablement une demande de support humain
        if has_parler and has_human:
            # Exclure les faux positifs
            exclude_keywords = ["parler de", "parler du", "parler des", "parler d'"]
            if not any(exc in message_lower for exc in exclude_keywords):
                return True
        
        # Autres patterns
        other_patterns = [
            "vraie personne",
            "personne réelle",
            "agent humain",
            "conseiller humain",
            "support humain",
            "besoin d'un humain",
            "besoin d'une personne"
        ]
        
        return any(pattern in message_lower for pattern in other_patterns)
    
    def _parse_escalation_choice(self, message: str) -> Optional[str]:
        """
        Parse la réponse de l'utilisateur pour déterminer son choix
        Retourne 'human', 'ticket', ou None si non reconnu
        """
        message_lower = message.lower().strip()
        
        # Mots-clés pour choisir un humain
        human_keywords = [
            "collègue", "collègues", "humain", "humains", "personne", "personnes",
            "agent", "agents", "conseiller", "conseillers", "support humain",
            "parler à", "discuter avec", "échanger avec", "contact humain"
        ]
        
        # Mots-clés pour choisir un ticket
        ticket_keywords = [
            "ticket", "tickets", "créer un ticket", "ouvrir un ticket",
            "demande de support", "demande support", "créer une demande"
        ]
        
        # Vérifier d'abord les mots-clés humain (priorité)
        if any(keyword in message_lower for keyword in human_keywords):
            return "human"
        
        # Ensuite les mots-clés ticket
        if any(keyword in message_lower for keyword in ticket_keywords):
            return "ticket"
        
        return None
    
    def _is_long_diagnostic(self, history: List[Dict[str, str]], response: Dict[str, Any]) -> bool:
        """
        Détermine si la conversation est un diagnostic long/complexe
        Critères:
        - Plus de 3 échanges dans l'historique
        - L'agent a posé plusieurs questions
        - Le problème semble complexe
        """
        if not history:
            return False
        
        # Critère 1: Nombre d'échanges (plus de 3 = diagnostic long)
        if len(history) >= 3:
            return True
        
        # Critère 2: L'agent a posé plusieurs questions dans l'historique
        question_count = 0
        for exchange in history:
            bot_response = exchange.get("bot", "").lower()
            if "?" in bot_response or any(q in bot_response for q in [
                "pouvez-vous", "pourriez-vous", "auriez-vous", "avez-vous",
                "quel est", "quelle est", "comment", "où", "quand"
            ]):
                question_count += 1
        
        if question_count >= 2:
            return True
        
        # Critère 3: La réponse actuelle suggère un problème complexe
        response_text = response.get("message", "").lower()
        complexity_indicators = [
            "plusieurs étapes", "plusieurs options", "plusieurs solutions",
            "complexe", "compliqué", "difficile", "nécessite", "requiert"
        ]
        
        if any(indicator in response_text for indicator in complexity_indicators):
            return True
        
        return False
    
    async def _process_with_forced_ticket(
        self,
        message: str,
        session_id: str,
        user_id: str,
        history: List[Dict[str, str]],
        stream_callback = None
    ) -> Dict[str, Any]:
        """
        Traite une demande en forçant la création d'un ticket
        (utilisé quand l'utilisateur choisit 'ticket' après un diagnostic long)
        """
        from app.services.langgraph_swarm import LangGraphSwarm
        from app.services.router_agent import RouterAgent
        from app.services.ticket_validator import TicketValidator
        from app.agents.odoo_ticket_agent import OdooTicketAgent
        
        swarm = LangGraphSwarm()
        router_agent = RouterAgent()
        ticket_validator = TicketValidator()
        ticket_agent = OdooTicketAgent()
        
        # Analyser l'intention
        routing_decision = await router_agent.analyze_and_route(
            message=message,
            history=history
        )
        
        # Traiter avec le swarm (sans créer de ticket automatiquement)
        response = await swarm.process(
            message=message,
            session_id=session_id,
            user_id=user_id,
            routing_decision=routing_decision,
            history=history,
            stream_callback=stream_callback
        )
        
        # Forcer la création du ticket
        try:
            ticket = await ticket_agent.create_ticket(
                user_id=user_id,
                session_id=session_id,
                issue_description=message,
                conversation_history=history,
                agent_used=response.get("agent", "unknown")
            )
            
            ticket_message = (
                f"{response.get('message', '')}\n\n"
                f"✅ Un ticket de support a été créé (ID: {ticket.get('id', 'N/A')}). "
                f"Notre équipe va le traiter dans les plus brefs délais."
            )
            
            # Mettre à jour les métadonnées
            metadata = response.get("metadata", {})
            metadata["ticket_created"] = True
            metadata["ticket_id"] = ticket.get("id")
            metadata["forced_ticket"] = True  # Indique que c'était un choix utilisateur
            
            return {
                "message": ticket_message,
                "agent": response.get("agent", "unknown"),
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error("Error creating forced ticket", error=str(e))
            return {
                "message": (
                    f"{response.get('message', '')}\n\n"
                    "⚠️ Je n'ai pas pu créer le ticket automatiquement. "
                    "Veuillez contacter directement le support ou réessayer."
                ),
                "agent": response.get("agent", "unknown"),
                "metadata": response.get("metadata", {})
            }

