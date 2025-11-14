#!/usr/bin/env python3
"""
Script pour charger les données Jamf dans Supabase
"""
import asyncio
import sys
import os
import csv
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.supabase_client import SupabaseClient
import structlog

logger = structlog.get_logger()


async def load_jamf_data_to_supabase(csv_file: Path):
    """
    Charge les données Jamf depuis le CSV dans Supabase
    """
    supabase = SupabaseClient()
    client = supabase._get_client()
    
    # Lire le CSV
    devices = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            devices.append({
                "device_jss_id": int(row["Device JSS ID"]),
                "hostname": row["Hostname"],
                "serial": row["Serial"],
                "username": row["Username"],
                "is_admin": row["Is Admin"].upper() == "TRUE",
                "is_filevault_user": row["Is Filevault user"].upper() == "TRUE",
                "uid": int(row["UID"]) if row["UID"] else None,
                "home_directory": row["Home Directory"] if row["Home Directory"] else None
            })
    
    logger.info(f"Loading {len(devices)} Jamf device records to Supabase")
    
    # Supprimer les données existantes (pour un rechargement complet)
    try:
        client.table("jamf_devices").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        logger.info("Cleared existing Jamf data")
    except Exception as e:
        logger.warning(f"Could not clear existing data (might be empty): {e}")
    
    # Insérer par batch de 100
    batch_size = 100
    total_inserted = 0
    
    for i in range(0, len(devices), batch_size):
        batch = devices[i:i + batch_size]
        try:
            result = client.table("jamf_devices").upsert(
                batch,
                on_conflict="device_jss_id,serial,username"
            ).execute()
            
            total_inserted += len(batch)
            logger.info(f"Inserted batch {i//batch_size + 1} ({len(batch)} records)")
            
        except Exception as e:
            logger.error(f"Error inserting batch {i//batch_size + 1}: {e}")
    
    logger.info(f"Successfully loaded {total_inserted} Jamf device records to Supabase")


async def main():
    """Point d'entrée principal"""
    csv_file = Path(__file__).parent.parent / "knowledge_base" / "jamf_data.csv"
    
    if not csv_file.exists():
        logger.error(f"Jamf data CSV file not found: {csv_file}")
        return
    
    await load_jamf_data_to_supabase(csv_file)


if __name__ == "__main__":
    asyncio.run(main())

