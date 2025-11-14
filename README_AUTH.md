# Système d'Authentification

Système d'authentification sécurisé avec SSO Google et contrôle d'accès basé sur une liste d'utilisateurs autorisés.

## Architecture

### Frontend (Next.js)
- **NextAuth.js** : Gestion de l'authentification OAuth
- **Google Provider** : SSO Google uniquement
- **Middleware** : Protection automatique des routes
- **Page de login** : Interface de connexion

### Backend (FastAPI)
- **JWT Verification** : Vérification des tokens dans les requêtes
- **Auth Middleware** : Protection des endpoints API
- **WebSocket Auth** : Authentification via query parameter

### Base de données (Supabase)
- **Table `users`** : Liste des utilisateurs autorisés
- **Table `user_sessions`** : Suivi des sessions actives
- **Fonctions SQL** : Vérification d'autorisation

## Configuration

### Variables d'environnement Frontend

```env
# NextAuth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your_secret_key_here

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Supabase
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

### Variables d'environnement Backend

```env
# Authentication
NEXTAUTH_SECRET=your_nextauth_secret_key_here
SECRET_KEY=your_secret_key_here
```

## Configuration Google OAuth

1. Aller sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créer un projet ou sélectionner un projet existant
3. Activer l'API Google+ 
4. Créer des identifiants OAuth 2.0
5. Ajouter les URI de redirection :
   - `http://localhost:3000/api/auth/callback/google` (dev)
   - `https://votre-domaine.com/api/auth/callback/google` (prod)
6. Copier le Client ID et Client Secret

## Utilisation

### Ajouter un utilisateur autorisé

```bash
python3 backend/scripts/add_user.py user@example.com --name "John Doe" --role "user"
```

### Flux d'authentification

1. **Utilisateur accède à l'application** → Redirigé vers `/login`
2. **Clic sur "Continuer avec Google"** → Redirection vers Google OAuth
3. **Connexion Google** → Google redirige vers le callback
4. **Vérification dans Supabase** → Vérifie si l'email est dans la table `users`
5. **Si autorisé** → Création de session JWT → Redirection vers le chat
6. **Si non autorisé** → Message d'erreur → Reste sur la page de login

### Protection des routes

- **Frontend** : Le middleware Next.js protège automatiquement toutes les routes sauf `/login` et `/api/auth`
- **Backend API** : Les endpoints REST nécessitent un header `Authorization: Bearer <token>`
- **WebSocket** : Le token est passé en query parameter `?token=<token>`

## Sécurité

✅ **SSO Google uniquement** : Pas de mots de passe à gérer
✅ **Liste blanche d'utilisateurs** : Seuls les emails dans la table `users` peuvent se connecter
✅ **JWT signés** : Tokens signés avec secret partagé
✅ **Sessions trackées** : Suivi des sessions dans Supabase
✅ **Expiration automatique** : Sessions expirées après 30 jours
✅ **HTTPS requis en production** : Les tokens ne doivent jamais transiter en clair

## Endpoints protégés

- `POST /api/v1/chat` : Requiert authentification
- `GET /api/v1/history/{session_id}` : Requiert authentification
- `WS /ws/{session_id}` : Requiert token en query parameter

## Maintenance

### Nettoyer les sessions expirées

```sql
SELECT cleanup_expired_sessions();
```

### Désactiver un utilisateur

```sql
UPDATE users SET is_active = FALSE WHERE email = 'user@example.com';
```

### Réactiver un utilisateur

```sql
UPDATE users SET is_active = TRUE WHERE email = 'user@example.com';
```

