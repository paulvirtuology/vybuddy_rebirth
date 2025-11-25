"""
Ticket State Machine: Machine à état déterministe pour la validation de tickets.

Applique des règles métier strictes et séquentielles pour décider si un ticket
doit être créé. Chaque étape doit être validée avant de passer à la suivante.
"""
from __future__ import annotations

import structlog

from .ticket_state import ConversationState, TicketDecision, TicketStep

logger = structlog.get_logger()


class TicketStateMachine:
    """
    Machine à état déterministe pour la validation de tickets.
    
    Implémente la progression stricte:
    DETECT → COLLECT_REQUIRED → DIAGNOSE → DECIDE → VALIDATE → CREATE
    
    Chaque étape conditionne la suivante. Aucune ambiguïté possible.
    """

    @staticmethod
    def evaluate(state: ConversationState) -> TicketDecision:
        """
        Évalue l'état actuel et retourne une décision déterministe.
        
        Règles appliquées dans l'ordre (sans exception):
        1. DETECT: Type de demande et procédure doivent être identifiés
        2. COLLECT_REQUIRED: Tous les champs requis doivent être collectés
        3. DIAGNOSE: Les étapes de diagnostic doivent être complétées
        4. DECIDE: Vérifier si une action humaine est nécessaire
        5. VALIDATE: L'agent doit confirmer l'action sans poser de questions
        6. CREATE: Toutes les conditions sont remplies → création du ticket
        """
        
        # RÈGLE 1: DETECT - Type et procédure doivent être identifiés
        if not state.request_type:
            logger.debug("State Machine: Request type not detected", step="DETECT")
            return TicketDecision(
                step=TicketStep.DETECT,
                should_create=False,
                reason="Type de demande non détecté. Classification en cours.",
            )
        
        if not state.procedure:
            logger.debug(
                "State Machine: Procedure not found",
                step="DETECT",
                request_type=state.request_type,
            )
            return TicketDecision(
                step=TicketStep.DETECT,
                should_create=False,
                reason=f"Procédure non trouvée pour le type '{state.request_type}'. Vérification de la Knowledge Base.",
            )

        # RÈGLE 2: COLLECT_REQUIRED - Tous les champs requis doivent avoir une valeur non-null
        missing_fields = state.missing_fields
        if missing_fields:
            logger.info(
                "State Machine: Missing required fields",
                step="COLLECT_REQUIRED",
                missing_fields=missing_fields,
                collected_fields=list(state.collected_fields.keys()),
            )
            return TicketDecision(
                step=TicketStep.COLLECT_REQUIRED,
                should_create=False,
                reason=f"Champs obligatoires manquants: {', '.join(missing_fields)}. L'agent doit les collecter avant de créer le ticket.",
                missing_fields=missing_fields,
            )

        # RÈGLE 3: DIAGNOSE - Les étapes de diagnostic doivent être complétées
        if state.diagnostic_incomplete:
            logger.info(
                "State Machine: Diagnostic incomplete",
                step="DIAGNOSE",
                completed_steps=state.completed_steps,
                required_steps=state.procedure.diagnostic_steps,
            )
            return TicketDecision(
                step=TicketStep.DIAGNOSE,
                should_create=False,
                reason="Les étapes de diagnostic définies dans la procédure ne sont pas toutes complétées.",
            )

        # RÈGLE 4: DECIDE - Vérifier si une action humaine est nécessaire
        if not state.needs_human_action and not state.procedure.requires_human_action:
            logger.info(
                "State Machine: No human action required",
                step="DECIDE",
                needs_human_action=state.needs_human_action,
                procedure_requires_human=state.procedure.requires_human_action,
            )
            return TicketDecision(
                step=TicketStep.DECIDE,
                should_create=False,
                reason="Le problème peut être résolu par l'agent sans intervention humaine. Aucun ticket nécessaire.",
            )

        # RÈGLE 5: VALIDATE - L'agent doit confirmer explicitement l'action
        if not state.agent_confirmed_action:
            logger.info(
                "State Machine: Agent has not confirmed action - BLOCKING ticket creation",
                step="VALIDATE",
                agent_confirmed=state.agent_confirmed_action,
                request_type=state.request_type,
                collected_fields=list(state.collected_fields.keys()),
            )
            return TicketDecision(
                step=TicketStep.VALIDATE,
                should_create=False,
                reason="L'agent doit confirmer explicitement qu'il crée/lance la demande (ex: 'je crée', 'je lance', 'je m'occupe').",
            )

        # RÈGLE 6: VALIDATE - Aucune question ne doit être posée lors de la confirmation
        if state.question_signals:
            logger.warning(
                "State Machine: Agent confirmed but still asking questions",
                step="VALIDATE",
                question_signals=state.question_signals,
            )
            return TicketDecision(
                step=TicketStep.VALIDATE,
                should_create=False,
                reason=f"L'agent confirme la création mais pose encore des questions ({', '.join(state.question_signals[:3])}). La confirmation doit être sans questions.",
            )

        # RÈGLE 7: CREATE - Toutes les conditions sont remplies
        logger.info(
            "State Machine: All conditions met, ready to create ticket",
            step="CREATE",
            request_type=state.request_type,
            collected_fields=list(state.collected_fields.keys()),
        )
        return TicketDecision(
            step=TicketStep.CREATE,
            should_create=True,
            reason="Toutes les conditions sont remplies: type détecté, champs collectés, diagnostic complet, action humaine requise, agent a confirmé sans questions.",
        )

