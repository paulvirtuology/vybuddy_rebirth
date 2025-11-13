# VyBuddy Rebirth - Système Multi-Agents de Support IT

Système de support informatique de niveau 1 utilisant une architecture multi-agents avec plusieurs LLMs (OpenAI, Anthropic, Gemini).

## Architecture

- **Frontend**: Next.js avec WebSocket pour le chat en temps réel
- **Backend**: FastAPI avec orchestration multi-agents via LangGraph
- **Bases de données**: 
  - Supabase (logs & historique)
  - Redis Cloud (état des sessions)
  - Pinecone (RAG vectoriel)

## Agents Spécialisés

- **Router Agent**: Analyse l'intention et choisit le LLM approprié
- **Workspace Agent**: Support Google Workspace
- **MacOS Agent**: Diagnostic Mac
- **Knowledge Agent**: RAG interne pour les procédures
- **Network Agent**: Diagnostic WiFi/Réseau
- **Odoo Ticket Agent**: Création de tickets en cas d'échec

## Installation

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Configuration

Copiez `.env.example` vers `.env` et configurez vos clés API et connexions.

## Démarrage

### Backend

#### Option 1: Avec Docker (Recommandé)

```bash
cd backend
docker-compose up -d
```

#### Option 2: Sans Docker

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm run dev
```

## Documentation

Toute la documentation est disponible dans le dossier [`docs/`](docs/) :

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** : Architecture détaillée du système
- **[INSTALLATION.md](docs/INSTALLATION.md)** : Guide d'installation complet
- **[USAGE.md](docs/USAGE.md)** : Guide d'utilisation
- **[ADDING_AGENTS.md](docs/ADDING_AGENTS.md)** : Guide pour ajouter de nouveaux agents
- **[DOCKER.md](docs/DOCKER.md)** : Guide Docker pour le backend

