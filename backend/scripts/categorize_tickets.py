#!/usr/bin/env python3
"""
Script pour catégoriser automatiquement les tickets résolus
Étape 1: Catégorisation automatique
"""
import asyncio
import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Any

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
import structlog

logger = structlog.get_logger()

# Catégories principales identifiées
CATEGORIES = {
    "email_accounts": {
        "name": "Gestion des comptes email",
        "keywords": ["gmail", "email", "mail", "compte", "adresse", "signature", "boucle"],
        "description": "Création, modification, suppression de comptes email, signatures, boucles de mail"
    },
    "monday_access": {
        "name": "Accès et configuration Monday.com",
        "keywords": ["monday", "board", "accès", "dashboard", "automation"],
        "description": "Gestion des accès Monday, création de boards, automatisations"
    },
    "drive_access": {
        "name": "Accès Google Drive",
        "keywords": ["drive", "partage", "fichier", "document"],
        "description": "Gestion des accès Drive, partage de fichiers, récupération de documents"
    },
    "software_installation": {
        "name": "Installation de logiciels",
        "keywords": ["installation", "app", "logiciel", "software", "download", "vygeek store"],
        "description": "Installation, désinstallation, mise à jour de logiciels et applications"
    },
    "network_wifi": {
        "name": "Problèmes réseau et WiFi",
        "keywords": ["wifi", "réseau", "connexion", "internet", "vyfrance"],
        "description": "Problèmes de connexion WiFi, réseau bureau, configuration réseau"
    },
    "macos_issues": {
        "name": "Problèmes macOS et MacBook",
        "keywords": ["mac", "macbook", "macos", "sonoma", "mise à jour", "réinitialiser"],
        "description": "Problèmes macOS, mises à jour, réinitialisation, configuration MacBook"
    },
    "licenses": {
        "name": "Gestion des licences",
        "keywords": ["licence", "license", "microsoft", "office", "intellij", "adobe"],
        "description": "Gestion des licences logicielles (Microsoft, IntelliJ, Adobe, etc.)"
    },
    "workspace_tools": {
        "name": "Outils workspace (DocuSign, LastPass, etc.)",
        "keywords": ["docusign", "lastpass", "authenticator", "lucidchart", "confluence"],
        "description": "Gestion des accès et configuration des outils workspace"
    },
    "timesheet": {
        "name": "Gestion Timesheet",
        "keywords": ["timesheet", "temps", "tracking", "client", "tâche"],
        "description": "Problèmes et modifications liés au suivi du temps (Timesheet)"
    },
    "meeting_rooms": {
        "name": "Réservation de salles de réunion",
        "keywords": ["salle", "meeting", "réunion", "booking", "réservation"],
        "description": "Gestion des réservations de salles, accès aux salles"
    },
    "other": {
        "name": "Autres",
        "keywords": [],
        "description": "Tickets ne correspondant à aucune catégorie spécifique"
    }
}


async def categorize_ticket(ticket_title: str, llm: ChatOpenAI) -> Dict[str, Any]:
    """
    Catégorise un ticket en utilisant le LLM
    """
    prompt = f"""Analysez ce ticket de support IT et catégorisez-le.

Ticket: {ticket_title}

Catégories disponibles:
{json.dumps({k: v['name'] for k, v in CATEGORIES.items()}, indent=2, ensure_ascii=False)}

Répondez au format JSON:
{{
    "category": "nom_de_la_categorie",
    "confidence": 0.0-1.0,
    "reasoning": "explication courte"
}}
"""

    try:
        messages = [
            SystemMessage(content="Vous êtes un expert en catégorisation de tickets IT. Répondez uniquement en JSON valide."),
            HumanMessage(content=prompt)
        ]
        response = await llm.ainvoke(messages)
        
        # Extraire le JSON de la réponse
        content = response.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        
        result = json.loads(content)
        return result
    except Exception as e:
        logger.warning(f"Error categorizing ticket '{ticket_title}': {e}")
        # Fallback: catégorisation par mots-clés
        return categorize_by_keywords(ticket_title)


def categorize_by_keywords(ticket_title: str) -> Dict[str, Any]:
    """
    Catégorisation de fallback par mots-clés
    """
    ticket_lower = ticket_title.lower()
    
    for category_id, category_info in CATEGORIES.items():
        if category_id == "other":
            continue
        for keyword in category_info["keywords"]:
            if keyword.lower() in ticket_lower:
                return {
                    "category": category_id,
                    "confidence": 0.7,
                    "reasoning": f"Mot-clé détecté: {keyword}"
                }
    
    return {
        "category": "other",
        "confidence": 0.5,
        "reasoning": "Aucun mot-clé spécifique détecté"
    }


async def categorize_all_tickets(tickets_file: Path) -> List[Dict[str, Any]]:
    """
    Catégorise tous les tickets du fichier
    """
    llm = ChatOpenAI(
        model="gpt-4o-mini",  # Modèle rapide et économique pour la catégorisation
        temperature=0.1,
        api_key=settings.OPENAI_API_KEY
    )
    
    # Lire les tickets
    with open(tickets_file, 'r', encoding='utf-8') as f:
        tickets = [line.strip() for line in f if line.strip()]
    
    logger.info(f"Found {len(tickets)} tickets to categorize")
    
    categorized_tickets = []
    
    # Catégoriser par batch pour optimiser
    batch_size = 10
    for i in range(0, len(tickets), batch_size):
        batch = tickets[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(tickets) + batch_size - 1)//batch_size}")
        
        tasks = [categorize_ticket(ticket, llm) for ticket in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for ticket, result in zip(batch, results):
            if isinstance(result, Exception):
                logger.error(f"Error categorizing ticket '{ticket}': {result}")
                # Fallback
                result = categorize_by_keywords(ticket)
            
            categorized_tickets.append({
                "ticket": ticket,
                "category": result.get("category", "other"),
                "confidence": result.get("confidence", 0.5),
                "reasoning": result.get("reasoning", "")
            })
    
    return categorized_tickets


async def main():
    """Point d'entrée principal"""
    # Chemin vers le fichier de tickets
    tickets_file = Path(__file__).parent.parent / "knowledge_base" / "tickets_resolus.txt"
    
    if not tickets_file.exists():
        logger.error(f"Tickets file not found: {tickets_file}")
        return
    
    # Catégoriser tous les tickets
    categorized = await categorize_all_tickets(tickets_file)
    
    # Sauvegarder les résultats
    output_file = Path(__file__).parent.parent / "knowledge_base" / "tickets_categorises.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(categorized, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved categorized tickets to {output_file}")
    
    # Statistiques par catégorie
    stats = {}
    for item in categorized:
        cat = item["category"]
        stats[cat] = stats.get(cat, 0) + 1
    
    logger.info("Category statistics:")
    for cat, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {cat}: {count} tickets")


if __name__ == "__main__":
    asyncio.run(main())

