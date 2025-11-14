"""
Service pour gérer les procédures de support IT
Récupère les procédures depuis Supabase et les utilise pour guider les agents
"""
import structlog
from typing import List, Dict, Any, Optional
import json

from app.database.supabase_client import SupabaseClient
from app.database.pinecone_client import PineconeClient

logger = structlog.get_logger()


class ProcedureService:
    """Service pour gérer les procédures de support"""
    
    def __init__(self):
        self.supabase = SupabaseClient()
        self.pinecone = PineconeClient()
    
    async def get_procedures_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Récupère les procédures pour une catégorie donnée
        """
        try:
            client = self.supabase._get_client()
            result = client.rpc(
                "get_procedures_by_category",
                {"category_filter": category}
            ).execute()
            
            procedures = []
            for row in result.data:
                procedures.append({
                    "id": row["id"],
                    "category": row["category"],
                    "title": row["title"],
                    "description": row["description"],
                    "diagnostic_questions": json.loads(row["diagnostic_questions"]) if isinstance(row["diagnostic_questions"], str) else row["diagnostic_questions"],
                    "resolution_steps": json.loads(row["resolution_steps"]) if isinstance(row["resolution_steps"], str) else row["resolution_steps"],
                    "ticket_creation": json.loads(row["ticket_creation"]) if isinstance(row["ticket_creation"], str) else row["ticket_creation"],
                    "common_issues": json.loads(row["common_issues"]) if isinstance(row["common_issues"], str) else row["common_issues"]
                })
            
            return procedures
        except Exception as e:
            logger.error(f"Error fetching procedures for category {category}: {e}")
            return []
    
    async def find_relevant_procedure(
        self,
        user_message: str,
        category: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Trouve la procédure la plus pertinente pour un message utilisateur
        Utilise la recherche vectorielle dans Pinecone
        """
        try:
            # Recherche dans Pinecone pour trouver des procédures pertinentes
            search_query = f"{user_message} {category or ''}"
            results = await self.pinecone.search(
                query=search_query,
                top_k=3,
                namespace="procedures" if category else None
            )
            
            if not results:
                return None
            
            # Prendre le résultat le plus pertinent
            best_match = results[0]
            
            # Si on a une catégorie, filtrer par catégorie
            if category:
                # Récupérer toutes les procédures de la catégorie
                procedures = await self.get_procedures_by_category(category)
                
                # Trouver celle qui correspond le mieux au résultat de recherche
                for procedure in procedures:
                    if procedure["title"].lower() in best_match["text"].lower():
                        return procedure
                
                # Sinon, retourner la première procédure de la catégorie
                if procedures:
                    return procedures[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding relevant procedure: {e}")
            return None
    
    async def log_procedure_usage(
        self,
        procedure_id: str,
        session_id: str,
        user_id: str,
        success: bool = True,
        feedback: Optional[str] = None
    ):
        """
        Enregistre l'utilisation d'une procédure pour le suivi
        """
        try:
            client = self.supabase._get_client()
            client.table("procedure_usage").insert({
                "procedure_id": procedure_id,
                "session_id": session_id,
                "user_id": user_id,
                "success": success,
                "feedback": feedback
            }).execute()
        except Exception as e:
            logger.error(f"Error logging procedure usage: {e}")
    
    def format_procedure_for_prompt(self, procedure: Dict[str, Any]) -> str:
        """
        Formate une procédure pour l'inclure dans un prompt
        """
        formatted = f"""PROCÉDURE: {procedure['title']}
Description: {procedure.get('description', '')}

QUESTIONS DE DIAGNOSTIC À POSER:
"""
        for i, question in enumerate(procedure.get("diagnostic_questions", []), 1):
            formatted += f"{i}. {question}\n"
        
        formatted += "\nÉTAPES DE RÉSOLUTION:\n"
        for step in procedure.get("resolution_steps", []):
            admin_note = " (nécessite droits admin)" if step.get("requires_admin") else ""
            formatted += f"Étape {step['step']}: {step['action']}{admin_note}\n"
            if step.get("details"):
                formatted += f"  → {step['details']}\n"
        
        ticket_info = procedure.get("ticket_creation", {})
        if ticket_info:
            formatted += f"\nCRÉATION DE TICKET ODOO:\n"
            formatted += f"Quand: {ticket_info.get('when', 'Si nécessaire')}\n"
            fields = ticket_info.get("required_fields", {})
            if fields:
                formatted += "Champs requis:\n"
                for field, value in fields.items():
                    formatted += f"  - {field}: {value}\n"
        
        if procedure.get("common_issues"):
            formatted += "\nPROBLÈMES FRÉQUENTS:\n"
            for issue in procedure["common_issues"]:
                formatted += f"- {issue}\n"
        
        return formatted

