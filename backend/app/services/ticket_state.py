"""
Structures de données partagées pour la gestion des tickets.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TicketStep(str, Enum):
    DETECT = "detect"
    COLLECT_REQUIRED = "collect_required"
    DIAGNOSE = "diagnose"
    DECIDE = "decide"
    VALIDATE = "validate"
    CREATE = "create"


@dataclass
class ProcedureDefinition:
    request_type: str
    required_fields: List[str] = field(default_factory=list)
    diagnostic_steps: List[str] = field(default_factory=list)
    escalation_rules: Dict[str, Any] = field(default_factory=dict)
    requires_human_action: bool = True


@dataclass
class ConversationState:
    message: str
    history: List[Dict[str, str]]
    request_type: Optional[str] = None
    procedure: Optional[ProcedureDefinition] = None
    collected_fields: Dict[str, Any] = field(default_factory=dict)
    completed_steps: List[str] = field(default_factory=list)
    needs_human_action: bool = False
    agent_confirmed_action: bool = False
    question_signals: List[str] = field(default_factory=list)

    @property
    def missing_fields(self) -> List[str]:
        if not self.procedure:
            return []
        return [
            field_name
            for field_name in self.procedure.required_fields
            if field_name not in self.collected_fields
            or self.collected_fields.get(field_name) in (None, "")
        ]

    @property
    def diagnostic_incomplete(self) -> bool:
        if not self.procedure or not self.procedure.diagnostic_steps:
            return False
        return any(step not in self.completed_steps for step in self.procedure.diagnostic_steps)


@dataclass
class TicketDecision:
    step: TicketStep
    should_create: bool
    reason: str
    missing_fields: List[str] = field(default_factory=list)

