"""
Validateur de tickets professionnel basé sur:
- Classification intelligente (LLM)
- Extraction structurée de champs (LLM)
- Machine à état déterministe
- Knowledge Base (Pinecone/Supabase)

Architecture solide, déterministe, scalable et facile à maintenir.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional

import structlog

from .action_detector import detect_agent_action
from .question_detector import detect_questions
from .request_classifier import RequestClassifier
from .ticket_procedure_repository import TicketProcedureRepository
from .field_extractor import FieldExtractor
from .conversation_state_cache import ConversationStateCache
from .ticket_state import ConversationState, TicketDecision
from .ticket_state_machine import TicketStateMachine

logger = structlog.get_logger()


class TicketValidator:
    """
    Validateur professionnel de tickets avec architecture modulaire.
    
    Flux:
    1. Chargement de l'état depuis le cache (si disponible)
    2. Classification de la demande (LLM) - si pas en cache
    3. Récupération de la procédure depuis la Knowledge Base - si pas en cache
    4. Extraction structurée des champs requis (LLM) - mise à jour incrémentale
    5. Évaluation par la machine à état déterministe
    6. Sauvegarde de l'état dans le cache
    7. Décision finale (créer ou non le ticket)
    """

    def __init__(self):
        self.classifier = RequestClassifier()
        self.procedure_repository = TicketProcedureRepository()
        self.field_extractor = FieldExtractor()
        self.state_cache = ConversationStateCache()

    async def should_create_ticket(
        self,
        message: str,
        agent_response: str,
        agent_used: str,
        session_id: str,
        user_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        needs_ticket_suggested: bool = False,
    ) -> Dict[str, Any]:
        """
        Valide si un ticket doit être créé en suivant un processus déterministe.
        
        Args:
            message: Dernier message de l'utilisateur
            agent_response: Réponse de l'agent
            agent_used: Nom de l'agent utilisé
            session_id: ID de la session (requis pour le cache)
            user_id: ID de l'utilisateur (optionnel, pour le cache)
            history: Historique de la conversation
            needs_ticket_suggested: Si l'agent a suggéré un ticket
        
        Returns:
            Dict avec should_create, reason, confidence, et details
        """
        history = history or []
        
        logger.info(
            "Ticket validation started",
            message_preview=message[:50],
            agent_used=agent_used,
            session_id=session_id,
            history_length=len(history),
        )
        
        # ÉTAPE 0: Charger l'état depuis le cache (si disponible)
        cached_state = await self.state_cache.get_state(session_id, user_id)
        
        # Initialiser l'état de la conversation
        if cached_state:
            # Fusionner l'état en cache avec les nouvelles données
            state = ConversationState(
                message=message,
                history=history,  # Toujours utiliser l'historique le plus récent
                request_type=cached_state.request_type,
                procedure=cached_state.procedure,
                collected_fields=cached_state.collected_fields.copy(),  # Copie pour éviter mutations
                completed_steps=cached_state.completed_steps.copy(),
                needs_human_action=cached_state.needs_human_action,
                agent_confirmed_action=False,  # Réinitialiser à chaque appel
                question_signals=[],  # Réinitialiser à chaque appel
            )
            logger.info(
                "State loaded from cache",
                session_id=session_id,
                request_type=state.request_type,
                cached_fields_count=len(state.collected_fields),
            )
        else:
            # Nouvel état si pas de cache
            state = ConversationState(message=message, history=history)
            logger.debug("No cached state, starting fresh", session_id=session_id)

        # ÉTAPE 1: Classification de la demande (seulement si pas en cache)
        if not state.request_type:
            state.request_type = await self._detect_request_type(message, history, agent_used=agent_used)
            if not state.request_type:
                logger.info("Request type not detected, waiting for more context.")
                # Sauvegarder l'état même si pas de type détecté
                await self.state_cache.save_state(state, session_id, user_id)
                return self._build_response(
                    should_create=False,
                    reason="Type de demande non détecté. L'agent doit clarifier la demande.",
                    step="detect",
                )

        # ÉTAPE 2: Récupération de la procédure depuis la Knowledge Base (seulement si pas en cache)
        if not state.procedure and state.request_type:
            state.procedure = await self.procedure_repository.get_procedure(state.request_type, message)
            if not state.procedure:
                logger.warning(
                    "Procedure not found in knowledge base",
                    request_type=state.request_type,
                )
                await self.state_cache.save_state(state, session_id, user_id)
                return self._build_response(
                    should_create=False,
                    reason=f"Procédure non trouvée pour '{state.request_type}'. Vérification de la Knowledge Base nécessaire.",
                    step="detect",
                )

        # ÉTAPE 3: Extraction structurée des champs requis (mise à jour incrémentale)
        if state.procedure and state.procedure.required_fields:
            # Extraire seulement les nouveaux champs depuis le dernier message
            extracted_fields = await self.field_extractor.extract_fields(
                request_type=state.request_type,
                procedure=state.procedure,
                history=history,
                current_message=message,
            )
            # Fusionner avec les champs déjà collectés (les nouveaux écrasent les anciens)
            state.collected_fields.update(extracted_fields)
            logger.info(
                "Fields extracted and merged",
                request_type=state.request_type,
                total_fields=len(state.collected_fields),
                fields_with_values=[k for k, v in state.collected_fields.items() if v is not None],
            )

        # ÉTAPE 4: Populer l'état avec les détections (questions, actions, diagnostic)
        self._populate_state(state, agent_response, needs_ticket_suggested)

        # ÉTAPE 5: Évaluation par la machine à état déterministe
        decision: TicketDecision = TicketStateMachine.evaluate(state)

        # ÉTAPE 6: Sauvegarder l'état dans le cache
        await self.state_cache.save_state(state, session_id, user_id)

        # Construire la réponse finale
        return self._build_response(
            should_create=decision.should_create,
            reason=decision.reason,
            step=decision.step.value,
            missing_fields=decision.missing_fields,
            request_type=state.request_type,
            procedure_found=bool(state.procedure),
            agent_confirmed=state.agent_confirmed_action,
            question_signals=state.question_signals,
            collected_fields=list(state.collected_fields.keys()),
        )
    
    async def invalidate_cache(self, session_id: str, user_id: Optional[str] = None) -> bool:
        """
        Invalide le cache pour une session (appelé après création de ticket).
        
        Args:
            session_id: ID de la session
            user_id: ID de l'utilisateur (optionnel)
        
        Returns:
            True si invalidé avec succès
        """
        return await self.state_cache.invalidate_state(session_id, user_id)

    async def _detect_request_type(
        self, message: str, history: List[Dict[str, str]], agent_used: Optional[str] = None
    ) -> Optional[str]:
        """Détecte le type de demande via classification LLM avec fallback."""
        classified = await self.classifier.classify(message, history, agent_used=agent_used)
        if classified:
            return classified
        return self._fallback_request_type(message, history)

    def _fallback_request_type(self, message: str, history: List[Dict[str, str]]) -> Optional[str]:
        """Fallback basé sur des mots-clés si la classification LLM échoue."""
        context = (message + " " + " ".join(f"{h.get('user','')} {h.get('bot','')}" for h in history)).lower()
        if any(keyword in context for keyword in ["installer", "installation", "logiciel", "word", "excel"]):
            return "installation_logiciel"
        if any(keyword in context for keyword in ["wifi", "connexion", "internet"]):
            return "wifi_probleme"
        if any(keyword in context for keyword in ["drive", "dossier partagé"]):
            return "acces_drive"
        if any(keyword in context for keyword in ["boucle", "adresse email", "créer email"]):
            return "creation_email"
        return None

    def _populate_state(
        self, state: ConversationState, agent_response: str, needs_ticket_suggested: bool
    ) -> None:
        """
        Popule l'état avec les détections de questions, actions et étapes de diagnostic.
        """
        # Détecter les actions de l'agent
        is_action, _ = detect_agent_action(agent_response)
        state.agent_confirmed_action = is_action

        # Détecter les questions dans la réponse de l'agent
        is_question, question_signals = detect_questions(agent_response)
        state.question_signals = question_signals if is_question else []

        # Déterminer si une action humaine est nécessaire
        state.needs_human_action = needs_ticket_suggested or (
            state.procedure.requires_human_action if state.procedure else True
        )

        # Vérifier les étapes de diagnostic complétées
        if state.procedure and state.procedure.diagnostic_steps:
            combined_history = " ".join(
                [state.message] + [h.get("user", "") + " " + h.get("bot", "") for h in state.history]
            ).lower()
            state.completed_steps = [
                step
                for step in state.procedure.diagnostic_steps
                if step and step.lower() in combined_history
            ]

        logger.debug(
            "State populated",
            request_type=state.request_type,
            collected_fields=list(state.collected_fields.keys()),
            agent_confirmed=state.agent_confirmed_action,
            questions=state.question_signals,
            needs_human_action=state.needs_human_action,
            completed_diagnostic_steps=len(state.completed_steps) if state.procedure else 0,
        )

    def _build_response(
        self,
        should_create: bool,
        reason: str,
        step: str,
        missing_fields: Optional[List[str]] = None,
        request_type: Optional[str] = None,
        procedure_found: bool = False,
        agent_confirmed: bool = False,
        question_signals: Optional[List[str]] = None,
        collected_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Construit la réponse standardisée du validateur."""
        return {
            "should_create": should_create,
            "reason": reason,
            "confidence": 0.95 if should_create else 0.85,
            "details": {
                "status": step,
                "missing_info": missing_fields or [],
                "request_type": request_type,
                "procedure_found": procedure_found,
                "agent_confirmed": agent_confirmed,
                "question_signals": question_signals or [],
                "collected_fields": collected_fields or [],
            },
        }

