"""
Service pour gérer les données Jamf
Vérifie si un MacBook est enrollé dans Jamf et récupère les informations
"""
import structlog
from typing import Dict, Any, Optional, List

from app.database.supabase_client import SupabaseClient

logger = structlog.get_logger()


class JamfService:
    """Service pour gérer les données Jamf"""
    
    def __init__(self):
        self.supabase = SupabaseClient()
    
    async def is_device_enrolled(self, serial_number: str) -> bool:
        """
        Vérifie si un MacBook est enrollé dans Jamf
        
        Args:
            serial_number: Numéro de série du MacBook
            
        Returns:
            True si le device est enrollé, False sinon
        """
        try:
            client = self.supabase._get_client()
            result = client.rpc(
                "is_device_jamf_enrolled",
                {"serial_number": serial_number}
            ).execute()
            
            return result.data if result.data else False
        except Exception as e:
            logger.error(f"Error checking Jamf enrollment for serial {serial_number}: {e}")
            return False
    
    async def get_device_info(self, serial_number: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations d'un device Jamf
        
        Args:
            serial_number: Numéro de série du MacBook
            
        Returns:
            Dictionnaire avec les informations du device ou None
        """
        try:
            client = self.supabase._get_client()
            result = client.rpc(
                "get_jamf_device_info",
                {"serial_number": serial_number}
            ).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting Jamf device info for serial {serial_number}: {e}")
            return None
    
    async def get_device_users(self, serial_number: str) -> List[Dict[str, Any]]:
        """
        Récupère la liste des utilisateurs d'un device Jamf
        
        Args:
            serial_number: Numéro de série du MacBook
            
        Returns:
            Liste des utilisateurs avec leurs informations
        """
        try:
            client = self.supabase._get_client()
            result = client.table("jamf_devices").select("*").eq("serial", serial_number).execute()
            
            users = []
            for row in result.data:
                users.append({
                    "username": row["username"],
                    "is_admin": row["is_admin"],
                    "is_filevault_user": row["is_filevault_user"],
                    "uid": row["uid"],
                    "home_directory": row["home_directory"]
                })
            
            return users
        except Exception as e:
            logger.error(f"Error getting device users for serial {serial_number}: {e}")
            return []
    
    async def find_device_by_hostname(self, hostname: str) -> Optional[Dict[str, Any]]:
        """
        Trouve un device par son hostname
        
        Args:
            hostname: Nom d'hôte du MacBook
            
        Returns:
            Dictionnaire avec les informations du device ou None
        """
        try:
            client = self.supabase._get_client()
            result = client.table("jamf_devices").select("*").eq("hostname", hostname).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                # Retourner les infos du premier device trouvé
                device = result.data[0]
                return {
                    "device_jss_id": device["device_jss_id"],
                    "hostname": device["hostname"],
                    "serial": device["serial"],
                    "is_enrolled": True
                }
            return None
        except Exception as e:
            logger.error(f"Error finding device by hostname {hostname}: {e}")
            return None

