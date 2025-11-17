"""
Service d'orchestration principal
Coordonne les agents et gère le flux de traitement
"""
import structlog
from typing import Dict, Any

from app.services.router_agent import RouterAgent
from app.services.langgraph_swarm import LangGraphSwarm
from app.database.redis_client import RedisClient
from app.database.supabase_client import SupabaseClient

logger = structlog.get_logger()


class OrchestratorService:
    """Service principal d'orchestration"""
    
    def __init__(self):
        self.router_agent = RouterAgent()
        self.swarm = LangGraphSwarm()
        self.redis = RedisClient()
        self.supabase = SupabaseClient()
    
    async def process_request(
        self,
        message: str,
        session_id: str,
        user_id: str,
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
            
            # Sauvegarde de l'historique
            await self.redis.add_to_session_history(
                session_id=session_id,
                user_message=message,
                bot_response=response["message"]
            )
            
            # Logging dans Supabase
            await self.supabase.log_interaction(
                session_id=session_id,
                user_id=user_id,
                user_message=message,
                bot_response=response["message"],
                agent_used=routing_decision["agent"],
                metadata=response.get("metadata", {})
            )
            
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

