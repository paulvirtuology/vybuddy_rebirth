"""
Configuration du logging structuré
"""
import logging
import sys
import structlog
from structlog.stdlib import LoggerFactory


def setup_logging(log_level: str = "INFO"):
    """Configure le logging structuré"""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configuration du logging standard
    log_level_upper = log_level.upper()
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level_upper),
    )
    
    # Réduire la verbosité des logs HTTP et WebSocket
    # Désactiver les logs HTTP de httpx (Supabase client)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Désactiver les logs HTTP de httpcore (utilisé par httpx)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Réduire les logs de uvicorn (garder seulement WARNING et ERROR)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)  # Garder les erreurs
    
    # Réduire les logs de fastapi
    logging.getLogger("fastapi").setLevel(logging.WARNING)

