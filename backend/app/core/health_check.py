"""
Vérification de santé des services au démarrage
"""
import structlog
from typing import Dict, Any, List
import asyncio

from app.core.config import settings
from app.database.redis_client import RedisClient
from app.database.supabase_client import SupabaseClient
from app.database.pinecone_client import PineconeClient

logger = structlog.get_logger()


class HealthChecker:
    """Vérifie la santé de tous les services au démarrage"""
    
    def __init__(self):
        self.redis_client = RedisClient()
        self.supabase_client = SupabaseClient()
        self.pinecone_client = PineconeClient()
        self.results: Dict[str, Dict[str, Any]] = {}
    
    async def check_redis(self) -> Dict[str, Any]:
        """Vérifie la connexion Redis"""
        try:
            await self.redis_client.connect()
            # Test d'écriture/lecture
            test_key = "health_check_test"
            await self.redis_client.set_session_data(
                session_id="health_check",
                key=test_key,
                value={"test": "ok"},
                ttl=10
            )
            result = await self.redis_client.get_session_data(
                session_id="health_check",
                key=test_key
            )
            
            if result and result.get("test") == "ok":
                await self.redis_client.disconnect()
                return {
                    "status": "ok",
                    "message": "Redis Cloud connecté et fonctionnel"
                }
            else:
                return {
                    "status": "error",
                    "message": "Redis: Échec du test de lecture/écriture"
                }
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return {
                "status": "error",
                "message": f"Redis: {str(e)}"
            }
    
    async def check_supabase(self) -> Dict[str, Any]:
        """Vérifie la connexion Supabase"""
        try:
            client = self.supabase_client._get_client()
            # Test simple de connexion
            # On essaie de faire une requête simple
            result = client.table("interactions").select("id").limit(1).execute()
            
            return {
                "status": "ok",
                "message": "Supabase connecté et fonctionnel"
            }
        except Exception as e:
            error_msg = str(e)
            # Si la table n'existe pas, c'est OK (première installation)
            if "relation" in error_msg.lower() or "does not exist" in error_msg.lower():
                return {
                    "status": "warning",
                    "message": "Supabase connecté mais les tables n'existent pas encore. Exécutez supabase_schema.sql"
                }
            logger.error("Supabase health check failed", error=error_msg)
            return {
                "status": "error",
                "message": f"Supabase: {error_msg}"
            }
    
    async def check_pinecone(self) -> Dict[str, Any]:
        """Vérifie la connexion Pinecone"""
        try:
            client = self.pinecone_client._get_client()
            # Vérifier que l'index existe
            index = self.pinecone_client._get_index()
            
            # Test simple: obtenir les stats de l'index
            stats = index.describe_index_stats()
            
            return {
                "status": "ok",
                "message": f"Pinecone connecté - Index '{settings.PINECONE_INDEX_NAME}' accessible",
                "stats": {
                    "total_vectors": stats.get("total_vector_count", 0),
                    "dimensions": stats.get("dimension", 0)
                }
            }
        except Exception as e:
            error_msg = str(e)
            logger.error("Pinecone health check failed", error=error_msg)
            return {
                "status": "error",
                "message": f"Pinecone: {error_msg}"
            }
    
    async def check_openai(self) -> Dict[str, Any]:
        """Vérifie la connexion OpenAI"""
        try:
            from langchain_openai import ChatOpenAI
            
            llm = ChatOpenAI(
                model="gpt-3.5-turbo",  # Modèle léger pour le test
                temperature=0,
                api_key=settings.OPENAI_API_KEY,
                max_tokens=10
            )
            
            response = await llm.ainvoke("Test")
            
            if response and response.content:
                return {
                    "status": "ok",
                    "message": "OpenAI API fonctionnelle"
                }
            else:
                return {
                    "status": "error",
                    "message": "OpenAI: Réponse vide"
                }
        except Exception as e:
            error_msg = str(e)
            logger.error("OpenAI health check failed", error=error_msg)
            return {
                "status": "error",
                "message": f"OpenAI: {error_msg}"
            }
    
    async def check_anthropic(self) -> Dict[str, Any]:
        """Vérifie la connexion Anthropic"""
        try:
            from langchain_anthropic import ChatAnthropic
            
            llm = ChatAnthropic(
                model="claude-3-haiku-20240307",  # Modèle léger pour le test
                temperature=0,
                api_key=settings.ANTHROPIC_API_KEY,
                max_tokens=10
            )
            
            response = await llm.ainvoke("Test")
            
            if response and response.content:
                return {
                    "status": "ok",
                    "message": "Anthropic API fonctionnelle"
                }
            else:
                return {
                    "status": "error",
                    "message": "Anthropic: Réponse vide"
                }
        except Exception as e:
            error_msg = str(e)
            logger.error("Anthropic health check failed", error=error_msg)
            return {
                "status": "error",
                "message": f"Anthropic: {error_msg}"
            }
    
    async def check_gemini(self) -> Dict[str, Any]:
        """Vérifie la connexion Google Gemini"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            # Utiliser gemini-2.5-flash pour le test (plus rapide et moins cher)
            # Selon https://ai.google.dev/gemini-api/docs/models?hl=fr
            model = genai.GenerativeModel(model_name="gemini-2.5-flash")
            
            # Utiliser un prompt plus sûr pour éviter les blocages de sécurité
            response = model.generate_content(
                "Bonjour, pouvez-vous me dire bonjour en retour ?",
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=10,
                    temperature=0.1
                )
            )
            
            # Vérifier le finish_reason
            if response.candidates:
                candidate = response.candidates[0]
                finish_reason = candidate.finish_reason
                
                # finish_reason 1 = STOP (normal)
                # finish_reason 2 = MAX_TOKENS (normal aussi, juste limité)
                # finish_reason 3 = SAFETY (bloqué par les filtres)
                # finish_reason 4 = RECITATION (contenu recité)
                
                if finish_reason == 1:  # STOP - succès
                    return {
                        "status": "ok",
                        "message": "Google Gemini API fonctionnelle"
                    }
                elif finish_reason == 2:  # MAX_TOKENS - OK mais limité
                    return {
                        "status": "ok",
                        "message": "Google Gemini API fonctionnelle (limite de tokens atteinte)"
                    }
                elif finish_reason == 3:  # SAFETY - bloqué mais API fonctionne
                    return {
                        "status": "warning",
                        "message": "Google Gemini API fonctionnelle mais réponse bloquée par les filtres de sécurité"
                    }
                elif finish_reason == 4:  # RECITATION
                    return {
                        "status": "warning",
                        "message": "Google Gemini API fonctionnelle mais contenu recité détecté"
                    }
                else:
                    # Essayer d'accéder au texte même si finish_reason n'est pas STOP
                    try:
                        if hasattr(response, 'text') and response.text:
                            return {
                                "status": "ok",
                                "message": "Google Gemini API fonctionnelle"
                            }
                    except:
                        pass
                    
                    return {
                        "status": "warning",
                        "message": f"Google Gemini API répond mais finish_reason={finish_reason}"
                    }
            else:
                return {
                    "status": "error",
                    "message": "Gemini: Aucune candidate dans la réponse"
                }
                
        except Exception as e:
            error_msg = str(e)
            logger.error("Gemini health check failed", error=error_msg)
            
            # Si c'est juste un problème de réponse bloquée, c'est un warning
            if "finish_reason" in error_msg.lower() or "part" in error_msg.lower():
                return {
                    "status": "warning",
                    "message": "Google Gemini API accessible mais réponse bloquée par les filtres de sécurité"
                }
            
            return {
                "status": "error",
                "message": f"Gemini: {error_msg}"
            }
    
    async def check_odoo(self) -> Dict[str, Any]:
        """Vérifie la connexion Odoo"""
        try:
            import xmlrpc.client
            
            # Test de connexion via XML-RPC
            common = xmlrpc.client.ServerProxy(f"{settings.ODOO_URL}/xmlrpc/2/common")
            uid = common.authenticate(
                settings.ODOO_DATABASE,
                settings.ODOO_USERNAME,
                settings.ODOO_PASSWORD,
                {}
            )
            
            if not uid:
                return {
                    "status": "error",
                    "message": "Odoo: Authentification échouée (vérifiez les identifiants)"
                }
            
            # Vérifier que le module Helpdesk est disponible
            models = xmlrpc.client.ServerProxy(f"{settings.ODOO_URL}/xmlrpc/2/object")
            try:
                # Vérifier si le modèle helpdesk.ticket existe
                helpdesk_available = models.execute_kw(
                    settings.ODOO_DATABASE,
                    uid,
                    settings.ODOO_PASSWORD,
                    "helpdesk.ticket",
                    "search_count",
                    [[]]
                )
                
                return {
                    "status": "ok",
                    "message": f"Odoo connecté - Module Helpdesk disponible",
                    "uid": uid
                }
            except Exception as e:
                # Si helpdesk.ticket n'existe pas, c'est un warning
                if "does not exist" in str(e).lower() or "model" in str(e).lower():
                    return {
                        "status": "warning",
                        "message": "Odoo connecté mais le module Helpdesk n'est pas installé"
                    }
                raise
            
        except Exception as e:
            error_msg = str(e)
            logger.error("Odoo health check failed", error=error_msg)
            
            # Messages d'erreur plus explicites
            if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                return {
                    "status": "error",
                    "message": f"Odoo: Impossible de se connecter à {settings.ODOO_URL}"
                }
            elif "authentication" in error_msg.lower() or "invalid" in error_msg.lower():
                return {
                    "status": "error",
                    "message": "Odoo: Erreur d'authentification (vérifiez les identifiants)"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Odoo: {error_msg}"
                }
    
    async def check_all(self) -> Dict[str, Any]:
        """Vérifie tous les services"""
        logger.info("Starting health checks...")
        
        checks = [
            ("Redis", self.check_redis()),
            ("Supabase", self.check_supabase()),
            ("Pinecone", self.check_pinecone()),
            ("OpenAI", self.check_openai()),
            ("Anthropic", self.check_anthropic()),
            ("Gemini", self.check_gemini()),
            ("Odoo", self.check_odoo()),
        ]
        
        results = {}
        for name, check_coro in checks:
            try:
                result = await check_coro
                results[name] = result
                self.results[name] = result
            except Exception as e:
                logger.error(f"Health check error for {name}", error=str(e))
                results[name] = {
                    "status": "error",
                    "message": f"Exception: {str(e)}"
                }
                self.results[name] = results[name]
        
        return results
    
    def print_results(self, results: Dict[str, Any] = None):
        """Affiche les résultats de manière formatée"""
        if results is None:
            results = self.results
        
        print("\n" + "="*60)
        print("  VÉRIFICATION DE SANTÉ DES SERVICES")
        print("="*60 + "\n")
        
        status_icons = {
            "ok": "✅",
            "warning": "⚠️",
            "error": "❌"
        }
        
        for service_name, result in results.items():
            status = result.get("status", "unknown")
            icon = status_icons.get(status, "❓")
            message = result.get("message", "Pas de message")
            
            print(f"{icon} {service_name:12} : {message}")
            
            # Afficher les stats supplémentaires si disponibles
            if "stats" in result:
                stats = result["stats"]
                for key, value in stats.items():
                    print(f"   └─ {key}: {value}")
        
        print("\n" + "="*60)
        
        # Résumé
        ok_count = sum(1 for r in results.values() if r.get("status") == "ok")
        warning_count = sum(1 for r in results.values() if r.get("status") == "warning")
        error_count = sum(1 for r in results.values() if r.get("status") == "error")
        total = len(results)
        
        print(f"Résumé: {ok_count}/{total} OK, {warning_count} avertissements, {error_count} erreurs")
        print("="*60 + "\n")
        
        # Avertissement si des erreurs critiques
        if error_count > 0:
            print("⚠️  ATTENTION: Certains services ne sont pas disponibles!")
            print("   L'application peut ne pas fonctionner correctement.\n")
        
        return error_count == 0

