#!/usr/bin/env python3
"""
Script pour structurer les tickets en procédures réutilisables
Étape 2: Structuration en procédures
"""
import asyncio
import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
import structlog

logger = structlog.get_logger()


async def create_procedure_from_tickets(
    category: str,
    tickets: List[str],
    llm: ChatOpenAI
) -> Dict[str, Any]:
    """
    Crée une procédure réutilisable à partir d'un groupe de tickets similaires
    """
    tickets_text = "\n".join([f"- {ticket}" for ticket in tickets[:20]])  # Limiter à 20 tickets
    
    prompt = f"""À partir de ces tickets résolus de support IT, créez une procédure standardisée réutilisable.

Catégorie: {category}
Tickets résolus:
{tickets_text}

Créez une procédure structurée qui:
1. Identifie le type de demande
2. Liste les questions de diagnostic à poser (comme un support N1 humain)
3. Définit les étapes de résolution
4. Indique quand créer un ticket Odoo et quelles informations inclure

Format de réponse JSON:
{{
    "title": "Titre de la procédure",
    "category": "{category}",
    "description": "Description courte",
    "diagnostic_questions": [
        "Question 1 à poser",
        "Question 2 à poser"
    ],
    "resolution_steps": [
        {{
            "step": 1,
            "action": "Action à effectuer",
            "details": "Détails supplémentaires",
            "requires_admin": false
        }}
    ],
    "ticket_creation": {{
        "when": "Quand créer un ticket Odoo",
        "required_fields": {{
            "title": "Format du titre",
            "description": "Informations à inclure",
            "priority": "priorité suggérée"
        }}
    }},
    "common_issues": [
        "Problème fréquent 1",
        "Problème fréquent 2"
    ]
}}
"""

    try:
        messages = [
            SystemMessage(content="Vous êtes un expert en création de procédures IT. Répondez uniquement en JSON valide. Les procédures doivent être claires, actionnables et suivre les meilleures pratiques de support N1."),
            HumanMessage(content=prompt)
        ]
        response = await llm.ainvoke(messages)
        
        # Extraire le JSON
        content = response.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        
        procedure = json.loads(content)
        procedure["category"] = category
        procedure["source_tickets_count"] = len(tickets)
        
        return procedure
    except Exception as e:
        logger.error(f"Error creating procedure for category {category}: {e}")
        # Procédure de fallback
        return {
            "title": f"Procédure {category}",
            "category": category,
            "description": f"Procédure générée automatiquement pour {category}",
            "diagnostic_questions": [
                "Quel est le problème exact ?",
                "Depuis quand le problème existe-t-il ?"
            ],
            "resolution_steps": [
                {
                    "step": 1,
                    "action": "Diagnostiquer le problème",
                    "details": "Collecter les informations nécessaires",
                    "requires_admin": False
                }
            ],
            "ticket_creation": {
                "when": "Si le problème nécessite une intervention admin",
                "required_fields": {
                    "title": "Résumé du problème",
                    "description": "Détails du problème et actions déjà tentées",
                    "priority": "Normal"
                }
            },
            "common_issues": [],
            "source_tickets_count": len(tickets)
        }


async def create_procedures_from_categorized_tickets(
    categorized_file: Path
) -> List[Dict[str, Any]]:
    """
    Crée des procédures à partir des tickets catégorisés
    """
    # Charger les tickets catégorisés
    with open(categorized_file, 'r', encoding='utf-8') as f:
        categorized_tickets = json.load(f)
    
    # Grouper par catégorie
    tickets_by_category = defaultdict(list)
    for item in categorized_tickets:
        category = item["category"]
        tickets_by_category[category].append(item["ticket"])
    
    logger.info(f"Creating procedures for {len(tickets_by_category)} categories")
    
    llm = ChatOpenAI(
        model="gpt-4o",  # Modèle plus puissant pour créer des procédures
        temperature=0.2,
        api_key=settings.OPENAI_API_KEY
    )
    
    procedures = []
    
    # Créer une procédure par catégorie
    for category, tickets in tickets_by_category.items():
        logger.info(f"Creating procedure for {category} ({len(tickets)} tickets)")
        
        # Limiter le nombre de tickets pour éviter les tokens excessifs
        tickets_sample = tickets[:30] if len(tickets) > 30 else tickets
        
        procedure = await create_procedure_from_tickets(category, tickets_sample, llm)
        procedures.append(procedure)
    
    return procedures


async def main():
    """Point d'entrée principal"""
    # Chemin vers le fichier de tickets catégorisés
    categorized_file = Path(__file__).parent.parent / "knowledge_base" / "tickets_categorises.json"
    
    if not categorized_file.exists():
        logger.error(f"Categorized tickets file not found: {categorized_file}")
        logger.info("Run categorize_tickets.py first")
        return
    
    # Créer les procédures
    procedures = await create_procedures_from_categorized_tickets(categorized_file)
    
    # Sauvegarder les procédures
    output_file = Path(__file__).parent.parent / "knowledge_base" / "procedures.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(procedures, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(procedures)} procedures to {output_file}")
    
    # Créer aussi des fichiers Markdown pour chaque procédure
    procedures_dir = Path(__file__).parent.parent / "data" / "knowledge_base" / "procedures"
    procedures_dir.mkdir(parents=True, exist_ok=True)
    
    for procedure in procedures:
        category = procedure["category"]
        filename = f"{category}_procedure.md"
        filepath = procedures_dir / filename
        
        # Convertir en Markdown
        md_content = f"""# {procedure['title']}

**Catégorie:** {category}
**Description:** {procedure['description']}

## Questions de diagnostic

"""
        for q in procedure.get("diagnostic_questions", []):
            md_content += f"- {q}\n"
        
        md_content += "\n## Étapes de résolution\n\n"
        for step in procedure.get("resolution_steps", []):
            admin_note = " (nécessite droits admin)" if step.get("requires_admin") else ""
            md_content += f"### Étape {step['step']}: {step['action']}{admin_note}\n\n"
            if step.get("details"):
                md_content += f"{step['details']}\n\n"
        
        md_content += "\n## Création de ticket Odoo\n\n"
        ticket_info = procedure.get("ticket_creation", {})
        md_content += f"**Quand créer un ticket:** {ticket_info.get('when', 'Si nécessaire')}\n\n"
        md_content += "**Champs requis:**\n"
        fields = ticket_info.get("required_fields", {})
        for field, value in fields.items():
            md_content += f"- **{field}:** {value}\n"
        
        if procedure.get("common_issues"):
            md_content += "\n## Problèmes fréquents\n\n"
            for issue in procedure["common_issues"]:
                md_content += f"- {issue}\n"
        
        md_content += f"\n---\n*Procédure générée à partir de {procedure.get('source_tickets_count', 0)} tickets résolus*\n"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"Created procedure file: {filename}")


if __name__ == "__main__":
    asyncio.run(main())

