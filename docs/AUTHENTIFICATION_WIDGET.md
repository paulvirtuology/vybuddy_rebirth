# Authentification dans le Widget Chat

Ce document explique comment fonctionne l'authentification Google OAuth dans le widget chargé via `chat-widget.js`.

## Vue d'ensemble

L'authentification fonctionne **entièrement dans l'iframe** du widget. Le portail externe n'a **aucune interaction** avec le processus d'authentification.

## Architecture

```
┌─────────────────────────────────────┐
│  Portail Externe                    │
│  (votre-portail.com)                │
│                                     │
│  ┌───────────────────────────────┐  │
│  │  iframe (chatbot.com/widget)  │  │
│  │                               │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │  NextAuth SessionProvider│  │  │
│  │  │  + ChatWidgetIframe      │  │  │
│  │  └─────────────────────────┘  │  │
│  │                               │  │
│  │  Authentification isolée      │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Flux d'authentification

### 1. Chargement initial du widget

```javascript
// chat-widget.js crée l'iframe
iframe.src = 'https://chatbot.vygeek.com/widget'
```

L'iframe charge la page `/widget` qui contient :
- `SessionProvider` (NextAuth)
- `ChatWidgetIframe` (composant React)

### 2. Vérification de la session

```tsx
// ChatWidgetIframe.tsx
const { data: session, status } = useSession()
```

NextAuth vérifie automatiquement :
- Si un cookie de session existe
- Si la session est valide
- Si l'utilisateur est authentifié

### 3. État non authentifié

Si `status === 'unauthenticated'`, le widget affiche :

```tsx
<button onClick={() => signIn('google', { callbackUrl: window.location.href })}>
  Continuer avec Google
</button>
```

### 4. Clic sur "Continuer avec Google"

```tsx
signIn('google', { callbackUrl: window.location.href })
```

**Ce qui se passe :**
1. NextAuth redirige vers `/api/auth/signin/google`
2. Redirection vers Google OAuth
3. L'utilisateur se connecte avec son compte Google
4. Google redirige vers `/api/auth/callback/google?code=...`

### 5. Callback NextAuth

```typescript
// app/api/auth/[...nextauth]/route.ts
async signIn({ user, account, profile }) {
  // 1. Vérifier si l'utilisateur est autorisé dans Supabase
  const { data } = await supabase.rpc('is_user_authorized', { 
    user_email: user.email 
  })
  
  // 2. Si autorisé, créer/mettre à jour le profil
  if (data === true) {
    return true // Authentification réussie
  }
  
  // 3. Si non autorisé, rejeter
  throw new Error("UNAUTHORIZED")
}
```

### 6. Création de la session

```typescript
async session({ session, token }) {
  // Créer un JWT pour le backend
  const backendToken = jwt.sign({
    email: token.email,
    name: token.name,
    picture: token.picture,
  }, process.env.NEXTAUTH_SECRET!, { expiresIn: "30d" })
  
  session.accessToken = backendToken
  return session
}
```

### 7. Redirection et cookies

NextAuth :
- Crée un cookie de session (`next-auth.session-token`)
- Redirige vers `callbackUrl` (l'iframe `/widget`)
- La session est maintenant disponible dans l'iframe

### 8. État authentifié

```tsx
// ChatWidgetIframe.tsx
if (status === 'authenticated' && session) {
  // Afficher le chat
  // Créer une session de chat
  // Connecter le WebSocket avec le token
}
```

## Points importants

### Isolation dans l'iframe

✅ **L'authentification est complètement isolée** dans l'iframe :
- Les cookies NextAuth sont stockés pour le domaine du chatbot (`chatbot.vygeek.com`)
- Le portail externe n'a **aucun accès** aux cookies ou à la session
- Pas de partage de session entre le portail et le widget

### Cookies et SameSite

Pour que l'authentification fonctionne dans une iframe cross-origin, NextAuth doit être configuré avec :

```typescript
// next.config.js ou variables d'environnement
cookies: {
  sessionToken: {
    name: `__Secure-next-auth.session-token`,
    options: {
      httpOnly: true,
      sameSite: 'none', // Important pour iframe cross-origin
      path: '/',
      secure: true, // HTTPS requis
    },
  },
}
```

### Configuration Google OAuth

Dans Google Cloud Console, les URI de redirection doivent inclure :

```
https://chatbot.vygeek.com/api/auth/callback/google
```

**Important :** L'URL doit pointer vers le **domaine du chatbot**, pas celui du portail.

## Flux complet (schéma)

```
1. Utilisateur ouvre le widget
   ↓
2. iframe charge /widget
   ↓
3. NextAuth vérifie la session
   ↓
4. Si non authentifié → Affiche bouton Google
   ↓
5. Utilisateur clique "Continuer avec Google"
   ↓
6. Redirection vers Google OAuth
   ↓
7. Utilisateur se connecte avec Google
   ↓
8. Google redirige vers /api/auth/callback/google
   ↓
9. NextAuth vérifie l'autorisation (Supabase)
   ↓
10. Si autorisé → Crée session + cookie
   ↓
11. Redirection vers /widget (iframe)
   ↓
12. Session disponible → Affiche le chat
```

## Sécurité

### Vérification d'autorisation

Chaque utilisateur doit être **explicitement autorisé** dans Supabase :

```sql
-- Table users
SELECT * FROM users WHERE email = 'user@example.com' AND is_active = true;
```

Si l'utilisateur n'est pas dans la table `users`, l'authentification est **rejetée**.

### Tokens JWT

Le token JWT créé par NextAuth est utilisé pour :
- Authentifier les requêtes API vers le backend
- Authentifier les connexions WebSocket
- Identifier l'utilisateur dans les logs

```typescript
// Dans les requêtes API
headers: {
  'Authorization': `Bearer ${session.accessToken}`
}

// Dans WebSocket
ws://chatbot.com/ws/session-id?token=${session.accessToken}
```

## Dépannage

### L'authentification ne fonctionne pas dans l'iframe

**Problème :** Les cookies ne sont pas sauvegardés dans l'iframe.

**Solutions :**
1. Vérifier que `sameSite: 'none'` est configuré
2. Vérifier que `secure: true` est configuré (HTTPS requis)
3. Vérifier que le domaine du chatbot est correct dans les cookies

### Erreur "UNAUTHORIZED"

**Problème :** L'utilisateur n'est pas dans la table `users` de Supabase.

**Solution :**
```bash
python3 backend/scripts/add_user.py user@example.com --name "John Doe" --role "user"
```

### La redirection ne fonctionne pas

**Problème :** `callbackUrl` pointe vers le mauvais domaine.

**Solution :** S'assurer que `callbackUrl` pointe vers l'iframe :
```typescript
signIn('google', { callbackUrl: window.location.href }) // URL de l'iframe
```

## Variables d'environnement requises

```env
# NextAuth
NEXTAUTH_URL=https://chatbot.vygeek.com
NEXTAUTH_SECRET=your_secret_key

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Supabase (pour vérification des utilisateurs)
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

## Résumé

✅ **L'authentification fonctionne entièrement dans l'iframe**
✅ **Le portail externe n'a aucune interaction avec l'auth**
✅ **NextAuth gère automatiquement les cookies et sessions**
✅ **Chaque utilisateur doit être autorisé dans Supabase**
✅ **Les tokens JWT sont utilisés pour authentifier les API/WebSocket**

