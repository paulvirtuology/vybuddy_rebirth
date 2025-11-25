"""
Odoo Ticket Agent - Création de tickets dans Odoo
"""
from typing import Dict, Any, List
import structlog
import httpx
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

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
        
        # LLM pour générer les titres et résumés
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # Modèle rapide et économique
            temperature=0.3,
            api_key=settings.OPENAI_API_KEY
        )
    
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
    
    async def _generate_ticket_summary(
        self,
        issue_description: str,
        conversation_history: List[Dict[str, str]] = None,
        agent_used: str = "unknown"
    ) -> Dict[str, str]:
        """
        Génère un titre et un résumé clairs à partir de l'historique de conversation
        
        Returns:
            Dict avec 'title' et 'summary'
        """
        try:
            # Construire le contexte de la conversation
            conversation_text = ""
            if conversation_history:
                for exchange in conversation_history:
                    user_msg = exchange.get('user', '').strip()
                    bot_msg = exchange.get('bot', '').strip()
                    if user_msg:
                        conversation_text += f"Utilisateur: {user_msg}\n"
                    if bot_msg:
                        conversation_text += f"Assistant: {bot_msg}\n"
            
            # Prompt pour générer titre et résumé
            prompt = f"""Analysez cette conversation de support IT et générez un titre clair et un résumé structuré pour un ticket.

Dernier message utilisateur: {issue_description}

Historique de la conversation:
{conversation_text}

Agent utilisé: {agent_used}

Générez:
1. Un TITRE court et descriptif (max 60 caractères) qui résume clairement la demande
   - Exemple: "Création boucle email testing@virtuocode.ai"
   - Exemple: "Installation logiciel sur MacBook"
   - Exemple: "Problème connexion WiFi"
   - ÉVITEZ les titres génériques comme "Support IT - ..." ou juste le dernier message

2. Un RÉSUMÉ structuré qui:
   - Identifie clairement le type de demande
   - Liste les informations importantes collectées (emails, noms, détails techniques, etc.)
   - Résume le contexte et la demande de l'utilisateur
   - Exclut les détails de conversation répétitifs ou non pertinents
   - Format clair et lisible pour un technicien IT

Répondez UNIQUEMENT en JSON valide:
{{
    "title": "Titre clair et descriptif",
    "summary": "Résumé structuré et clair de la demande"
}}
"""

            messages = [
                SystemMessage(content="Vous êtes un expert en rédaction de tickets IT. Répondez uniquement en JSON valide, sans texte supplémentaire."),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            # Gérer le cas où response.content pourrait être un dict ou une string
            if isinstance(response.content, dict):
                # Si c'est déjà un dict, l'utiliser directement
                result = response.content
            else:
                content = str(response.content).strip()
                
                # Nettoyer le JSON si nécessaire
                if content.startswith("```json"):
                    content = content.replace("```json", "").replace("```", "").strip()
                elif content.startswith("```"):
                    content = content.replace("```", "").strip()
                
                result = json.loads(content)
            
            # Validation et fallback
            # S'assurer que title et summary sont des strings
            title = result.get("title", "")
            summary = result.get("summary", "")
            # Convertir en string si ce n'est pas déjà le cas
            if isinstance(title, dict):
                title = str(title)
            if isinstance(summary, dict):
                summary = str(summary)
            title = str(title).strip() if title else ""
            summary = str(summary).strip() if summary else ""
            
            if not title or len(title) > 100:
                # Fallback: utiliser le dernier message tronqué
                title = issue_description[:50] if issue_description else "Support IT"
            
            if not summary:
                # Fallback: résumé basique
                summary = f"Demande: {issue_description}\n\nAgent utilisé: {agent_used}"
            
            logger.info(
                "Generated ticket summary",
                title_preview=title[:50],
                summary_length=len(summary)
            )
            
            return {
                "title": title,
                "summary": summary
            }
            
        except Exception as e:
            logger.warning(
                "Error generating ticket summary, using fallback",
                error=str(e)
            )
            # Fallback en cas d'erreur
            fallback_title = issue_description[:50] if issue_description else "Support IT"
            fallback_summary = f"""Demande: {issue_description}

Agent utilisé: {agent_used}
"""
            if conversation_history:
                fallback_summary += "\nHistorique de la conversation:\n"
                for exchange in conversation_history[-5:]:  # Derniers 5 échanges
                    user_msg = exchange.get('user', '').strip()
                    bot_msg = exchange.get('bot', '').strip()
                    if user_msg:
                        fallback_summary += f"\nUtilisateur: {user_msg}"
                    if bot_msg:
                        fallback_summary += f"\nAssistant: {bot_msg}\n"
            
            return {
                "title": fallback_title,
                "summary": fallback_summary
            }
    
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
            
            # Générer titre et résumé avec LLM
            summary_data = await self._generate_ticket_summary(
                issue_description=issue_description,
                conversation_history=conversation_history,
                agent_used=agent_used
            )
            
            ticket_title = summary_data["title"]
            ticket_summary = summary_data["summary"]
            
            # Construction de la description complète avec résumé structuré
            description = f"""{ticket_summary}

---
Informations techniques:
- Agent utilisé: {agent_used}
- Session ID: {session_id}
- Utilisateur: {user_id}
"""
            
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
            
            # Création du ticket avec titre généré
            ticket_data = {
                "name": ticket_title,
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

