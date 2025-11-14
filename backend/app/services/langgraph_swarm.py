"""
LangGraph Swarm - Orchestration multi-agents
"""
import structlog
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END

from app.agents.network_agent import NetworkAgent
from app.agents.macos_agent import MacOSAgent
from app.agents.workspace_agent import WorkspaceAgent
from app.agents.knowledge_agent import KnowledgeAgent
from app.agents.odoo_ticket_agent import OdooTicketAgent
from app.services.ticket_validator import TicketValidator
from app.core.config import settings

logger = structlog.get_logger()


class LangGraphSwarm:
    """Orchestrateur multi-agents avec LangGraph"""
    
    def __init__(self):
        self.network_agent = NetworkAgent()
        self.macos_agent = MacOSAgent()
        self.workspace_agent = WorkspaceAgent()
        self.knowledge_agent = KnowledgeAgent()
        self.ticket_agent = OdooTicketAgent()
        self.ticket_validator = TicketValidator()
        
        # Construction du graphe LangGraph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Construit le graphe d'orchestration"""
        workflow = StateGraph(dict)
        
        # Ajout des nœuds (agents)
        workflow.add_node("network", self._network_node)
        workflow.add_node("macos", self._macos_node)
        workflow.add_node("workspace", self._workspace_node)
        workflow.add_node("knowledge", self._knowledge_node)
        workflow.add_node("ticket", self._ticket_node)
        
        # Fonction de routage conditionnel
        def route_agent(state: dict) -> str:
            """Route vers l'agent approprié basé sur la décision de routage"""
            agent = state.get("routing_decision", {}).get("agent", "knowledge")
            return agent
        
        # Point d'entrée avec routage conditionnel
        workflow.set_conditional_entry_point(
            route_agent,
            {
                "network": "network",
                "macos": "macos",
                "workspace": "workspace",
                "knowledge": "knowledge",
                "router": "knowledge",  # Fallback: router -> knowledge pour les cas généraux
            }
        )
        
        # Tous les agents vont vers le nœud ticket (qui vérifie si un ticket est nécessaire)
        workflow.add_edge("network", "ticket")
        workflow.add_edge("macos", "ticket")
        workflow.add_edge("workspace", "ticket")
        workflow.add_edge("knowledge", "ticket")
        
        workflow.add_edge("ticket", END)
        
        return workflow.compile()
    
    async def _network_node(self, state: dict) -> dict:
        """Nœud Network Agent"""
        try:
            stream_callback = state.get("stream_callback")
            response = await self.network_agent.process(
                message=state["message"],
                session_id=state["session_id"],
                user_id=state["user_id"],
                history=state.get("history", []),
                llm_provider=state["routing_decision"]["llm"],
                stream_callback=stream_callback
            )
            state["response"] = response
            state["agent_used"] = "network"
            return state
        except Exception as e:
            logger.error("Network agent error", error=str(e))
            state["response"] = {"message": "Erreur lors du diagnostic réseau. Veuillez réessayer ou contacter le support si le problème persiste.", "needs_ticket": False}
            return state
    
    async def _macos_node(self, state: dict) -> dict:
        """Nœud MacOS Agent"""
        try:
            stream_callback = state.get("stream_callback")
            response = await self.macos_agent.process(
                message=state["message"],
                session_id=state["session_id"],
                user_id=state["user_id"],
                history=state.get("history", []),
                llm_provider=state["routing_decision"]["llm"],
                stream_callback=stream_callback
            )
            state["response"] = response
            state["agent_used"] = "macos"
            return state
        except Exception as e:
            logger.error("MacOS agent error", error=str(e))
            state["response"] = {"message": "Erreur lors du diagnostic MacOS. Veuillez réessayer ou contacter le support si le problème persiste.", "needs_ticket": False}
            return state
    
    async def _workspace_node(self, state: dict) -> dict:
        """Nœud Workspace Agent"""
        try:
            stream_callback = state.get("stream_callback")
            response = await self.workspace_agent.process(
                message=state["message"],
                session_id=state["session_id"],
                user_id=state["user_id"],
                history=state.get("history", []),
                llm_provider=state["routing_decision"]["llm"],
                stream_callback=stream_callback
            )
            state["response"] = response
            state["agent_used"] = "workspace"
            return state
        except Exception as e:
            logger.error("Workspace agent error", error=str(e))
            state["response"] = {"message": "Erreur lors du diagnostic Workspace. Veuillez réessayer ou contacter le support si le problème persiste.", "needs_ticket": False}
            return state
    
    async def _knowledge_node(self, state: dict) -> dict:
        """Nœud Knowledge Agent"""
        try:
            stream_callback = state.get("stream_callback")
            response = await self.knowledge_agent.process(
                message=state["message"],
                session_id=state["session_id"],
                user_id=state["user_id"],
                history=state.get("history", []),
                llm_provider=state["routing_decision"]["llm"],
                stream_callback=stream_callback
            )
            state["response"] = response
            state["agent_used"] = "knowledge"
            return state
        except Exception as e:
            logger.error("Knowledge agent error", error=str(e))
            state["response"] = {"message": "Erreur lors de la recherche de connaissances. Veuillez réessayer ou contacter le support si le problème persiste.", "needs_ticket": False}
            return state
    
    async def _ticket_node(self, state: dict) -> dict:
        """Nœud Ticket Agent - Valide et crée un ticket si nécessaire"""
        response = state.get("response", {})
        needs_ticket_suggested = response.get("needs_ticket", False)
        
        # Valider si un ticket doit être créé
        validation = await self.ticket_validator.should_create_ticket(
            message=state["message"],
            agent_response=response.get("message", ""),
            agent_used=state.get("agent_used", "unknown"),
            history=state.get("history", []),
            needs_ticket_suggested=needs_ticket_suggested
        )
        
        if validation.get("should_create", False):
            try:
                ticket = await self.ticket_agent.create_ticket(
                    user_id=state["user_id"],
                    session_id=state["session_id"],
                    issue_description=state["message"],
                    conversation_history=state.get("history", []),
                    agent_used=state.get("agent_used", "unknown")
                )
                
                state["ticket_created"] = True
                state["ticket_id"] = ticket.get("id")
                state["response"]["message"] += f"\n\nUn ticket a été créé dans Odoo (ID: {ticket.get('id')}). Notre équipe va vous contacter prochainement."
                
                logger.info(
                    "Ticket created after validation",
                    ticket_id=ticket.get("id"),
                    reason=validation.get("reason", ""),
                    confidence=validation.get("confidence", 0.5)
                )
                
            except Exception as e:
                logger.error("Ticket creation error", error=str(e))
                state["response"]["message"] += "\n\nUne erreur est survenue lors de la création du ticket. Veuillez contacter le support directement."
        else:
            logger.info(
                "Ticket not created after validation",
                reason=validation.get("reason", ""),
                confidence=validation.get("confidence", 0.5),
                suggested=needs_ticket_suggested
            )
        
        return state
    
    async def process(
        self,
        message: str,
        session_id: str,
        user_id: str,
        routing_decision: Dict[str, Any],
        history: List[Dict[str, str]] = None,
        stream_callback = None
    ) -> Dict[str, Any]:
        """
        Traite une requête via le swarm d'agents
        
        Args:
            message: Message de l'utilisateur
            session_id: ID de la session
            user_id: ID de l'utilisateur
            routing_decision: Décision du router agent
            history: Historique de la conversation
            
        Returns:
            Réponse avec message et métadonnées
        """
        # État initial
        initial_state = {
            "message": message,
            "session_id": session_id,
            "user_id": user_id,
            "routing_decision": routing_decision,
            "history": history or [],
            "response": {},
            "agent_used": None,
            "ticket_created": False,
            "stream_callback": stream_callback
        }
        
        # Exécution du graphe
        try:
            final_state = await self.graph.ainvoke(initial_state)
            
            response = final_state.get("response", {})
            
            return {
                "message": response.get("message", "Je n'ai pas pu traiter votre demande."),
                "agent": final_state.get("agent_used", "unknown"),
                "metadata": {
                    "ticket_created": final_state.get("ticket_created", False),
                    "ticket_id": final_state.get("ticket_id"),
                    "confidence": routing_decision.get("confidence", 0.5)
                }
            }
            
        except Exception as e:
            logger.error("Swarm processing error", error=str(e), exc_info=True)
            return {
                "message": "Une erreur est survenue lors du traitement. Veuillez réessayer.",
                "agent": "system",
                "metadata": {"error": str(e)}
            }

