# Intégration du Widget Chat Bubble

Ce guide explique comment intégrer le widget de chat VyBuddy dans le portail Vygeek ou toute autre application.

## Vue d'ensemble

Le widget `ChatBubbleWidget` est un composant React qui affiche un bouton flottant de chat. Lorsqu'il est cliqué, il ouvre une fenêtre de chat simplifiée avec les fonctionnalités de base :
- Chat en temps réel avec VyBuddy
- Nouvelle conversation
- Authentification Google OAuth

## Prérequis

1. **NextAuth configuré** : Le widget utilise NextAuth pour l'authentification Google
2. **SessionProvider** : Le composant doit être enveloppé dans un `SessionProvider` de NextAuth
3. **Variables d'environnement** : Les mêmes variables que l'application principale (GOOGLE_CLIENT_ID, etc.)

## Installation

### 1. Copier les composants

Les composants suivants sont nécessaires :
- `frontend/components/ChatBubbleWidget.tsx`
- `frontend/components/ChatWidgetWindow.tsx`
- `frontend/components/MessageList.tsx` (déjà existant)
- `frontend/components/MessageInput.tsx` (déjà existant)
- `frontend/hooks/useWebSocket.ts` (déjà existant)

### 2. Intégration dans votre application

#### Option A : Intégration dans un layout Next.js

```tsx
// app/layout.tsx ou app/portail/layout.tsx
'use client'

import { SessionProvider } from 'next-auth/react'
import ChatBubbleWidget from '@/components/ChatBubbleWidget'

export default function PortalLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <SessionProvider>
      {children}
      {/* Widget de chat - s'affiche sur toutes les pages */}
      <ChatBubbleWidget />
    </SessionProvider>
  )
}
```

#### Option B : Intégration dans une page spécifique

```tsx
// app/portail/page.tsx
'use client'

import { SessionProvider } from 'next-auth/react'
import ChatBubbleWidget from '@/components/ChatBubbleWidget'

export default function PortalPage() {
  return (
    <SessionProvider>
      <div>
        {/* Votre contenu du portail */}
        <h1>Portail Vygeek</h1>
      </div>

      {/* Widget de chat */}
      <ChatBubbleWidget />
    </SessionProvider>
  )
}
```

#### Option C : Intégration dans une application React externe

Si vous intégrez dans une application React non-Next.js, vous devrez :

1. Installer les dépendances :
```bash
npm install next-auth react-hot-toast axios
```

2. Configurer NextAuth dans votre application
3. Utiliser le composant de la même manière

## Personnalisation

### Position du widget

```tsx
<ChatBubbleWidget position="bottom-right" />  // Par défaut
<ChatBubbleWidget position="bottom-left" />
<ChatBubbleWidget position="top-right" />
<ChatBubbleWidget position="top-left" />
```

### Couleur du bouton

```tsx
<ChatBubbleWidget buttonColor="bg-indigo-tropical" />  // Par défaut
<ChatBubbleWidget buttonColor="bg-blue-600" />
<ChatBubbleWidget buttonColor="bg-green-500" />
```

### Taille du bouton

```tsx
<ChatBubbleWidget buttonSize="large" />   // Par défaut (64x64px)
<ChatBubbleWidget buttonSize="medium" /> // 56x56px
<ChatBubbleWidget buttonSize="small" />  // 48x48px
```

### Exemple complet avec personnalisation

```tsx
<ChatBubbleWidget
  position="bottom-left"
  buttonColor="bg-blue-600"
  buttonSize="medium"
/>
```

## Fonctionnalités

### Authentification

À l'ouverture du widget :
- Si l'utilisateur n'est **pas connecté** : affiche un bouton "Continuer avec Google"
- Si l'utilisateur est **connecté** : affiche directement le chat

### Chat

- **Messages en temps réel** : Communication bidirectionnelle via WebSocket
- **Streaming** : Les réponses de VyBuddy s'affichent en temps réel
- **Historique** : Les messages sont chargés depuis Supabase
- **Feedback** : Possibilité de liker/disliker et commenter les réponses

### Nouvelle conversation

Un bouton "Nouvelle conversation" est disponible dans le header du widget pour démarrer un nouveau chat.

## Architecture technique

### Composants

1. **ChatBubbleWidget** : Bouton flottant et gestion de l'ouverture/fermeture
2. **ChatWidgetWindow** : Fenêtre de chat avec :
   - Gestion de l'authentification
   - Interface de chat simplifiée
   - WebSocket pour les messages en temps réel
   - Intégration avec l'API backend

### Flux d'authentification

```
Utilisateur ouvre le widget
    ↓
Vérification de la session NextAuth
    ↓
Si non authentifié → Affiche bouton Google
    ↓
Si authentifié → Affiche le chat
```

### Flux de chat

```
Utilisateur envoie un message
    ↓
WebSocket → Backend
    ↓
Backend traite avec les agents
    ↓
Réponse streamée via WebSocket
    ↓
Affichage en temps réel dans le widget
```

## Variables d'environnement requises

```env
# API Backend
NEXT_PUBLIC_API_URL=http://localhost:8000

# NextAuth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your_secret

# Google OAuth
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

# Supabase (pour l'authentification et les messages)
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_key
```

## Dépannage

### Le widget ne s'affiche pas

1. Vérifiez que `SessionProvider` enveloppe le composant
2. Vérifiez les styles CSS (Tailwind doit être configuré)
3. Vérifiez la console pour les erreurs

### L'authentification ne fonctionne pas

1. Vérifiez les variables d'environnement NextAuth
2. Vérifiez que les routes d'authentification sont configurées (`/api/auth/[...nextauth]`)
3. Vérifiez les credentials Google OAuth

### Les messages ne s'affichent pas

1. Vérifiez la connexion WebSocket (onglet Network dans DevTools)
2. Vérifiez que `NEXT_PUBLIC_API_URL` est correct
3. Vérifiez que le token d'authentification est valide

### Le widget est masqué par d'autres éléments

Le widget utilise `z-50` pour le bouton et `z-50` pour la fenêtre. Si nécessaire, ajustez le z-index dans le CSS.

## Exemple d'utilisation complète

```tsx
'use client'

import { SessionProvider } from 'next-auth/react'
import ChatBubbleWidget from '@/components/ChatBubbleWidget'

export default function PortalPage() {
  return (
    <SessionProvider>
      <div className="min-h-screen bg-gray-50">
        {/* Header du portail */}
        <header className="bg-white shadow">
          <div className="max-w-7xl mx-auto px-4 py-6">
            <h1 className="text-2xl font-bold">Portail Vygeek</h1>
          </div>
        </header>

        {/* Contenu principal */}
        <main className="max-w-7xl mx-auto px-4 py-8">
          <p>Bienvenue sur le portail Vygeek</p>
          {/* ... reste du contenu ... */}
        </main>

        {/* Widget de chat - toujours visible */}
        <ChatBubbleWidget
          position="bottom-right"
          buttonColor="bg-indigo-tropical"
          buttonSize="large"
        />
      </div>
    </SessionProvider>
  )
}
```

## Notes importantes

1. **SessionProvider** : Doit être au niveau le plus haut possible (layout ou page racine)
2. **Performance** : Le widget ne charge les données que lorsqu'il est ouvert
3. **Responsive** : Le widget est optimisé pour desktop. Pour mobile, considérez une version fullscreen
4. **Sécurité** : L'authentification est gérée par NextAuth, les tokens sont sécurisés

## Support

Pour toute question ou problème, contactez l'équipe de développement VyBuddy.

