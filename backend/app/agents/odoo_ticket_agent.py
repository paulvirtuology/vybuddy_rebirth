"""
Odoo Ticket Agent - Création de tickets dans Odoo
"""
from typing import Dict, Any, List
import structlog
import httpx

from app.core.config import settings

logger = structlog.get_logger()


class OdooTicketAgent:
    """Agent spécialisé dans la création de tickets Odoo"""
    
    def __init__(self):
        self.odoo_url = settings.ODOO_URL
        self.database = settings.ODOO_DATABASE
        self.username = settings.ODOO_USERNAME
        self.password = settings.ODOO_PASSWORD
        self.uid = None
    
    async def _authenticate(self) -> bool:
        """Authentification Odoo"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.odoo_url}/web/session/authenticate",
                    json={
                        "jsonrpc": "2.0",
                        "params": {
                            "db": self.database,
                            "login": self.username,
                            "password": self.password
                        }
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.uid = data.get("result", {}).get("uid")
                    return self.uid is not None
                
                return False
                
        except Exception as e:
            logger.error("Odoo authentication error", error=str(e))
            return False
    
    async def _get_user_id(self, user_name: str) -> int:
        """
        Récupère l'ID utilisateur Odoo à partir du nom
        Utilise l'API XML-RPC d'Odoo
        """
        try:
            import xmlrpc.client
            
            # Connexion à Odoo via XML-RPC
            common = xmlrpc.client.ServerProxy(f"{self.odoo_url}/xmlrpc/2/common")
            uid = common.authenticate(
                self.database,
                self.username,
                self.password,
                {}
            )
            
            if not uid:
                logger.error("Odoo authentication failed")
                return None
            
            # Recherche de l'utilisateur
            models = xmlrpc.client.ServerProxy(f"{self.odoo_url}/xmlrpc/2/object")
            user_ids = models.execute_kw(
                self.database,
                uid,
                self.password,
                "res.partner",
                "search",
                [[["name", "ilike", user_name]]],
                {"limit": 1}
            )
            
            if user_ids:
                users = models.execute_kw(
                    self.database,
                    uid,
                    self.password,
                    "res.partner",
                    "read",
                    [user_ids],
                    {"fields": ["id", "name"]}
                )
                if users:
                    return users[0]["id"]
            
            return None
            
        except Exception as e:
            logger.error("Error getting user ID", error=str(e))
            return None
    
    async def create_ticket(
        self,
        user_id: str,
        session_id: str,
        issue_description: str,
        conversation_history: List[Dict[str, str]] = None,
        agent_used: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Crée un ticket dans Odoo Helpdesk
        
        Args:
            user_id: ID ou nom de l'utilisateur
            session_id: ID de la session
            issue_description: Description du problème
            conversation_history: Historique de la conversation
            agent_used: Agent qui a traité la demande
            
        Returns:
            Informations du ticket créé
        """
        try:
            import xmlrpc.client
            
            # Connexion à Odoo
            common = xmlrpc.client.ServerProxy(f"{self.odoo_url}/xmlrpc/2/common")
            uid = common.authenticate(
                self.database,
                self.username,
                self.password,
                {}
            )
            
            if not uid:
                raise Exception("Odoo authentication failed")
            
            # Construction de la description complète
            description = f"""Problème signalé: {issue_description}

Agent utilisé: {agent_used}
Session ID: {session_id}

Historique de la conversation:
"""
            if conversation_history:
                for exchange in conversation_history[-10:]:  # Derniers 10 échanges
                    description += f"\nUtilisateur: {exchange.get('user', '')}"
                    description += f"\nAssistant: {exchange.get('bot', '')}\n"
            
            # Recherche de l'utilisateur (partenaire)
            models = xmlrpc.client.ServerProxy(f"{self.odoo_url}/xmlrpc/2/object")
            
            # Recherche du partenaire par nom (simplifié)
            partner_ids = models.execute_kw(
                self.database,
                uid,
                self.password,
                "res.partner",
                "search",
                [[["name", "ilike", user_id]]],
                {"limit": 1}
            )
            
            partner_id = partner_ids[0] if partner_ids else None
            
            # Si pas trouvé, créer un partenaire (optionnel)
            if not partner_id:
                partner_id = models.execute_kw(
                    self.database,
                    uid,
                    self.password,
                    "res.partner",
                    "create",
                    [{"name": user_id}]
                )
            
            # Recherche de l'équipe helpdesk (par défaut)
            team_ids = models.execute_kw(
                self.database,
                uid,
                self.password,
                "helpdesk.team",
                "search",
                [[]],
                {"limit": 1}
            )
            
            team_id = team_ids[0] if team_ids else None
            
            # Création du ticket
            ticket_data = {
                "name": f"Support IT - {issue_description[:50]}",
                "description": description,
                "partner_id": partner_id,
                "team_id": team_id,
                "tag_ids": [(6, 0, [])],  # Tags optionnels
            }
            
            ticket_id = models.execute_kw(
                self.database,
                uid,
                self.password,
                "helpdesk.ticket",
                "create",
                [ticket_data]
            )
            
            logger.info(
                "Ticket created in Odoo",
                ticket_id=ticket_id,
                user_id=user_id,
                session_id=session_id
            )
            
            return {
                "id": ticket_id,
                "name": ticket_data["name"],
                "status": "created"
            }
            
        except Exception as e:
            logger.error(
                "Error creating Odoo ticket",
                error=str(e),
                exc_info=True
            )
            raise

