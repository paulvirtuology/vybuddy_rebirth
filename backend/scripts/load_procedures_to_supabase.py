#!/usr/bin/env python3
"""
Script pour charger les procédures dans Supabase
Étape 5: Stockage dans Supabase
"""
import asyncio
import sys
import os
import json
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.supabase_client import SupabaseClient
from app.core.config import settings
import structlog

logger = structlog.get_logger()


async def load_procedures_to_supabase(procedures_file: Path):
    """
    Charge les procédures dans Supabase
    """
    supabase = SupabaseClient()
    client = supabase._get_client()
    
    # Charger les procédures
    with open(procedures_file, 'r', encoding='utf-8') as f:
        procedures = json.load(f)
    
    logger.info(f"Loading {len(procedures)} procedures to Supabase")
    
    for procedure in procedures:
        try:
            # Préparer les données
            data = {
                "category": procedure["category"],
                "title": procedure["title"],
                "description": procedure.get("description", ""),
                "diagnostic_questions": json.dumps(procedure.get("diagnostic_questions", [])),
                "resolution_steps": json.dumps(procedure.get("resolution_steps", [])),
                "ticket_creation": json.dumps(procedure.get("ticket_creation", {})),
                "common_issues": json.dumps(procedure.get("common_issues", [])),
                "source_tickets_count": procedure.get("source_tickets_count", 0)
            }
            
            # Insérer ou mettre à jour (upsert)
            result = client.table("procedures").upsert(
                data,
                on_conflict="category,title"
            ).execute()
            
            logger.info(f"Loaded procedure: {procedure['title']} ({procedure['category']})")
            
        except Exception as e:
            logger.error(f"Error loading procedure {procedure.get('title', 'unknown')}: {e}")
    
    logger.info("Finished loading procedures to Supabase")


async def main():
    """Point d'entrée principal"""
    procedures_file = Path(__file__).parent.parent / "knowledge_base" / "procedures.json"
    
    if not procedures_file.exists():
        logger.error(f"Procedures file not found: {procedures_file}")
        logger.info("Run create_procedures.py first")
        return
    
    await load_procedures_to_supabase(procedures_file)


if __name__ == "__main__":
    asyncio.run(main())

