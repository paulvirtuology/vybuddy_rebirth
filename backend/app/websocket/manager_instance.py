"""
Instance globale du ConnectionManager
Permet de partager la même instance entre main.py et d'autres services (Slack bridge)
"""
from app.websocket.manager import ConnectionManager

manager = ConnectionManager()


