#!/usr/bin/env python3
"""
Script pour ajouter un utilisateur admin à la table admin_users
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


async def add_admin_user(email: str):
    """
    Ajoute un utilisateur admin à la table admin_users
    
    Args:
        email: Email de l'utilisateur (doit exister dans la table users)
    """
    supabase = SupabaseClient()
    client = supabase._get_client()
    
    try:
        # Vérifier si l'utilisateur existe dans la table users
        user_result = client.table("users").select("*").eq("email", email).execute()
        
        if not user_result.data or len(user_result.data) == 0:
            logger.error(f"User {email} does not exist in the users table. Please add the user first using add_user.py")
            return
        
        user_id = user_result.data[0]["id"]
        
        # Vérifier si l'utilisateur est déjà admin
        admin_result = client.table("admin_users").select("*").eq("email", email).execute()
        
        if admin_result.data and len(admin_result.data) > 0:
            logger.info(f"User {email} is already an admin")
            return
        
        # Ajouter l'utilisateur à la table admin_users
        client.table("admin_users").insert({
            "user_id": user_id,
            "email": email
        }).execute()
        
        logger.info(f"User {email} added as admin successfully")
        
    except Exception as e:
        logger.error(f"Error adding admin user {email}: {e}")
        raise


async def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ajouter un utilisateur admin")
    parser.add_argument("email", help="Email de l'utilisateur à ajouter comme admin")
    
    args = parser.parse_args()
    
    await add_admin_user(args.email)


if __name__ == "__main__":
    asyncio.run(main())

