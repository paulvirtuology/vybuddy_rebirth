# Intégration Slack - VyBuddy

Ce document explique comment configurer et utiliser l'intégration Slack de VyBuddy.

## Vue d'ensemble

L'intégration Slack permet à VyBuddy de:
- Répondre aux messages dans les canaux Slack
- Répondre aux mentions directes
- Gérer les commandes slash (`/vybuddy`)
- Maintenir le contexte des conversations via les threads
- Sauvegarder toutes les interactions dans Supabase

## Architecture

```
Slack Workspace
    ↓ (webhook)
FastAPI /api/v1/slack/events
    ↓
SlackService (vérification signature, envoi messages)
    ↓
OrchestratorService (traitement avec les agents)
    ↓
Réponse envoyée dans Slack
```

## Configuration

### 1. Créer une application Slack

1. Allez sur [api.slack.com/apps](https://api.slack.com/apps)
2. Cliquez sur "Create New App" → "From scratch"
3. Donnez un nom à votre app (ex: "VyBuddy") et sélectionnez votre workspace
4. Notez l'**App ID** (visible dans "Basic Information")

### 2. Configurer les OAuth & Permissions

1. Dans le menu de gauche, allez dans "OAuth & Permissions"
2. Dans "Scopes" → "Bot Token Scopes", ajoutez:
   - `app_mentions:read` - Pour recevoir les mentions
   - `channels:history` - Pour lire l'historique des canaux publics
   - `channels:read` - Pour obtenir les infos des canaux
   - `chat:write` - Pour envoyer des messages
   - `commands` - Pour les commandes slash
   - `groups:history` - Pour lire l'historique des canaux privés
   - `groups:read` - Pour obtenir les infos des canaux privés
   - `im:history` - Pour lire les messages directs
   - `im:read` - Pour obtenir les infos des messages directs
   - `im:write` - Pour envoyer des messages directs
   - `users:read` - Pour obtenir les infos des utilisateurs
   - `users:read.email` - Pour obtenir les emails des utilisateurs

3. Faites défiler vers le haut et cliquez sur "Install to Workspace"
4. Autorisez l'application
5. Copiez le **Bot User OAuth Token** (commence par `xoxb-`)

### 3. Configurer les Event Subscriptions

1. Dans le menu de gauche, allez dans "Event Subscriptions"
2. Activez "Enable Events"
3. Dans "Request URL", entrez:
   ```
   https://votre-domaine.com/api/v1/slack/events
   ```
   Ou pour le développement local avec ngrok:
   ```
   https://votre-ngrok-url.ngrok.io/api/v1/slack/events
   ```
4. Slack enverra un challenge pour vérifier l'URL. Si tout est correct, vous verrez "✓ Verified"
5. Dans "Subscribe to bot events", ajoutez:
   - `app_mentions` - Quand le bot est mentionné
   - `message.channels` - Messages dans les canaux publics
   - `message.groups` - Messages dans les canaux privés
   - `message.im` - Messages directs

6. Cliquez sur "Save Changes"

### 4. Configurer les Slash Commands (optionnel)

1. Dans le menu de gauche, allez dans "Slash Commands"
2. Cliquez sur "Create New Command"
3. Configurez:
   - **Command**: `/vybuddy`
   - **Request URL**: `https://votre-domaine.com/api/v1/slack/commands`
   - **Short Description**: `Posez une question à VyBuddy`
   - **Usage Hint**: `[votre question]`
4. Cliquez sur "Save"
5. Répétez pour créer `/vybuddy-help` (optionnel)

### 5. Récupérer le Signing Secret

1. Dans le menu de gauche, allez dans "Basic Information"
2. Faites défiler jusqu'à "App Credentials"
3. Copiez le **Signing Secret**

### 6. Configurer les variables d'environnement

Ajoutez ces variables dans votre fichier `.env`:

```bash
# Slack Integration
SLACK_BOT_TOKEN=xoxb-votre-token-bot
SLACK_SIGNING_SECRET=votre-signing-secret
SLACK_APP_ID=votre-app-id
```

### 7. Installer les dépendances

```bash
cd backend
pip install -r requirements.txt
```

## Utilisation

### Messages dans les canaux

1. Invitez le bot dans un canal: `/invite @VyBuddy`
2. Mentionnez le bot: `@VyBuddy Comment réinitialiser mon mot de passe?`
3. Le bot répondra dans un thread

### Messages directs

1. Ouvrez une conversation directe avec le bot
2. Envoyez votre message
3. Le bot répondra directement

### Commandes slash

1. Dans n'importe quel canal ou message direct, tapez:
   ```
   /vybuddy Comment créer un compte Google Workspace?
   ```
2. Le bot répondra dans le canal (ou en privé selon la commande)

## Développement local

Pour tester en local, utilisez [ngrok](https://ngrok.com/):

```bash
# Installer ngrok
brew install ngrok  # macOS
# ou télécharger depuis https://ngrok.com/

# Démarrer le tunnel
ngrok http 8000

# Utiliser l'URL fournie (ex: https://abc123.ngrok.io)
# dans la configuration Slack Event Subscriptions
```

## Base de données

Les conversations Slack sont stockées dans Supabase avec:
- `session_id`: Format `slack_{channel_id}_{thread_ts}` ou `slack_{channel_id}_{ts}`
- `user_id`: Email de l'utilisateur Slack (ou `slack_{user_id}` si pas d'email)
- `metadata`: JSON contenant les infos Slack (channel, user, timestamps, etc.)

Voir `backend/scripts/slack_integration_schema.sql` pour les extensions optionnelles.

## Sécurité

- **Vérification des signatures**: Toutes les requêtes Slack sont vérifiées via HMAC SHA256
- **Timestamp validation**: Les requêtes trop anciennes (>5 min) sont rejetées
- **Bot message filtering**: Les messages du bot lui-même sont ignorés pour éviter les boucles

## Dépannage

### Le bot ne répond pas

1. Vérifiez que le bot est invité dans le canal
2. Vérifiez les logs du backend pour les erreurs
3. Vérifiez que les Event Subscriptions sont activées
4. Vérifiez que le token est correct dans `.env`

### Erreur "Invalid signature"

1. Vérifiez que `SLACK_SIGNING_SECRET` est correct
2. Vérifiez que l'URL du webhook est correcte
3. En développement, la vérification peut être désactivée (voir `slack_service.py`)

### Le bot répond en double

1. Vérifiez qu'il n'y a qu'une seule instance du bot en cours d'exécution
2. Vérifiez les Event Subscriptions pour éviter les doublons

## Endpoints API

### POST /api/v1/slack/events

Endpoint principal pour recevoir les événements Slack.

**Headers requis:**
- `X-Slack-Signature`: Signature HMAC
- `X-Slack-Request-Timestamp`: Timestamp de la requête

**Réponses:**
- `200 OK` avec `{"challenge": "..."}` pour l'URL verification
- `200 OK` avec `{"status": "ok"}` pour les événements traités

### POST /api/v1/slack/commands

Endpoint pour les commandes slash.

**Headers requis:**
- `X-Slack-Signature`: Signature HMAC
- `X-Slack-Request-Timestamp`: Timestamp de la requête

**Body (form-data):**
- `command`: La commande (ex: `/vybuddy`)
- `text`: Le texte de la commande
- `user_id`: ID de l'utilisateur
- `channel_id`: ID du canal

### POST /api/v1/slack/interactions

Endpoint pour les interactions interactives (boutons, menus, etc.).

**Note:** Actuellement, cet endpoint retourne juste un accusé de réception. Les interactions peuvent être implémentées plus tard.

## Prochaines étapes

- [ ] Support des interactions interactives (boutons, menus)
- [ ] Support des blocs Slack (rich formatting)
- [ ] Notifications pour les tickets créés
- [ ] Dashboard d'analyse des conversations Slack
- [ ] Support des fichiers et images

## Support

Pour toute question ou problème, consultez:
- [Documentation Slack API](https://api.slack.com/)
- Les logs du backend
- La documentation VyBuddy dans `docs/`

