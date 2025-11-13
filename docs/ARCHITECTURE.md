# Architecture - VyBuddy Rebirth

## Vue d'ensemble

VyBuddy Rebirth est un système multi-agents de support informatique utilisant plusieurs LLMs (OpenAI, Anthropic, Gemini) pour résoudre automatiquement les problèmes de niveau 1.

## Architecture du Système

```
┌─────────────────┐
│  Next.js        │
│  Frontend       │
│  (WebSocket)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI        │
│  Gateway        │
│  (Orchestrateur)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Router Agent   │
│  (Analyse       │
│   intention)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LangGraph      │
│  Swarm          │
│  (Orchestration)│
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼
┌────────┐ ┌──────┐ ┌─────────┐ ┌──────────┐
│Network │ │MacOS │ │Workspace│ │Knowledge │
│ Agent  │ │Agent │ │ Agent   │ │  Agent   │
└───┬────┘ └──┬───┘ └────┬────┘ └────┬─────┘
    │         │          │           │
    └─────────┴──────────┴───────────┘
                    │
                    ▼
            ┌──────────────┐
            │ Ticket Agent │
            │   (Odoo)     │
            └──────────────┘
```

## Composants Principaux

### 1. Frontend (Next.js)

- **Interface Chat**: Interface utilisateur pour interagir avec le système
- **WebSocket Client**: Connexion temps réel avec le backend
- **Gestion d'état**: Gestion des messages et de l'état de connexion

### 2. Backend (FastAPI)

#### Gateway (main.py)
- Point d'entrée de l'API
- Gestion des WebSockets
- Routes REST pour les interactions

#### Router Agent
- Analyse l'intention de l'utilisateur
- Sélectionne le LLM approprié (OpenAI, Anthropic, Gemini)
- Route vers l'agent spécialisé

#### LangGraph Swarm
- Orchestration multi-agents
- Gestion du flux de traitement
- Coordination entre les agents

### 3. Agents Spécialisés

#### Network Agent
- **Spécialité**: Problèmes WiFi et réseau
- **LLM préféré**: Anthropic (raisonnement diagnostique)
- **Exemple**: Diagnostic de connexion WiFi

#### MacOS Agent
- **Spécialité**: Problèmes macOS/MacBook
- **LLM préféré**: OpenAI (connaissance technique)
- **Exemple**: Problèmes Finder, Safari, système

#### Workspace Agent
- **Spécialité**: Google Workspace
- **LLM préféré**: Gemini (intégration Google native)
- **Exemple**: Problèmes Gmail, Drive, Calendar

#### Knowledge Agent
- **Spécialité**: Recherche de procédures et documentation
- **LLM préféré**: Anthropic (RAG)
- **Base de données**: Pinecone (recherche vectorielle)

#### Odoo Ticket Agent
- **Spécialité**: Création de tickets
- **Déclenchement**: Lorsqu'un diagnostic échoue
- **Intégration**: API XML-RPC Odoo

### 4. Bases de Données

#### Redis Cloud
- **Usage**: État des sessions
- **Données**: Historique de conversation (temporaire)
- **TTL**: 7 jours

#### Supabase
- **Usage**: Logs et historique permanent
- **Tables**:
  - `interactions`: Toutes les interactions utilisateur-bot
  - `tickets`: Tickets créés dans Odoo

#### Pinecone
- **Usage**: Recherche vectorielle (RAG)
- **Embeddings**: OpenAI text-embedding-3-small
- **Index**: `vybuddy-rag`

## Flux de Traitement

1. **Réception**: L'utilisateur envoie un message via WebSocket
2. **Routage**: Le Router Agent analyse l'intention
3. **Sélection**: Choix du LLM et de l'agent approprié
4. **Traitement**: L'agent spécialisé traite la demande
5. **Réponse**: Le bot répond avec des questions ou solutions
6. **Escalade**: Si le problème persiste, création d'un ticket Odoo
7. **Logging**: Toutes les interactions sont enregistrées

## Stratégie Multi-LLM

### OpenAI (GPT-5)
- **Forces**: Connaissance technique, génération de code
- **Usage**: MacOS Agent, Router Agent

### Anthropic (Claude Sonnet 4.5)
- **Modèle**: claude-sonnet-4-5 (alias) ou claude-sonnet-4-5-20250929 (ID complet)
- **Forces**: Raisonnement, diagnostic, RAG, agents complexes
- **Usage**: Network Agent, Knowledge Agent

### Gemini (Pro 2.5)
- **Forces**: Intégration Google, multimodal
- **Usage**: Workspace Agent

## Sécurité

- Variables d'environnement pour les clés API
- CORS configuré pour le frontend
- Validation des entrées utilisateur
- Logging structuré pour l'audit

## Scalabilité

- Architecture modulaire et extensible
- Agents indépendants et réutilisables
- Bases de données cloud (Redis Cloud, Supabase)
- WebSocket pour les communications temps réel

## Améliorations Futures

- Authentification utilisateur
- Dashboard d'administration
- Analytics et métriques
- Amélioration du RAG avec plus de documents
- Support de plus d'agents spécialisés
- Intégration avec d'autres outils (Monday, etc.)

