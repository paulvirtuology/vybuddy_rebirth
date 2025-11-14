#!/usr/bin/env python3
"""
Script pour ajouter un utilisateur autorisé à la table users
"""
import asyncio
import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.supabase_client import SupabaseClient
import structlog

logger = structlog.get_logger()


async def add_user(email: str, name: str = None, role: str = "user"):
    """
    Ajoute un utilisateur à la table users
    
    Args:
        email: Email de l'utilisateur (obligatoire)
        name: Nom de l'utilisateur (optionnel)
        role: Rôle de l'utilisateur (défaut: "user")
    """
    supabase = SupabaseClient()
    client = supabase._get_client()
    
    try:
        # Vérifier si l'utilisateur existe déjà
        result = client.table("users").select("*").eq("email", email).execute()
        
        if result.data and len(result.data) > 0:
            logger.info(f"User {email} already exists, updating...")
            # Mettre à jour
            client.table("users").update({
                "name": name,
                "role": role,
                "is_active": True,
                "updated_at": "now()"
            }).eq("email", email).execute()
            logger.info(f"User {email} updated successfully")
        else:
            # Créer
            client.table("users").insert({
                "email": email,
                "name": name,
                "role": role,
                "is_active": True
            }).execute()
            logger.info(f"User {email} added successfully")
            
    except Exception as e:
        logger.error(f"Error adding user {email}: {e}")
        raise


async def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Add a user to the authorized users table")
    parser.add_argument("email", help="User email address")
    parser.add_argument("--name", help="User name", default=None)
    parser.add_argument("--role", help="User role (default: user)", default="user")
    
    args = parser.parse_args()
    
    await add_user(args.email, args.name, args.role)


if __name__ == "__main__":
    asyncio.run(main())

