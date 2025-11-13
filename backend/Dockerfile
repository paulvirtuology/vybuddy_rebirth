# ============================================
# Dockerfile pour VyBuddy Rebirth Backend
# ============================================

# Stage 1: Builder
FROM python:3.11-slim AS builder

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copier le fichier de dépendances
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Créer un utilisateur non-root pour la sécurité
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copier les dépendances installées depuis le builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copier le code de l'application
COPY . .

# Changer le propriétaire des fichiers
RUN chown -R appuser:appuser /app

# Passer à l'utilisateur non-root
USER appuser

# Exposer le port
EXPOSE 8000

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    LOG_LEVEL=INFO

# Healthcheck
#HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Commande de démarrage
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

