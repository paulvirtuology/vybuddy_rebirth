#!/usr/bin/env python3
"""
Script pour parser les procédures standards basiques et les convertir en format structuré
"""
import asyncio
import sys
import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog

logger = structlog.get_logger()

# Mapping des procédures vers les catégories existantes
PROCEDURE_CATEGORIES = {
    "Demande accès dossier google drive partagé": "drive_access",
    "Demande de création de nouvelle adresse email": "email_accounts",
    "Demande de licence pour un outil": "licenses",
    "Problèmes de macbook": "macos_issues",
    "Demande d'accès aux salles de réunion": "meeting_rooms",
    "Demande de création de compte monday": "monday_access",
    "Demande d'accès à un board monday": "monday_access",
    "Problème de connexion wifi": "network_wifi",
    "Demande installation de logiciels": "software_installation",
    "Problème de timesheet": "timesheet",
    "Problème de google workspace": "workspace_tools"
}


def parse_procedure_text(text: str) -> Dict[str, Any]:
    """
    Parse une procédure depuis le texte brut
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    if not lines:
        return None
    
    # Le titre est la première ligne (sans les **)
    title = lines[0].replace('**', '').replace(':', '').strip()
    
    # Extraire les étapes
    steps = []
    diagnostic_questions = []
    ticket_info = {
        "when": "Après avoir collecté toutes les informations nécessaires",
        "required_fields": {
            "title": "Résumé de la demande",
            "description": "Détails complets de la demande et informations collectées",
            "priority": "Normal"
        }
    }
    
    step_number = 1
    current_substeps = []
    
    for i, line in enumerate(lines[1:], 1):
        line_lower = line.lower()
        
        # Ignorer les lignes vides
        if not line:
            continue
        
        # Détecter les questions de diagnostic (lignes qui commencent par Identifier, Demander, etc.)
        if line.startswith('Identifier'):
            item = line.replace('Identifier', '').strip()
            diagnostic_questions.append(f"Quel/Quelle est {item.lower()} ?")
        elif line.startswith('Demander'):
            item = line.replace('Demander', '').strip()
            if item:
                diagnostic_questions.append(f"{item} ?")
        elif line.startswith('Analyser'):
            item = line.replace('Analyser', '').strip()
            diagnostic_questions.append(f"Pouvez-vous analyser {item.lower()} ?")
        elif line.startswith('Vérifier'):
            item = line.replace('Vérifier', '').strip()
            diagnostic_questions.append(f"Pouvez-vous vérifier {item.lower()} ?")
        
        # Détecter les sous-étapes conditionnelles
        if line.startswith('*Si') or line.startswith('*si'):
            condition = line.replace('*', '').strip()
            current_substeps.append(condition)
        # Détecter les étapes normales
        elif not line.startswith('*') and line:
            # Vérifier si c'est une instruction de création de ticket
            if 'ticket' in line_lower or 'odoo' in line_lower:
                if 'ne pas insister' in line_lower or 'si non résolu' in line_lower or 'si toujours' in line_lower:
                    ticket_info["when"] = "Si le problème n'est pas résolu après les tentatives de diagnostic"
                elif 'si besoin' in line_lower or 'si nécessaire' in line_lower:
                    ticket_info["when"] = "Si une licence ou une validation est nécessaire"
                else:
                    ticket_info["when"] = "Après avoir collecté toutes les informations nécessaires"
                
                # Extraire les détails à inclure
                if 'détails' in line_lower or 'détails' in line:
                    ticket_info["required_fields"]["description"] = "Tous les détails collectés, étapes déjà effectuées, et informations de diagnostic"
                
                # Créer une étape pour la création de ticket
                action = line
                if current_substeps:
                    details = "\n".join([f"- {sub}" for sub in current_substeps])
                    current_substeps = []
                else:
                    details = ""
                
                steps.append({
                    "step": step_number,
                    "action": action,
                    "details": details,
                    "requires_admin": False
                })
                step_number += 1
            else:
                # Étape normale
                action = line
                requires_admin = any(keyword in line_lower for keyword in ['jamf', 'admin', 'système', 'paramètres'])
                
                details = ""
                if current_substeps:
                    details = "\n".join([f"- {sub}" for sub in current_substeps])
                    current_substeps = []
                
                steps.append({
                    "step": step_number,
                    "action": action,
                    "details": details,
                    "requires_admin": requires_admin
                })
                step_number += 1
    
    # Si pas d'étapes explicites, créer une étape générique basée sur le contenu
    if not steps:
        # Essayer d'extraire des informations du texte
        all_text = ' '.join(lines[1:])
        if 'identifier' in all_text.lower():
            steps.append({
                "step": 1,
                "action": "Identifier les informations nécessaires",
                "details": "Collecter toutes les informations demandées dans la procédure",
                "requires_admin": False
            })
            steps.append({
                "step": 2,
                "action": "Créer un ticket Odoo avec les détails collectés",
                "details": "",
                "requires_admin": False
            })
        else:
            steps.append({
                "step": 1,
                "action": "Suivre la procédure standard",
                "details": "Collecter les informations nécessaires selon la procédure",
                "requires_admin": False
            })
    
    # Si pas de questions de diagnostic, en créer des génériques
    if not diagnostic_questions:
        diagnostic_questions = [
            "Quel est le problème exact ?",
            "Depuis quand le problème existe-t-il ?"
        ]
    
    return {
        "title": title,
        "category": PROCEDURE_CATEGORIES.get(title, "other"),
        "description": f"Procédure standard pour {title.lower()}",
        "diagnostic_questions": diagnostic_questions,
        "resolution_steps": steps,
        "ticket_creation": ticket_info,
        "common_issues": [],
        "source_tickets_count": 0,
        "is_standard": True
    }


def parse_standard_procedures_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    Parse le fichier de procédures standards
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Séparer les procédures (délimitées par **)
    procedures = []
    current_procedure = ""
    
    for line in content.split('\n'):
        # Détecter le début d'une nouvelle procédure (ligne avec ** au début)
        if line.strip().startswith('**'):
            # Nouvelle procédure détectée
            if current_procedure:
                parsed = parse_procedure_text(current_procedure)
                if parsed:
                    procedures.append(parsed)
            current_procedure = line + '\n'
        elif current_procedure:
            current_procedure += line + '\n'
    
    # Ajouter la dernière procédure
    if current_procedure:
        parsed = parse_procedure_text(current_procedure)
        if parsed:
            procedures.append(parsed)
    
    return procedures


async def main():
    """Point d'entrée principal"""
    procedures_file = Path(__file__).parent.parent / "knowledge_base" / "standard_process_basic.txt"
    
    if not procedures_file.exists():
        logger.error(f"Standard procedures file not found: {procedures_file}")
        return
    
    # Parser les procédures
    procedures = parse_standard_procedures_file(procedures_file)
    
    logger.info(f"Parsed {len(procedures)} standard procedures")
    
    # Sauvegarder en JSON
    output_file = Path(__file__).parent.parent / "knowledge_base" / "standard_procedures.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(procedures, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved standard procedures to {output_file}")
    
    # Créer aussi des fichiers Markdown
    procedures_dir = Path(__file__).parent.parent / "data" / "knowledge_base" / "procedures"
    procedures_dir.mkdir(parents=True, exist_ok=True)
    
    for procedure in procedures:
        category = procedure["category"]
        # Créer un nom de fichier basé sur le titre
        filename = f"{category}_standard_{procedure['title'].lower().replace(' ', '_').replace(':', '').replace('é', 'e')[:50]}.md"
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
            if step.get("substeps"):
                md_content += "**Conditions:**\n"
                for substep in step["substeps"]:
                    md_content += f"- {substep}\n"
                md_content += "\n"
        
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
        
        md_content += f"\n---\n*Procédure standard basique*\n"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"Created procedure file: {filename}")


if __name__ == "__main__":
    asyncio.run(main())

