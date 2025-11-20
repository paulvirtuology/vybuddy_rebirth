"""
Service pour gérer les fichiers de la base de connaissances dans Supabase Storage
"""
import structlog
import re
import unicodedata
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from supabase import create_client, Client

from app.core.config import settings

logger = structlog.get_logger()

# Nom du bucket Supabase Storage pour la base de connaissances
KNOWLEDGE_BASE_BUCKET = "knowledge-base"


class KnowledgeBaseStorage:
    """Service pour gérer les fichiers de la base de connaissances dans Supabase Storage"""
    
    def __init__(self):
        self.bucket = KNOWLEDGE_BASE_BUCKET
        # Utiliser le service role key si disponible pour bypass RLS, sinon utiliser la clé normale
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
        self.supabase_client: Optional[Client] = None
        
        # Avertir si on n'utilise pas le service role key (peut causer des erreurs RLS)
        if not settings.SUPABASE_SERVICE_ROLE_KEY:
            logger.warning(
                "SUPABASE_SERVICE_ROLE_KEY not set. Using SUPABASE_KEY which may be restricted by RLS policies. "
                "For admin operations (knowledge base management), set SUPABASE_SERVICE_ROLE_KEY in your .env file."
            )
    
    def _get_storage_client(self):
        """Retourne le client Supabase Storage avec le service role key pour bypass RLS"""
        if not self.supabase_client:
            self.supabase_client = create_client(settings.SUPABASE_URL, self.service_key)
        return self.supabase_client.storage
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Nettoie le nom de fichier pour être compatible avec Supabase Storage
        - Remplace les caractères spéciaux par des underscores
        - Normalise les caractères Unicode (enlève les accents)
        - Limite la longueur
        """
        # Normaliser les caractères Unicode (NFD = décomposition)
        filename = unicodedata.normalize('NFD', filename)
        # Supprimer les accents
        filename = filename.encode('ascii', 'ignore').decode('ascii')
        # Remplacer les caractères non alphanumériques (sauf . - _ /) par des underscores
        filename = re.sub(r'[^a-zA-Z0-9._/-]', '_', filename)
        # Supprimer les underscores multiples
        filename = re.sub(r'_+', '_', filename)
        # Supprimer les underscores en début/fin
        filename = filename.strip('_')
        return filename
    
    def _normalize_path(self, file_path: str) -> str:
        """
        Normalise le chemin du fichier pour Supabase Storage
        - Enlève les slashes en début/fin
        - Remplace les backslashes par des slashes
        - Nettoie les noms de fichiers pour être compatible avec Supabase Storage
        """
        # Enlever les slashes en début/fin
        path = file_path.strip("/")
        # Remplacer les backslashes par des slashes
        path = path.replace("\\", "/")
        
        # Si le chemin contient un dossier (ex: procedures/file.md)
        if "/" in path:
            parts = path.split("/")
            # Nettoyer chaque partie du chemin
            cleaned_parts = []
            for part in parts:
                if part.endswith(".md"):
                    # C'est le nom de fichier, le nettoyer
                    name, ext = part.rsplit(".md", 1)
                    cleaned_name = self._sanitize_filename(name) + ".md"
                    cleaned_parts.append(cleaned_name)
                else:
                    # C'est un dossier, le nettoyer aussi
                    cleaned_parts.append(self._sanitize_filename(part))
            path = "/".join(cleaned_parts)
        else:
            # C'est juste un fichier à la racine
            if path.endswith(".md"):
                name, ext = path.rsplit(".md", 1)
                path = self._sanitize_filename(name) + ".md"
            else:
                path = self._sanitize_filename(path)
        
        return path
    
    async def list_files(self) -> List[Dict[str, Any]]:
        """
        Liste tous les fichiers de la base de connaissances
        
        Returns:
            Liste des fichiers avec leurs métadonnées
        """
        try:
            storage = self._get_storage_client()
            files = []
            
            # Lister les fichiers à la racine
            try:
                root_files = storage.from_(self.bucket).list("")
                for item in root_files:
                    name = item.get("name", "")
                    # Vérifier si c'est un fichier .md (pas un dossier)
                    if name.endswith(".md") and name != "README.md":
                        files.append({
                            "path": name,
                            "name": name,
                            "type": "file",
                            "size": item.get("metadata", {}).get("size", 0) if item.get("metadata") else 0,
                            "modified": item.get("updated_at", datetime.utcnow().isoformat())
                        })
            except Exception as e:
                logger.warning("Error listing root files", error=str(e))
            
            # Lister les fichiers dans le dossier procedures
            try:
                procedures_files = storage.from_(self.bucket).list("procedures")
                for item in procedures_files:
                    name = item.get("name", "")
                    if name.endswith(".md"):
                        files.append({
                            "path": f"procedures/{name}",
                            "name": name,
                            "type": "file",
                            "category": "procedures",
                            "size": item.get("metadata", {}).get("size", 0) if item.get("metadata") else 0,
                            "modified": item.get("updated_at", datetime.utcnow().isoformat())
                        })
            except Exception as e:
                # Le dossier procedures n'existe peut-être pas encore, ce n'est pas une erreur
                logger.debug("Procedures directory not found or empty", error=str(e))
            
            # Trier par chemin
            files.sort(key=lambda x: x["path"])
            
            return files
            
        except Exception as e:
            logger.error("Error listing knowledge base files from storage", error=str(e))
            return []
    
    async def get_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le contenu d'un fichier
        
        Args:
            file_path: Chemin du fichier (ex: "file.md" ou "procedures/file.md")
            
        Returns:
            Dictionnaire avec path, name, content, size, modified ou None si non trouvé
        """
        try:
            # Normaliser le chemin
            normalized_path = self._normalize_path(file_path)
            
            # Sécuriser le chemin
            if ".." in normalized_path or normalized_path.startswith("/"):
                raise ValueError("Invalid file path")
            
            # Vérifier que c'est un fichier .md
            if not normalized_path.endswith(".md"):
                raise ValueError("Only .md files are allowed")
            
            storage = self._get_storage_client()
            
            # Télécharger le fichier
            file_content = storage.from_(self.bucket).download(normalized_path)
            
            # Décoder le contenu (bytes -> string)
            content = file_content.decode('utf-8')
            
            # Récupérer les métadonnées
            file_metadata = None
            file_name = normalized_path.split("/")[-1]
            
            try:
                folder = normalized_path.rsplit("/", 1)[0] if "/" in normalized_path else ""
                file_info = storage.from_(self.bucket).list(folder)
                
                for item in file_info:
                    if item.get("name") == file_name:
                        file_metadata = item
                        break
            except Exception as e:
                logger.debug("Could not get file metadata", error=str(e))
            
            return {
                "path": normalized_path,  # Retourner le path normalisé (celui utilisé dans Storage)
                "name": file_name,
                "content": content,
                "size": len(content.encode('utf-8')),
                "modified": file_metadata.get("updated_at", datetime.utcnow().isoformat()) if file_metadata else datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Error getting knowledge base file from storage", error=str(e), file_path=file_path)
            return None
    
    async def save_file(self, file_path: str, content: str) -> Optional[Dict[str, Any]]:
        """
        Crée ou met à jour un fichier
        
        Args:
            file_path: Chemin du fichier (ex: "file.md" ou "procedures/file.md")
            content: Contenu du fichier
            
        Returns:
            Dictionnaire avec path, name, size, modified ou None en cas d'erreur
        """
        try:
            # Normaliser le chemin
            normalized_path = self._normalize_path(file_path)
            
            # Sécuriser le chemin
            if ".." in normalized_path or normalized_path.startswith("/"):
                raise ValueError("Invalid file path")
            
            # Vérifier que c'est un fichier .md
            if not normalized_path.endswith(".md"):
                raise ValueError("Only .md files are allowed")
            
            storage = self._get_storage_client()
            
            # Convertir le contenu en bytes
            content_bytes = content.encode('utf-8')
            
            # Déterminer le dossier et le nom du fichier
            if "/" in normalized_path:
                folder = "/".join(normalized_path.split("/")[:-1])
                file_name = normalized_path.split("/")[-1]
            else:
                folder = ""
                file_name = normalized_path
            
            # Upload le fichier
            # Si le fichier est dans un sous-dossier, on doit spécifier le chemin complet
            logger.debug("Uploading file to storage", bucket=self.bucket, path=normalized_path, size=len(content_bytes))
            try:
                result = storage.from_(self.bucket).upload(
                    normalized_path,
                    content_bytes,
                    file_options={"content-type": "text/markdown", "upsert": "true"}
                )
                logger.debug("Upload successful", path=normalized_path)
            except Exception as upload_error:
                error_msg = str(upload_error)
                error_dict = {}
                # Essayer de parser l'erreur si c'est un dict
                if isinstance(upload_error, dict):
                    error_dict = upload_error
                elif hasattr(upload_error, 'message'):
                    error_msg = upload_error.message
                elif hasattr(upload_error, 'args') and upload_error.args:
                    error_msg = str(upload_error.args[0])
                
                logger.error(
                    "Upload failed to Supabase Storage",
                    error=error_msg,
                    error_dict=error_dict,
                    error_type=type(upload_error).__name__,
                    bucket=self.bucket,
                    path=normalized_path,
                    normalized_path=normalized_path,
                    exc_info=True
                )
                
                # Messages d'erreur plus clairs selon le type d'erreur
                if "bucket" in error_msg.lower() or "not found" in error_msg.lower():
                    raise ValueError(f"Bucket '{self.bucket}' does not exist or is not accessible. Please create it in Supabase dashboard and ensure RLS policies allow access.")
                elif "permission" in error_msg.lower() or "unauthorized" in error_msg.lower() or "403" in error_msg:
                    raise ValueError(f"Permission denied. Ensure SUPABASE_SERVICE_ROLE_KEY is set correctly and the bucket '{self.bucket}' has proper RLS policies.")
                else:
                    raise
            
            logger.info("Knowledge base file saved to storage", file_path=normalized_path, bucket=self.bucket)
            
            return {
                "path": normalized_path,  # Retourner le path normalisé (celui utilisé dans Storage)
                "name": file_name,
                "size": len(content_bytes),
                "modified": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Error saving knowledge base file to storage", error=str(e), file_path=file_path)
            return None
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Supprime un fichier
        
        Args:
            file_path: Chemin du fichier
            
        Returns:
            True si succès, False sinon
        """
        try:
            # Normaliser le chemin
            normalized_path = self._normalize_path(file_path)
            
            # Sécuriser le chemin
            if ".." in normalized_path or normalized_path.startswith("/"):
                raise ValueError("Invalid file path")
            
            # Ne pas permettre la suppression de README.md
            if normalized_path.endswith("README.md") or normalized_path == "README.md":
                raise ValueError("Cannot delete README.md")
            
            # Vérifier que c'est un fichier .md
            if not normalized_path.endswith(".md"):
                raise ValueError("Only .md files are allowed")
            
            storage = self._get_storage_client()
            
            # Supprimer le fichier
            storage.from_(self.bucket).remove([normalized_path])
            
            logger.info("Knowledge base file deleted from storage", file_path=normalized_path)
            
            return True
            
        except Exception as e:
            logger.error("Error deleting knowledge base file from storage", error=str(e), file_path=file_path)
            return False
    
    async def file_exists(self, file_path: str) -> bool:
        """
        Vérifie si un fichier existe
        
        Args:
            file_path: Chemin du fichier
            
        Returns:
            True si le fichier existe, False sinon
        """
        try:
            normalized_path = self._normalize_path(file_path)
            storage = self._get_storage_client()
            
            # Lister les fichiers dans le dossier parent
            folder = "/".join(normalized_path.rsplit("/", 1)[:-1]) if "/" in normalized_path else ""
            file_name = normalized_path.split("/")[-1]
            
            files = storage.from_(self.bucket).list(folder)
            
            for item in files:
                if item.get("name") == file_name:
                    return True
            
            return False
            
        except Exception as e:
            logger.error("Error checking if file exists", error=str(e), file_path=file_path)
            return False

