#!/usr/bin/env python3
"""
Script pour charger la base de connaissances dans Pinecone
"""
import asyncio
import sys
import os
import unicodedata
import re
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.pinecone_client import PineconeClient
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
import structlog

logger = structlog.get_logger()


def normalize_id(text: str) -> str:
    """
    Normalise un texte pour créer un ID ASCII valide pour Pinecone
    Remplace les caractères accentués et les caractères spéciaux
    """
    # Normaliser les caractères Unicode (NFD = décomposition)
    text = unicodedata.normalize('NFD', text)
    # Supprimer les accents
    text = text.encode('ascii', 'ignore').decode('ascii')
    # Remplacer les espaces et caractères spéciaux par des underscores
    text = re.sub(r'[^a-zA-Z0-9_-]', '_', text)
    # Supprimer les underscores multiples
    text = re.sub(r'_+', '_', text)
    # Supprimer les underscores en début/fin
    text = text.strip('_')
    return text


async def load_knowledge_base():
    """Charge les fichiers markdown de la base de connaissances dans Pinecone
    
    Format uniforme: Tous les fichiers sont en Markdown (.md)
    Structure standardisée:
    - Titre principal (#)
    - Section Contexte (##)
    - Sections FAQ avec Q: et R: (##)
    - Sections procédures si nécessaire (##)
    """
    pinecone = PineconeClient()
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.OPENAI_API_KEY
    )
    
    # Chemin vers les fichiers de connaissances
    knowledge_dir = Path(__file__).parent.parent / "data" / "knowledge_base"
    
    if not knowledge_dir.exists():
        logger.error(f"Directory not found: {knowledge_dir}")
        return
    
    vectors_to_upsert = []
    
    # Traiter uniquement les fichiers Markdown (format uniforme)
    md_files = list(knowledge_dir.glob("*.md"))
    
    # Charger aussi les procédures si elles existent
    procedures_dir = knowledge_dir / "procedures"
    if procedures_dir.exists():
        logger.info("Found procedures directory, loading procedures...")
        md_files.extend(list(procedures_dir.glob("*.md")))
    # Exclure README.md
    md_files = [f for f in md_files if f.name != "README.md"]
    
    logger.info(f"Found {len(md_files)} markdown knowledge files")
    
    for md_file in md_files:
        logger.info(f"Processing: {md_file.name}")
        
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Diviser le contenu en sections pour créer des embeddings plus précis
        # Chaque section (##) devient un vecteur séparé
        sections = []
        current_section = ""
        current_title = ""
        
        for line in content.split('\n'):
            if line.startswith('## '):
                # Nouvelle section détectée
                if current_section.strip():
                    sections.append({
                        "title": current_title,
                        "content": current_section.strip()
                    })
                current_title = line.replace('## ', '').strip()
                current_section = line + '\n'
            elif line.startswith('### '):
                # Sous-section
                current_section += line + '\n'
            else:
                current_section += line + '\n'
        
        # Ajouter la dernière section
        if current_section.strip():
            sections.append({
                "title": current_title or md_file.stem,
                "content": current_section.strip()
            })
        
        # Si pas de sections détectées, traiter le document entier
        if not sections:
            sections = [{"title": md_file.stem, "content": content}]
        
        # Normaliser le nom de fichier pour l'ID
        normalized_stem = normalize_id(md_file.stem)
        
        # Créer un embedding pour le document complet
        doc_embedding = await embeddings.aembed_query(content)
        doc_vector = {
            "id": f"kb_doc_{normalized_stem}",
            "values": doc_embedding,
            "metadata": {
                "text": content,
                "source": md_file.name,
                "type": "knowledge_base",
                "format": "markdown",
                "section": "full_document"
            }
        }
        vectors_to_upsert.append(doc_vector)
        
        # Créer des embeddings pour chaque section (pour recherche plus précise)
        for idx, section in enumerate(sections):
            section_text = f"{section['title']}\n\n{section['content']}"
            section_embedding = await embeddings.aembed_query(section_text)
            
            # Normaliser le titre de section pour l'ID
            normalized_section_title = normalize_id(section['title'])
            
            section_vector = {
                "id": f"kb_section_{normalized_stem}_{idx}_{normalized_section_title[:30]}",
                "values": section_embedding,
                "metadata": {
                    "text": section_text,
                    "title": section['title'],
                    "source": md_file.name,
                    "type": "knowledge_base",
                    "format": "markdown",
                    "section": section['title'],
                    "section_index": idx
                }
            }
            vectors_to_upsert.append(section_vector)
    
    # Upsert dans Pinecone
    if vectors_to_upsert:
        try:
            index = pinecone._get_index()
            # Upsert par batch de 100 (limite Pinecone)
            batch_size = 100
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i + batch_size]
                index.upsert(vectors=batch)
                logger.info(f"Upserted batch {i//batch_size + 1} ({len(batch)} vectors)")
            
            logger.info(f"Successfully loaded {len(vectors_to_upsert)} documents into Pinecone")
        except Exception as e:
            logger.error(f"Error upserting to Pinecone: {e}")
            raise
    else:
        logger.warning("No documents to load")


if __name__ == "__main__":
    asyncio.run(load_knowledge_base())

