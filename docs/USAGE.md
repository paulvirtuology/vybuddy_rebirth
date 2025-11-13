# Guide d'Utilisation - VyBuddy Rebirth

## Démarrage Rapide

### 1. Démarrer le Backend

```bash
cd backend
source venv/bin/activate  # ou venv\Scripts\activate sur Windows
uvicorn main:app --reload --port 8000
```

Le backend sera accessible sur `http://localhost:8000`

### 2. Démarrer le Frontend

```bash
cd frontend
npm run dev
```

Le frontend sera accessible sur `http://localhost:3000`

## Utilisation

### Interface Chat

1. Ouvrez `http://localhost:3000` dans votre navigateur
2. Une session est automatiquement créée
3. Tapez votre message dans le champ de saisie
4. Le bot répondra en temps réel via WebSocket

### Exemples de Requêtes

#### Problème WiFi
```
Utilisateur: Je n'arrive pas à me connecter au wifi du bureau
Bot: D'accord. Et actuellement vous êtes connectés sur quel réseau?
Utilisateur: J'utilise mon téléphone comme point d'accès
Bot: Quand vous cliquez sur l'icône wifi en haut à gauche, est-ce que vous voyez le wifi du bureau sur la liste?
...
```

#### Problème MacOS
```
Utilisateur: Mon Finder ne répond plus
Bot: Essayons de redémarrer Finder. Appuyez sur Cmd+Option+Esc, sélectionnez Finder et cliquez sur "Forcer à quitter"...
```

#### Problème Google Workspace
```
Utilisateur: Je n'arrive pas à partager un fichier sur Google Drive
Bot: Vérifions les paramètres de partage. Pouvez-vous me dire quel type d'erreur vous voyez?
```

#### Recherche de Procédure
```
Utilisateur: Comment configurer un nouveau MacBook?
Bot: [Réponse basée sur la documentation dans Pinecone]
```

## API REST (Alternative au WebSocket)

### Envoyer un Message

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Je n'arrive pas à me connecter au wifi",
    "session_id": "session-123",
    "user_id": "user-1"
  }'
```

### Récupérer l'Historique

```bash
curl http://localhost:8000/api/v1/history/session-123?limit=50
```

## Configuration Pinecone (RAG)

Pour que le Knowledge Agent fonctionne, vous devez:

1. Créer un index Pinecone avec:
   - Nom: `vybuddy-rag` (ou celui configuré)
   - Dimensions: 1536
   - Métrique: cosine

2. Ajouter des documents (procédures, guides, etc.):

```python
from app.database.pinecone_client import PineconeClient

client = PineconeClient()
await client.upsert([
    {
        "id": "doc-1",
        "text": "Guide de configuration WiFi MacBook...",
        "metadata": {"type": "procedure", "category": "network"}
    }
])
```

## Configuration Odoo

### Prérequis

1. Module Helpdesk installé
2. Équipe Helpdesk créée
3. API XML-RPC activée
4. Identifiants configurés dans `.env`

### Test de Connexion

Le système créera automatiquement un ticket si:
- Un diagnostic échoue après plusieurs tentatives
- L'agent détecte qu'un ticket est nécessaire
- L'utilisateur demande explicitement un ticket

## Monitoring

### Logs Backend

Les logs sont structurés avec `structlog`. Vous verrez:
- Connexions WebSocket
- Décisions de routage
- Réponses des agents
- Créations de tickets
- Erreurs éventuelles

### Supabase

Consultez les tables `interactions` et `tickets` pour:
- Historique complet des conversations
- Statistiques d'utilisation des agents
- Tickets créés

### Redis

L'historique des sessions est stocké temporairement (7 jours) dans Redis pour:
- Contexte de conversation
- État de session
- Cache des réponses fréquentes

## Dépannage

### Le bot ne répond pas
- Vérifiez que le backend est démarré
- Vérifiez la connexion WebSocket dans la console du navigateur
- Vérifiez les logs backend

### Erreur "Agent not found"
- Vérifiez que tous les agents sont correctement importés
- Vérifiez les clés API dans `.env`

### Tickets non créés
- Vérifiez la configuration Odoo
- Vérifiez les logs pour les erreurs d'authentification
- Vérifiez que le module Helpdesk est installé

## Personnalisation

### Ajouter un Nouvel Agent

1. Créez un nouveau fichier dans `app/agents/`
2. Héritez de `BaseAgent`
3. Implémentez la méthode `process()`
4. Ajoutez l'agent dans `LangGraphSwarm`
5. Mettez à jour le `RouterAgent` pour le reconnaître

### Modifier le Routage

Éditez `app/services/router_agent.py` pour:
- Changer les règles de routage
- Ajouter de nouveaux intents
- Modifier la sélection de LLM

### Personnaliser les Prompts

Chaque agent a son propre prompt système. Modifiez-les dans:
- `app/agents/network_agent.py`
- `app/agents/macos_agent.py`
- `app/agents/workspace_agent.py`
- `app/agents/knowledge_agent.py`

