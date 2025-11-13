# Guide d'Installation - VyBuddy Rebirth

## Prérequis

- Python 3.10+
- Node.js 18+
- npm ou yarn
- Comptes et clés API pour:
  - OpenAI
  - Anthropic
  - Google (Gemini)
  - Supabase
  - Redis Cloud
  - Pinecone
  - Odoo

## Installation Backend

1. **Créer un environnement virtuel**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

2. **Installer les dépendances**

```bash
pip install -r requirements.txt
```

3. **Configurer les variables d'environnement**

Copiez le fichier `.env.example` vers `.env` et remplissez les valeurs :

```bash
cp .env.example .env
```

Puis éditez le fichier `.env` avec vos clés API et configurations. Consultez le fichier `.env.example` pour voir toutes les variables nécessaires avec leurs descriptions.

4. **Configurer Supabase**

Exécutez le script SQL `supabase_schema.sql` dans l'éditeur SQL de Supabase pour créer les tables nécessaires.

5. **Configurer Pinecone**

Créez un index dans Pinecone avec:
- Nom: `vybuddy-rag` (ou celui configuré dans `.env`)
- Dimensions: 1536 (pour text-embedding-3-small d'OpenAI)
- Métrique: cosine

6. **Démarrer le serveur**

```bash
uvicorn main:app --reload --port 8000
```

## Installation Frontend

1. **Installer les dépendances**

```bash
cd frontend
npm install
```

2. **Configurer les variables d'environnement**

Copiez le fichier `.env.example` vers `.env.local` et ajustez si nécessaire :

```bash
cp .env.example .env.local
```

Le fichier `.env.local` contient l'URL du backend. Par défaut, c'est `http://localhost:8000` pour le développement.

3. **Démarrer le serveur de développement**

```bash
npm run dev
```

Le frontend sera accessible sur `http://localhost:3000`

## Configuration Odoo

1. Assurez-vous que le module Helpdesk est installé dans Odoo
2. Créez une équipe Helpdesk si nécessaire
3. Vérifiez que l'API XML-RPC est activée
4. Testez la connexion avec les identifiants configurés

## Vérification

1. Backend: `http://localhost:8000/health` devrait retourner `{"status": "healthy"}`
2. Frontend: Ouvrez `http://localhost:3000` et testez le chat
3. Vérifiez les logs dans la console pour détecter d'éventuelles erreurs

## Dépannage

### Erreur de connexion Redis
- Vérifiez l'URL Redis Cloud
- Vérifiez le mot de passe
- Testez la connexion avec `redis-cli`

### Erreur Supabase
- Vérifiez que les tables sont créées
- Vérifiez les clés API
- Vérifiez les permissions RLS si activées

### Erreur Pinecone
- Vérifiez que l'index existe
- Vérifiez les dimensions de l'index (1536 pour OpenAI embeddings)
- Vérifiez la clé API

### Erreur Odoo
- Vérifiez que XML-RPC est activé
- Vérifiez les identifiants
- Vérifiez que le module Helpdesk est installé

