"""
Détection d'engagement d'action dans la réponse de l'agent.

Utilise des patterns stricts pour éviter les faux positifs.
Seules les phrases qui indiquent clairement une confirmation d'action sont détectées.
"""
from __future__ import annotations

import re
from typing import Tuple, List

# Patterns stricts pour la confirmation d'action
# Format: (pattern regex, description)
ACTION_PATTERNS = [
    # Confirmations explicites de création
    (re.compile(r"\bje\s+crée\b", re.IGNORECASE), "je crée"),
    (re.compile(r"\bje\s+vais\s+créer\b", re.IGNORECASE), "je vais créer"),
    (re.compile(r"\bje\s+lance\s+(?:la|une|le|les)\s+demande\b", re.IGNORECASE), "je lance la demande"),
    (re.compile(r"\bje\s+lance\s+(?:la|une|le|les)\s+création\b", re.IGNORECASE), "je lance la création"),
    (re.compile(r"\bje\s+crée\s+(?:la|une|le|les)\s+demande\b", re.IGNORECASE), "je crée la demande"),
    (re.compile(r"\bje\s+vais\s+créer\s+(?:un|une|le|la)\s+ticket\b", re.IGNORECASE), "je vais créer un ticket"),
    (re.compile(r"\bje\s+crée\s+(?:un|une|le|la)\s+ticket\b", re.IGNORECASE), "je crée un ticket"),
    
    # Confirmations avec "m'occupe"
    (re.compile(r"\bje\s+m['\s]occupe\b", re.IGNORECASE), "je m'occupe"),
    (re.compile(r"\bparfait[,\s]+je\s+m['\s]occupe\b", re.IGNORECASE), "parfait je m'occupe"),
    (re.compile(r"\bsuper[,\s]+je\s+m['\s]occupe\b", re.IGNORECASE), "super je m'occupe"),
    
    # Confirmations d'équipe
    (re.compile(r"\bnotre\s+équipe\s+s['\s]en\s+occupe\b", re.IGNORECASE), "notre équipe s'en occupe"),
    (re.compile(r"\bl['\s]équipe\s+(?:it\s+)?s['\s]en\s+charge\b", re.IGNORECASE), "l'équipe s'en charge"),
    (re.compile(r"\bl['\s]équipe\s+va\s+(?:créer|s['\s]en\s+occuper)\b", re.IGNORECASE), "l'équipe va créer"),
    
    # Confirmations de ticket
    (re.compile(r"\bun\s+ticket\s+va\s+être\s+créé\b", re.IGNORECASE), "un ticket va être créé"),
    (re.compile(r"\ble\s+ticket\s+va\s+être\s+créé\b", re.IGNORECASE), "le ticket va être créé"),
    (re.compile(r"\bticket\s+sera\s+créé\b", re.IGNORECASE), "ticket sera créé"),
    
    # Autres confirmations explicites
    (re.compile(r"\bje\s+vous\s+confirme\s+(?:que\s+)?(?:je\s+)?(?:vais\s+)?(?:créer|faire|m['\s]occuper)\b", re.IGNORECASE), "je vous confirme"),
    (re.compile(r"\bje\s+confirme[,\s]+(?:je\s+)?(?:vais\s+)?(?:créer|faire|m['\s]occuper)\b", re.IGNORECASE), "je confirme"),
    (re.compile(r"\bje\s+déclenche\s+(?:la|une|le|les)\s+(?:demande|création)\b", re.IGNORECASE), "je déclenche"),
]


def detect_agent_action(response: str) -> Tuple[bool, List[str]]:
    """
    Détecte si l'agent confirme explicitement qu'il crée/lance une action.
    
    Utilise des patterns stricts pour éviter les faux positifs.
    Ne détecte que les phrases qui indiquent clairement une confirmation d'action.
    
    Args:
        response: Réponse de l'agent
    
    Returns:
        Tuple (bool, List[str]): (True si action confirmée, liste des patterns détectés)
    """
    if not response or not response.strip():
        return (False, [])
    
    matches = []
    for pattern, description in ACTION_PATTERNS:
        if pattern.search(response):
            matches.append(description)
    
    return (len(matches) > 0, matches)

