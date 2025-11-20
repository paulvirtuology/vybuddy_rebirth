#!/usr/bin/env python3
"""
Script de migration pour transférer les fichiers de la base de connaissances
du filesystem local vers Supabase Storage
"""
import asyncio
import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.knowledge_base_storage import KnowledgeBaseStorage
import structlog

logger = structlog.get_logger()


async def migrate_knowledge_base():
    """
    Migre tous les fichiers de la base de connaissances du filesystem vers Supabase Storage
    """
    storage = KnowledgeBaseStorage()
    
    # Chemin vers les fichiers de connaissances locaux
    knowledge_dir = Path(__file__).parent.parent / "data" / "knowledge_base"
    
    if not knowledge_dir.exists():
        logger.error(f"Directory not found: {knowledge_dir}")
        logger.info("Nothing to migrate - directory does not exist")
        return
    
    files_migrated = 0
    files_skipped = 0
    errors = []
    
    # Traiter les fichiers .md dans le répertoire principal
    md_files = list(knowledge_dir.glob("*.md"))
    
    # Charger aussi les procédures si elles existent
    procedures_dir = knowledge_dir / "procedures"
    if procedures_dir.exists():
        logger.info("Found procedures directory, migrating procedures...")
        md_files.extend(list(procedures_dir.glob("*.md")))
    
    # Exclure README.md
    md_files = [f for f in md_files if f.name != "README.md"]
    
    logger.info(f"Found {len(md_files)} markdown files to migrate")
    
    for md_file in md_files:
        try:
            # Déterminer le chemin relatif pour Supabase Storage
            if md_file.parent.name == "procedures":
                storage_path = f"procedures/{md_file.name}"
            else:
                storage_path = md_file.name
            
            # Vérifier si le fichier existe déjà dans Storage
            if await storage.file_exists(storage_path):
                logger.info(f"File already exists in storage, skipping: {storage_path}")
                files_skipped += 1
                continue
            
            # Lire le contenu du fichier local
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Sauvegarder dans Supabase Storage
            result = await storage.save_file(storage_path, content)
            
            if result:
                logger.info(f"Migrated: {storage_path}")
                files_migrated += 1
            else:
                logger.error(f"Failed to migrate: {storage_path}")
                errors.append(storage_path)
                
        except Exception as e:
            logger.error(f"Error migrating {md_file.name}", error=str(e))
            errors.append(str(md_file))
    
    # Résumé
    logger.info("=" * 60)
    logger.info("Migration Summary:")
    logger.info(f"  Files migrated: {files_migrated}")
    logger.info(f"  Files skipped (already exist): {files_skipped}")
    logger.info(f"  Errors: {len(errors)}")
    
    if errors:
        logger.warning("Files with errors:")
        for error in errors:
            logger.warning(f"  - {error}")
    
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(migrate_knowledge_base())

