"""
Repository pour accéder aux procédures de la Knowledge Base.

Stratégie de récupération:
1. Recherche dans Supabase par catégorie (plus fiable)
2. Recherche vectorielle dans Pinecone (si Supabase échoue)
3. Fallback sur procédures par défaut (si tout échoue)

Architecture robuste avec gestion d'erreurs et logging détaillé.
"""
from __future__ import annotations

from typing import Optional, List, Dict, Any

import structlog

from app.services.procedure_service import ProcedureService
from .ticket_state import ProcedureDefinition

logger = structlog.get_logger()


class TicketProcedureRepository:
    """
    Repository robuste pour récupérer les procédures depuis la Knowledge Base.
    
    Utilise une stratégie multi-niveaux:
    - Supabase (source de vérité)
    - Pinecone (recherche vectorielle)
    - Fallback (procédures par défaut)
    """

    def __init__(self):
        self._procedure_service = ProcedureService()

    async def get_procedure(self, request_type: str, user_message: str) -> Optional[ProcedureDefinition]:
        """
        Récupère une procédure avec stratégie de fallback robuste.
        
        Args:
            request_type: Type de demande (ex: "installation_logiciel")
            user_message: Message utilisateur pour contexte de recherche
        
        Returns:
            ProcedureDefinition ou None si aucune procédure n'est trouvée
        """
        logger.info(
            "Fetching procedure",
            request_type=request_type,
            message_preview=user_message[:50],
        )

        # STRATÉGIE 1: Recherche dans Supabase par catégorie (plus fiable)
        procedure = await self._fetch_from_supabase(request_type)
        if procedure:
            logger.info("Procedure found in Supabase", request_type=request_type)
            return self._build_procedure_definition(procedure, request_type)

        # STRATÉGIE 2: Recherche vectorielle dans Pinecone
        procedure = await self._fetch_from_pinecone(request_type, user_message)
        if procedure:
            logger.info("Procedure found in Pinecone", request_type=request_type)
            return self._build_procedure_definition(procedure, request_type)

        # STRATÉGIE 3: Fallback sur procédures par défaut
        logger.warning(
            "Procedure not found in KB, using fallback",
            request_type=request_type,
        )
        return self._fallback_procedure(request_type)

    async def _fetch_from_supabase(self, request_type: str) -> Optional[Dict[str, Any]]:
        """Récupère la procédure depuis Supabase par catégorie."""
        try:
            procedures = await self._procedure_service.get_procedures_by_category(request_type)
            if procedures:
                # Retourner la première procédure de la catégorie
                # (on pourrait améliorer avec un scoring si plusieurs)
                return procedures[0]
        except Exception as err:
            logger.warning(
                "Failed to fetch from Supabase",
                request_type=request_type,
                error=str(err),
            )
        return None

    async def _fetch_from_pinecone(
        self, request_type: str, user_message: str
    ) -> Optional[Dict[str, Any]]:
        """Récupère la procédure depuis Pinecone via recherche vectorielle."""
        try:
            procedure = await self._procedure_service.find_relevant_procedure(
                user_message=user_message,
                category=request_type,
            )
            return procedure
        except Exception as err:
            logger.warning(
                "Failed to fetch from Pinecone",
                request_type=request_type,
                error=str(err),
            )
        return None

    def _build_procedure_definition(
        self, procedure: Dict[str, Any], request_type: str
    ) -> ProcedureDefinition:
        """
        Construit un ProcedureDefinition depuis un dict de procédure.
        
        Gère les différents formats possibles de la KB.
        """
        ticket_info = procedure.get("ticket_creation", {}) or {}
        required_fields = ticket_info.get("required_fields", {}) or {}

        # Si required_fields est un dict, extraire les clés
        if isinstance(required_fields, dict):
            field_names = list(required_fields.keys())
        elif isinstance(required_fields, list):
            field_names = required_fields
        else:
            field_names = []

        # Extraire les étapes de diagnostic
        resolution_steps = procedure.get("resolution_steps", []) or []
        diagnostic_steps = []
        if isinstance(resolution_steps, list):
            for step in resolution_steps:
                if isinstance(step, dict):
                    action = step.get("action") or step.get("step")
                    if action:
                        diagnostic_steps.append(str(action))
                elif isinstance(step, str):
                    diagnostic_steps.append(step)

        return ProcedureDefinition(
            request_type=request_type,
            required_fields=field_names,
            diagnostic_steps=diagnostic_steps,
            escalation_rules=ticket_info,
            requires_human_action=ticket_info.get("requires_human_action", True),
        )

    def _fallback_procedure(self, request_type: str) -> Optional[ProcedureDefinition]:
        """
        Procédures par défaut utilisées si la KB n'est pas disponible.
        
        Ces procédures sont minimales mais permettent au système de fonctionner
        même en cas de problème avec la Knowledge Base.
        """
        defaults: Dict[str, ProcedureDefinition] = {
            "installation_logiciel": ProcedureDefinition(
                request_type="installation_logiciel",
                required_fields=["logiciel", "software_name"],
                diagnostic_steps=[],
                requires_human_action=True,
            ),
            "wifi_probleme": ProcedureDefinition(
                request_type="wifi_probleme",
                required_fields=["network_name", "location"],
                diagnostic_steps=["redémarrage mac", "test autre réseau"],
                requires_human_action=False,
            ),
            "acces_drive": ProcedureDefinition(
                request_type="acces_drive",
                required_fields=["folder_name", "email", "reason"],
                diagnostic_steps=[],
                requires_human_action=True,
            ),
            "creation_email": ProcedureDefinition(
                request_type="creation_email",
                required_fields=["email", "emails", "reason"],
                diagnostic_steps=[],
                requires_human_action=True,
            ),
            "acces_monday": ProcedureDefinition(
                request_type="acces_monday",
                required_fields=["board_name", "nom", "email"],
                diagnostic_steps=[],
                requires_human_action=True,
            ),
            "probleme_macbook": ProcedureDefinition(
                request_type="probleme_macbook",
                required_fields=["serial_number", "device_id"],
                diagnostic_steps=["redémarrage", "vérification jamf"],
                requires_human_action=False,
            ),
        }
        
        fallback = defaults.get(request_type)
        if fallback:
            logger.info("Using fallback procedure", request_type=request_type)
        else:
            logger.warning("No fallback procedure available", request_type=request_type)
        
        return fallback

