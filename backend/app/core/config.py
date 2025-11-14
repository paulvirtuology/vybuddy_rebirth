"""
Configuration de l'application
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Paramètres de l'application"""
    
    # Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # API Keys
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str
    GOOGLE_API_KEY: str
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Redis Cloud
    REDIS_URL: str
    REDIS_PASSWORD: str = ""
    
    # Pinecone (nouveau SDK v3+)
    PINECONE_API_KEY: str
    PINECONE_ENVIRONMENT: str = ""  # Optionnel, non utilisé avec le nouveau SDK
    PINECONE_INDEX_NAME: str = "vybuddy-rag"
    
    # Odoo
    ODOO_URL: str
    ODOO_DATABASE: str
    ODOO_USERNAME: str
    ODOO_PASSWORD: str
    
    # Authentication
    NEXTAUTH_SECRET: str = ""
    SECRET_KEY: str = ""  # Fallback si NEXTAUTH_SECRET n'est pas défini
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

