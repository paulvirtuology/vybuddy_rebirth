"""
Validateur de tickets - Détermine si un ticket doit être créé
"""
from typing import Dict, Any, List
import structlog
from langchain_openai import ChatOpenAI

from app.core.config import settings

logger = structlog.get_logger()


class TicketValidator:
    """Valide si un ticket doit être créé basé sur le contexte"""
    
    # Mapping des types de demandes et informations requises (basé sur standard_process_basic.txt)
    REQUIRED_INFO = {
        "installation_logiciel": {
            "keywords": ["installer", "installation", "logiciel", "software", "app", "application", "excel", "office"],
            "required": ["numéro de série"],  # Un numéro de série MacBook est requis
            "optional": ["logiciel", "urgent", "urgence"]
        },
        "creation_email": {
            "keywords": ["créer", "création", "nouvelle adresse email", "nouveau email", "boucle email", "adresse email"],
            "required": ["nom", "société"],  # Nom et société minimaux requis
            "optional": ["bench", "pays", "fonction", "boucle", "personnes à inclure"]
        },
        "acces_drive": {
            "keywords": ["accès", "dossier", "google drive", "drive", "partagé"],
            "required": ["dossier", "raison"],  # Dossier et raison minimaux
            "optional": ["criticité"]
        },
        "licence": {
            "keywords": ["licence", "license", "office", "openai", "microsoft", "outil"],
            "required": ["outil"],  # L'outil est le minimum requis
            "optional": ["validation", "n+1", "personne"]
        },
        "acces_salle": {
            "keywords": ["salle", "réunion", "meeting room", "accès salle"],
            "required": ["salle", "personne"],
            "optional": []
        },
        "acces_monday": {
            "keywords": ["monday", "board", "accès monday", "compte monday"],
            "required": ["personne", "board"],
            "optional": ["licence", "validation"]
        },
        "probleme_macbook": {
            "keywords": ["macbook", "problème", "bug", "erreur", "ne fonctionne pas", "ne marche pas"],
            "required": ["diagnostic", "détails"],
            "optional": ["numéro de série"]
        },
        "probleme_wifi": {
            "keywords": ["wifi", "wifi", "connexion", "réseau", "internet", "pas de connexion"],
            "required": ["diagnostic", "étapes"],
            "optional": []
        }
    }
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-5",
            temperature=0.2,
            api_key=settings.OPENAI_API_KEY
        )
    
    def _detect_request_type(self, message: str, history: List[Dict[str, str]]) -> str:
        """Détecte le type de demande basé sur les mots-clés"""
        message_lower = message.lower()
        history_text = " ".join([h.get('user', '').lower() + " " + h.get('bot', '').lower() for h in (history or [])[-3:]])
        full_context = message_lower + " " + history_text
        
        # Compter les correspondances pour chaque type
        scores = {}
        for req_type, info in self.REQUIRED_INFO.items():
            score = sum(1 for keyword in info["keywords"] if keyword in full_context)
            if score > 0:
                scores[req_type] = score
        
        if scores:
            # Retourner le type avec le score le plus élevé
            return max(scores.items(), key=lambda x: x[1])[0]
        return None
    
    def _check_required_info(self, request_type: str, message: str, agent_response: str, history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Vérifie si les informations requises sont présentes dans l'historique"""
        if not request_type or request_type not in self.REQUIRED_INFO:
            return {"has_all_required": True, "missing_info": []}  # Pas de validation structurée si type non détecté
        
        required = self.REQUIRED_INFO[request_type]["required"]
        
        # Construire le contexte complet
        history_text = " ".join([h.get('user', '').lower() + " " + h.get('bot', '').lower() for h in (history or [])[-5:]])
        full_context = (message.lower() + " " + agent_response.lower() + " " + history_text)
        
        missing = []
        for info in required:
            # Vérifier si l'information est présente (flexible avec différentes formulations)
            found = False
            if info == "numéro de série" or info == "série" or info == "serial":
                found = any(term in full_context for term in ["numéro de série", "numéro série", "serial", "série", "n° de série", "n° série"])
            elif info == "nom" or info == "personne":
                # Le nom peut être dans le user_id, mais on vérifie aussi s'il est mentionné explicitement
                found = any(term in full_context for term in ["nom", "prénom", "name", "personne", "utilisateur"])
            elif info == "dossier":
                found = any(term in full_context for term in ["dossier", "folder", "document", "fichier"])
            elif info == "raison" or info == "pourquoi":
                found = any(term in full_context for term in ["raison", "pourquoi", "pour", "cause", "motif", "besoin"])
            elif info == "salle":
                found = any(term in full_context for term in ["salle", "room", "réunion", "meeting"])
            elif info == "outil":
                found = any(term in full_context for term in ["outil", "tool", "office", "openai", "microsoft", "logiciel", "software"])
            elif info == "board":
                found = any(term in full_context for term in ["board", "tableau", "monday"])
            elif info == "diagnostic" or info == "détails" or info == "étapes":
                # Pour les problèmes, on considère qu'il y a un diagnostic si l'agent a posé des questions ou donné des solutions
                found = len(history or []) > 1 or "diagnostic" in full_context or "étape" in full_context or "solution" in full_context
            elif info == "criticité":
                found = any(term in full_context for term in ["criticité", "critique", "urgent", "important", "priorité"])
            elif info == "validation" or info == "n+1":
                found = any(term in full_context for term in ["validation", "n+1", "manager", "superviseur", "validé", "approuvé"])
            else:
                # Recherche générique
                found = info.lower() in full_context
            
            if not found:
                missing.append(info)
        
        return {
            "has_all_required": len(missing) == 0,
            "missing_info": missing
        }
    
    async def should_create_ticket(
        self,
        message: str,
        agent_response: str,
        agent_used: str,
        history: List[Dict[str, str]] = None,
        needs_ticket_suggested: bool = False
    ) -> Dict[str, Any]:
        """
        Évalue si un ticket doit être créé
        
        Args:
            message: Message original de l'utilisateur
            agent_response: Réponse de l'agent
            agent_used: Agent qui a traité la demande
            history: Historique de la conversation
            needs_ticket_suggested: Si l'agent a suggéré un ticket
            
        Returns:
            Dict avec 'should_create' (bool) et 'reason' (str)
        """
        # Construire le contexte de la conversation
        history_context = ""
        if history:
            history_context = "\n".join([
                f"User: {h.get('user', '')}\nBot: {h.get('bot', '')}"
                for h in history[-5:]
            ])
        
        # Cas où on ne crée PAS de ticket (seulement si c'est une simple salutation/merci sans contexte)
        exclusion_keywords = [
            "salutation",
            "bonjour",
            "hello",
            "hi",
            "au revoir",
            "goodbye",
            "question simple",
            "information générale",
            "déjà résolu",
            "problème résolu",
            "ça fonctionne",
            "c'est bon",
            "ok"
        ]
        
        message_lower = message.lower()
        response_lower = agent_response.lower()
        
        # Vérifier les exclusions évidentes (mais pas "merci" ou "parfait" car ils peuvent être dans un contexte de création de ticket)
        for keyword in exclusion_keywords:
            # Ne pas exclure si le message contient des mots-clés de demande (création, accès, etc.)
            if keyword in message_lower or keyword in response_lower:
                # Si c'est juste une salutation simple sans contexte, exclure
                if keyword in ["salutation", "bonjour", "hello", "hi"] and len(message.split()) <= 2:
                    return {
                        "should_create": False,
                        "reason": f"Message exclu: {keyword}",
                        "confidence": 0.9
                    }
                # Pour les autres mots, vérifier s'il y a un contexte de demande
                if keyword not in ["salutation", "bonjour", "hello", "hi"]:
                    # Ne pas exclure si l'agent indique qu'il va créer/faire quelque chose
                    action_indicators = ["je m'occupe", "je vais créer", "je vais faire", "je crée", "je fais", "création", "créer", "faire"]
                    if not any(action in response_lower for action in action_indicators):
                        return {
                            "should_create": False,
                            "reason": f"Message exclu: {keyword}",
                            "confidence": 0.9
                        }
        
        # Si le message est très court et n'est pas un problème technique
        if len(message.split()) <= 3 and not any(tech_word in message_lower for tech_word in ["wifi", "réseau", "connexion", "problème", "erreur", "bug"]):
            return {
                "should_create": False,
                "reason": "Message trop court et non technique",
                "confidence": 0.8
            }
        
        # Détecter le type de demande et vérifier les informations requises
        request_type = self._detect_request_type(message, history)
        info_check = self._check_required_info(request_type, message, agent_response, history)
        
        # Si des informations essentielles manquent ET que le type est détecté, ne PAS créer de ticket
        if request_type and not info_check["has_all_required"]:
            missing_str = ", ".join(info_check["missing_info"])
            return {
                "should_create": False,
                "reason": f"Informations manquantes pour cette demande: {missing_str}. L'agent doit d'abord collecter ces informations avant de créer un ticket.",
                "confidence": 0.92
            }
        
        # Vérifier si l'agent pose encore des questions (ne pas créer de ticket si c'est le cas)
        question_indicators = [
            "?", "pouvez-vous", "pourriez-vous", "auriez-vous", "avez-vous", "j'aurais besoin",
            "quel est", "quelle est", "quels sont", "quelles sont", "comment", "où", "quand",
            "pouvez vous", "pourriez vous", "auriez vous", "avez vous", "j aurais besoin",
            "vous avez", "vous les avez", "vous pouvez", "vous pourriez", "me donner",
            "me dire", "me confirmer", "me préciser", "me renseigner", "me fournir"
        ]
        
        agent_response_lower = agent_response.lower()
        is_asking_question = any(indicator in agent_response_lower for indicator in question_indicators)
        
        # Vérifier si l'agent indique qu'il va créer/faire quelque chose (signe que toutes les infos sont collectées)
        action_indicators = [
            "je m'occupe", "je vais créer", "je vais faire", "je crée", "je fais",
            "création", "créer", "faire", "je vous confirme", "je confirme",
            "notre équipe", "l'équipe va", "on va créer", "on va faire",
            "un ticket va être créé", "je vais créer un ticket", "créer un ticket",
            "ticket sera créé", "ticket va être créé", "notre équipe s'en occupe",
            "parfait", "super", "c'est noté", "merci"  # Peut indiquer que tout est collecté
        ]
        is_taking_action = any(indicator in agent_response_lower for indicator in action_indicators)
        
        # Si l'agent pose une question ET ne prend pas d'action, ne PAS créer de ticket
        if is_asking_question and not is_taking_action:
            return {
                "should_create": False,
                "reason": "L'agent pose encore des questions pour obtenir les informations nécessaires. Attendre la réponse de l'utilisateur avant de créer un ticket.",
                "confidence": 0.95
            }
        
        # Si l'agent indique qu'il va créer/faire quelque chose ET que les infos sont collectées, créer le ticket
        if is_taking_action and not is_asking_question:
            # Vérifier si c'est une demande qui nécessite une intervention humaine
            human_intervention_keywords = [
                "créer", "boucle", "adresse email", "compte", "accès", "licence",
                "installation", "logiciel", "ticket", "odoo"
            ]
            if any(keyword in agent_response_lower or keyword in message_lower for keyword in human_intervention_keywords):
                # Vérification supplémentaire: si le type est détecté, s'assurer que les infos sont là
                if request_type and info_check["has_all_required"]:
                    return {
                        "should_create": True,
                        "reason": f"Toutes les informations nécessaires sont collectées ({request_type}). L'agent confirme la création du ticket.",
                        "confidence": 0.95
                    }
                elif not request_type:
                    # Type non détecté mais action claire = créer le ticket (validation LLM le confirmera)
                    return {
                        "should_create": True,
                        "reason": "L'agent indique qu'il va créer/faire quelque chose qui nécessite une intervention humaine. Toutes les informations semblent collectées. Un ticket doit être créé.",
                        "confidence": 0.9
                    }
        
        # Construire le contexte de validation structurée pour le LLM
        validation_context = ""
        if request_type:
            validation_context = f"\n\nTYPE DE DEMANDE DÉTECTÉ: {request_type}"
            if info_check["has_all_required"]:
                validation_context += "\n✅ Toutes les informations requises sont présentes."
            else:
                validation_context += f"\n❌ Informations manquantes: {', '.join(info_check['missing_info'])}"
        
        # Prompt pour l'évaluation LLM (amélioré avec contexte structuré)
        evaluation_prompt = f"""Vous êtes un validateur de tickets de support IT. Votre rôle est de déterminer si un ticket doit être créé dans Odoo.

{validation_context}

Règles de validation CRITIQUES:
1. Créer un ticket OBLIGATOIREMENT si:
   - L'agent dit qu'il va "créer", "faire", "s'occuper de" quelque chose qui nécessite une intervention humaine
   - ET TOUTES les informations nécessaires ont été collectées (l'agent NE pose PLUS de questions)
   - ET l'agent confirme qu'il va procéder (pas seulement proposer)
   - Le problème nécessite une intervention humaine (création de compte, boucle email, accès, permissions, matériel, installation logiciel)
   - L'utilisateur demande explicitement un ticket
   - Le problème technique n'a pas pu être résolu après diagnostic
   - Le problème est complexe et nécessite une escalade
   - L'agent a épuisé toutes les solutions possibles

2. NE PAS créer de ticket si:
   - Le problème a été résolu
   - C'est une simple question d'information
   - C'est une salutation ou un message court (sans contexte de demande)
   - L'utilisateur demande juste des informations générales
   - Le problème peut être résolu par l'utilisateur avec les instructions données
   - L'agent pose ENCORE des questions pour obtenir des informations (même s'il a dit qu'il va créer quelque chose)
   - L'agent demande des informations supplémentaires (numéro de série, nom, email, détails, etc.)
   - L'agent utilise des mots comme "pourriez-vous", "avez-vous", "j'aurais besoin de", "j'ai besoin de", "donnez-moi", etc.
   - Des informations essentielles manquent selon le type de demande détecté

CAS SPÉCIFIQUES IMPORTANTS - RÈGLE D'OR:
- Si l'agent pose ENCORE une question ou demande ENCORE des informations (même après avoir dit qu'il va créer quelque chose) → NE PAS créer de ticket. L'agent doit d'abord collecter toutes les informations.
- Si l'agent dit "Je m'occupe de créer..." mais demande ensuite "Pourriez-vous me donner..." → NE PAS créer de ticket car des informations manquent encore.
- Si l'agent dit "Parfait" ou "Merci" APRÈS avoir collecté toutes les infos ET qu'il n'y a plus de questions → CRÉER UN TICKET
- Si l'agent dit "Parfait" ou "Merci" SANS contexte de création/action → NE PAS créer de ticket
- Si des informations essentielles manquent selon le type de demande → NE PAS créer de ticket, même s'il a dit qu'il va créer quelque chose
- Pour une installation logiciel: vérifier qu'un numéro de série MacBook a été fourni
- Pour une création email/boucle: vérifier que nom, société, et autres détails sont présents
- Pour un accès: vérifier que la raison et les détails sont collectés

Message utilisateur: {message}

Réponse de l'agent ({agent_used}): {agent_response}

Historique récent:
{history_context if history_context else "Aucun historique"}

L'agent a-t-il suggéré un ticket? {needs_ticket_suggested}

IMPORTANT: 
- Si l'agent indique qu'il va créer/faire quelque chose (ex: "Je m'occupe de créer..."), CRÉER UN TICKET car le système ne peut pas faire ces actions lui-même.
- Si l'agent pose encore des questions SANS indiquer qu'il va créer/faire quelque chose, NE PAS créer de ticket.

Analysez la situation et répondez au format JSON:
{{
    "should_create": true/false,
    "reason": "Explication détaillée de la décision",
    "confidence": 0.0-1.0
}}

Répondez UNIQUEMENT avec le JSON, sans texte supplémentaire."""

        try:
            response = await self.llm.ainvoke(evaluation_prompt)
            response_text = response.content.strip()
            
            # Extraire le JSON de la réponse
            import json
            import re
            
            # Chercher le JSON dans la réponse
            json_match = re.search(r'\{[^{}]*"should_create"[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # Essayer de parser toute la réponse
                result = json.loads(response_text)
            
            logger.info(
                "Ticket validation result",
                should_create=result.get("should_create", False),
                reason=result.get("reason", ""),
                confidence=result.get("confidence", 0.5),
                agent=agent_used
            )
            
            return {
                "should_create": result.get("should_create", False),
                "reason": result.get("reason", "Évaluation par LLM"),
                "confidence": result.get("confidence", 0.5)
            }
            
        except Exception as e:
            logger.error("Ticket validation error", error=str(e))
            # En cas d'erreur, être conservateur: ne créer un ticket que si explicitement suggéré
            return {
                "should_create": needs_ticket_suggested and len(message.split()) > 5,
                "reason": f"Erreur de validation: {str(e)}. Décision conservatrice basée sur suggestion.",
                "confidence": 0.5
            }

