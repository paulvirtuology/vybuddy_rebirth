"""
Client Pinecone pour la recherche vectorielle (RAG)
Utilise le nouveau SDK Pinecone (v3+) - anciennement pinecone-client
"""
from pinecone import Pinecone
import structlog
from typing import List, Dict, Any

from app.core.config import settings

logger = structlog.get_logger()


class PineconeClient:
    """Client Pinecone pour la recherche vectorielle"""
    
    def __init__(self):
        self.api_key = settings.PINECONE_API_KEY
        self.index_name = settings.PINECONE_INDEX_NAME
        # Note: PINECONE_ENVIRONMENT n'est plus nécessaire avec le nouveau SDK
        self.pc: Pinecone = None
        self.index = None
    
    def _get_client(self) -> Pinecone:
        """Retourne le client Pinecone (singleton)"""
        if not self.pc:
            self.pc = Pinecone(api_key=self.api_key)
        return self.pc
    
    def _get_index(self):
        """Retourne l'index Pinecone"""
        if not self.index:
            pc = self._get_client()
            self.index = pc.Index(self.index_name)
        return self.index
    
    async def search(
        self,
        query: str,
        top_k: int = 3,
        namespace: str = None
    ) -> List[Dict[str, Any]]:
        """
        Recherche vectorielle dans Pinecone
        
        Args:
            query: Requête de recherche
            top_k: Nombre de résultats à retourner
            namespace: Namespace Pinecone (optionnel)
            
        Returns:
            Liste des documents pertinents
        """
        try:
            # Pour la recherche vectorielle, on aurait besoin d'un modèle d'embedding
            # Ici, on simule une recherche basique
            # En production, utiliser un modèle comme OpenAI embeddings ou sentence-transformers
            
            from langchain_openai import OpenAIEmbeddings
            
            embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=settings.OPENAI_API_KEY
            )
            
            # Génération de l'embedding de la requête
            query_embedding = await embeddings.aembed_query(query)
            
            # Recherche dans Pinecone
            index = self._get_index()
            results = index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                namespace=namespace
            )
            
            # Formatage des résultats
            documents = []
            for match in results.matches:
                documents.append({
                    "id": match.id,
                    "score": match.score,
                    "text": match.metadata.get("text", ""),
                    "metadata": match.metadata
                })
            
            logger.info(
                "Pinecone search completed",
                query_preview=query[:50],
                results_count=len(documents)
            )
            
            return documents
            
        except Exception as e:
            logger.error(
                "Pinecone search error",
                error=str(e),
                exc_info=True
            )
            return []
    
    async def upsert(
        self,
        documents: List[Dict[str, Any]],
        namespace: str = None
    ):
        """
        Ajoute ou met à jour des documents dans Pinecone
        
        Args:
            documents: Liste de documents avec id, text, metadata
            namespace: Namespace Pinecone (optionnel)
        """
        try:
            from langchain_openai import OpenAIEmbeddings
            
            embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=settings.OPENAI_API_KEY
            )
            
            # Génération des embeddings
            texts = [doc["text"] for doc in documents]
            vectors = await embeddings.aembed_documents(texts)
            
            # Préparation des vecteurs pour Pinecone
            vectors_to_upsert = []
            for i, doc in enumerate(documents):
                vectors_to_upsert.append({
                    "id": doc["id"],
                    "values": vectors[i],
                    "metadata": {
                        "text": doc["text"],
                        **doc.get("metadata", {})
                    }
                })
            
            # Upsert dans Pinecone
            index = self._get_index()
            index.upsert(
                vectors=vectors_to_upsert,
                namespace=namespace
            )
            
            logger.info(
                "Documents upserted to Pinecone",
                count=len(documents)
            )
            
        except Exception as e:
            logger.error(
                "Pinecone upsert error",
                error=str(e),
                exc_info=True
            )

