#!/usr/bin/env python3
"""
Script principal pour exécuter tout le pipeline de création de base de connaissances procédurale
Exécute toutes les étapes dans l'ordre
"""
import asyncio
import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog

logger = structlog.get_logger()


async def run_pipeline():
    """
    Exécute le pipeline complet:
    1. Catégorisation des tickets
    2. Création des procédures
    3. Chargement dans Pinecone
    4. Chargement dans Supabase
    """
    logger.info("Starting full pipeline for procedural knowledge base creation")
    
    # Étape 1: Catégorisation
    logger.info("Step 1: Categorizing tickets...")
    from scripts.categorize_tickets import main as categorize_main
    await categorize_main()
    
    # Étape 2: Création des procédures
    logger.info("Step 2: Creating procedures...")
    from scripts.create_procedures import main as create_procedures_main
    await create_procedures_main()
    
    # Étape 3: Chargement dans Pinecone
    logger.info("Step 3: Loading procedures to Pinecone...")
    from scripts.load_knowledge_base import load_knowledge_base
    await load_knowledge_base()
    
    # Étape 4: Chargement dans Supabase
    logger.info("Step 4: Loading procedures to Supabase...")
    from scripts.load_procedures_to_supabase import main as load_supabase_main
    await load_supabase_main()
    
    logger.info("Pipeline completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_pipeline())

