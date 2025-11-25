"""
Extracteur structuré de champs depuis la conversation.

Utilise un LLM pour extraire les valeurs réelles des champs requis
définis dans les procédures de la Knowledge Base.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
import json
import structlog

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import settings
from .ticket_state import ProcedureDefinition

logger = structlog.get_logger()


class FieldExtractor:
    """
    Extrait automatiquement les valeurs des champs requis depuis l'historique
    de conversation en utilisant un LLM pour une extraction contextuelle précise.
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,  # Déterministe
            api_key=settings.OPENAI_API_KEY,
        )

    async def extract_fields(
        self,
        request_type: str,
        procedure: ProcedureDefinition,
        history: List[Dict[str, str]],
        current_message: str,
    ) -> Dict[str, Any]:
        """
        Extrait les valeurs des champs requis depuis l'historique.

        Args:
            request_type: Type de demande (ex: "installation_logiciel")
            procedure: Définition de la procédure avec les champs requis
            history: Historique de la conversation
            current_message: Dernier message de l'utilisateur

        Returns:
            Dict avec les champs extraits et leurs valeurs réelles
        """
        if not procedure or not procedure.required_fields:
            logger.debug("No required fields to extract", request_type=request_type)
            return {}

        # Construire le contexte conversationnel
        conversation_text = self._build_conversation_context(history, current_message)

        # Construire la description des champs requis
        fields_description = self._build_fields_description(procedure.required_fields)

        # Prompt structuré pour l'extraction
        prompt = f"""Tu es un extracteur structuré d'informations pour un système IT.

TYPE DE DEMANDE: {request_type}

CHAMPS REQUIS À EXTRAIRE:
{fields_description}

HISTORIQUE DE LA CONVERSATION:
{conversation_text}

TÂCHE:
Extrais UNIQUEMENT les valeurs des champs listés ci-dessus depuis l'historique.
Si un champ n'est pas mentionné dans la conversation, utilise null.
Si un champ est partiellement mentionné, extrais ce qui est disponible.

RÈGLES:
- Retourne UNIQUEMENT un JSON valide, sans texte supplémentaire
- Utilise null pour les champs non trouvés
- Pour les listes (ex: emails, noms), retourne un tableau JSON
- Normalise les valeurs (trim, lowercase si approprié)
- Si plusieurs valeurs sont mentionnées, prends la plus récente

FORMAT DE RÉPONSE (JSON):
{{
    "champ1": "valeur extraite ou null",
    "champ2": ["liste", "de", "valeurs"] ou null,
    ...
}}
"""

        try:
            response = await self.llm.ainvoke([
                SystemMessage(
                    content="Tu es un extracteur de données structurées. Réponds UNIQUEMENT en JSON valide, sans explication."
                ),
                HumanMessage(content=prompt.strip()),
            ])

            # Parser la réponse JSON
            content = response.content.strip()
            
            # Nettoyer la réponse (enlever markdown code blocks si présents)
            if content.startswith("```"):
                # Extraire le JSON du code block
                lines = content.split("\n")
                json_lines = [l for l in lines if not l.strip().startswith("```")]
                content = "\n".join(json_lines)
            
            extracted = json.loads(content)
            
            # Valider et normaliser les résultats
            normalized = self._normalize_extracted_fields(extracted, procedure.required_fields)
            
            logger.info(
                "Fields extracted",
                request_type=request_type,
                fields_found=list(normalized.keys()),
                fields_missing=[f for f in procedure.required_fields if f not in normalized or normalized.get(f) is None],
            )
            
            return normalized

        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to parse LLM response as JSON",
                error=str(e),
                response_preview=response.content[:200] if 'response' in locals() else "N/A",
            )
            return {}
        except Exception as e:
            logger.error("Field extraction failed", error=str(e), request_type=request_type)
            return {}

    def _build_conversation_context(
        self, history: List[Dict[str, str]], current_message: str
    ) -> str:
        """Construit le texte de la conversation pour le prompt."""
        lines = []
        
        # Ajouter l'historique récent (derniers 5 échanges)
        for h in history[-5:]:
            user_msg = h.get("user", "").strip()
            bot_msg = h.get("bot", "").strip()
            if user_msg:
                lines.append(f"Utilisateur: {user_msg}")
            if bot_msg:
                lines.append(f"Assistant: {bot_msg}")
        
        # Ajouter le message actuel
        if current_message.strip():
            lines.append(f"Utilisateur: {current_message.strip()}")
        
        return "\n".join(lines) if lines else "Aucune conversation."

    def _build_fields_description(self, required_fields: List[str]) -> str:
        """Construit la description des champs requis pour le prompt."""
        descriptions = {
            "logiciel": "Nom du logiciel à installer (ex: Microsoft Word, Excel, etc.)",
            "software_name": "Nom du logiciel à installer",
            "nom": "Nom de la personne concernée",
            "prénom": "Prénom de la personne concernée",
            "email": "Adresse email (peut être une liste)",
            "emails": "Liste d'adresses email",
            "dossier": "Nom du dossier/Drive concerné",
            "folder_name": "Nom du dossier Google Drive",
            "raison": "Raison/motif de la demande",
            "reason": "Raison de l'accès ou de la demande",
            "board_name": "Nom du board Monday.com",
            "société": "Société/Bench de la personne",
            "company": "Société de la personne",
            "numéro de série": "Numéro de série du MacBook",
            "serial_number": "Numéro de série du MacBook",
            "device_id": "Identifiant de l'appareil",
            "network_name": "Nom du réseau WiFi",
            "location": "Localisation/emplacement",
            "salle": "Nom de la salle",
            "room": "Nom de la salle",
        }
        
        lines = []
        for field in required_fields:
            desc = descriptions.get(field, f"Valeur du champ '{field}'")
            lines.append(f"- {field}: {desc}")
        
        return "\n".join(lines) if lines else "Aucun champ requis."

    def _normalize_extracted_fields(
        self, extracted: Dict[str, Any], required_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Normalise et valide les champs extraits.
        S'assure que tous les champs requis sont présents (avec null si non trouvés).
        """
        normalized = {}
        
        for field in required_fields:
            value = extracted.get(field)
            
            # Normaliser les valeurs
            if value is None or value == "" or value == "null":
                normalized[field] = None
            elif isinstance(value, str):
                # Trim et nettoyer
                cleaned = value.strip()
                normalized[field] = cleaned if cleaned else None
            elif isinstance(value, list):
                # Nettoyer les listes
                cleaned_list = [v.strip() for v in value if v and str(v).strip()]
                normalized[field] = cleaned_list if cleaned_list else None
            else:
                normalized[field] = value
        
        return normalized

