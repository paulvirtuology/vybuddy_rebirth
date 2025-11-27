# Intégration du Widget Chat via Script Externe

Ce guide explique comment intégrer le widget VyBuddy Chat dans un portail externe (déployé sur un environnement différent) via un simple script JavaScript.

## Vue d'ensemble

Le widget est chargé via un script externe qui crée automatiquement :
- Un bouton flottant de chat
- Une fenêtre de chat en iframe
- La communication entre le portail et le widget

## Installation

### Étape 1 : Ajouter le script dans votre HTML

Ajoutez le script dans le `<head>` ou avant la fermeture du `</body>` de votre page HTML :

```html
<!DOCTYPE html>
<html>
<head>
  <title>Portail Vygeek</title>
</head>
<body>
  <!-- Votre contenu -->
  
  <!-- Script du widget VyBuddy -->
  <script src="https://votre-chatbot.com/chat-widget.js"></script>
  <script>
    VyBuddyWidget.init({
      chatbotUrl: 'https://votre-chatbot.com',
      position: 'bottom-right',
      buttonColor: '#6366f1',
      buttonSize: 'large'
    });
  </script>
</body>
</html>
```

### Étape 2 : Configuration

Remplacez `https://votre-chatbot.com` par l'URL de votre environnement chatbot.

## Options de configuration

### `chatbotUrl` (requis)
URL de base de votre application chatbot (ex: `https://chatbot.vygeek.com`)

### `position` (optionnel)
Position du bouton sur l'écran :
- `'bottom-right'` (par défaut)
- `'bottom-left'`
- `'top-right'`
- `'top-left'`

### `buttonColor` (optionnel)
Couleur du bouton en hexadécimal (par défaut: `'#6366f1'`)

### `buttonSize` (optionnel)
Taille du bouton :
- `'small'` (48x48px)
- `'medium'` (56x56px)
- `'large'` (64x64px, par défaut)

### `zIndex` (optionnel)
Z-index du widget (par défaut: `9999`)

## Exemple complet

```html
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Portail Vygeek</title>
</head>
<body>
  <header>
    <h1>Portail Vygeek</h1>
  </header>
  
  <main>
    <p>Bienvenue sur le portail Vygeek</p>
    <!-- Votre contenu -->
  </main>

  <!-- Widget VyBuddy Chat -->
  <script src="https://chatbot.vygeek.com/chat-widget.js"></script>
  <script>
    VyBuddyWidget.init({
      chatbotUrl: 'https://chatbot.vygeek.com',
      position: 'bottom-right',
      buttonColor: '#6366f1',
      buttonSize: 'large'
    });
  </script>
</body>
</html>
```

## API JavaScript

Le widget expose une API globale `VyBuddyWidget` :

### `VyBuddyWidget.init(config)`
Initialise le widget avec la configuration fournie.

```javascript
VyBuddyWidget.init({
  chatbotUrl: 'https://chatbot.vygeek.com',
  position: 'bottom-right',
  buttonColor: '#6366f1',
  buttonSize: 'large'
});
```

### `VyBuddyWidget.open()`
Ouvre le widget programmatiquement.

```javascript
VyBuddyWidget.open();
```

### `VyBuddyWidget.close()`
Ferme le widget programmatiquement.

```javascript
VyBuddyWidget.close();
```

### `VyBuddyWidget.toggle()`
Ouvre ou ferme le widget selon son état actuel.

```javascript
VyBuddyWidget.toggle();
```

### `VyBuddyWidget.destroy()`
Supprime complètement le widget de la page.

```javascript
VyBuddyWidget.destroy();
```

## Exemples d'utilisation

### Intégration basique

```html
<script src="https://chatbot.vygeek.com/chat-widget.js"></script>
<script>
  VyBuddyWidget.init({
    chatbotUrl: 'https://chatbot.vygeek.com'
  });
</script>
```

### Personnalisation complète

```html
<script src="https://chatbot.vygeek.com/chat-widget.js"></script>
<script>
  VyBuddyWidget.init({
    chatbotUrl: 'https://chatbot.vygeek.com',
    position: 'bottom-left',
    buttonColor: '#10b981',
    buttonSize: 'medium',
    zIndex: 10000
  });
</script>
```

### Contrôle programmatique

```html
<button onclick="VyBuddyWidget.open()">Ouvrir le chat</button>
<button onclick="VyBuddyWidget.close()">Fermer le chat</button>
<button onclick="VyBuddyWidget.toggle()">Toggle le chat</button>
```

## Architecture technique

### Flux de chargement

```
1. Script chat-widget.js chargé depuis le portail
2. Script crée le bouton flottant
3. Au clic, crée un iframe pointant vers /widget
4. L'iframe charge l'application React complète
5. Communication via postMessage entre portail et iframe
```

### Communication postMessage

Le widget utilise `postMessage` pour communiquer entre le portail et l'iframe :

**Portail → Widget (iframe)**
```javascript
iframe.contentWindow.postMessage({
  type: 'VYBUDDY_WIDGET_INIT',
  options: { /* config */ }
}, 'https://chatbot.vygeek.com');
```

**Widget (iframe) → Portail**
```javascript
window.parent.postMessage({
  type: 'VYBUDDY_WIDGET_READY',
  authenticated: true
}, '*');
```

## Sécurité

### CORS et origines

Pour la sécurité en production, vous devez :

1. **Configurer les origines autorisées** dans le script `chat-widget.js` :
```javascript
// Dans chat-widget.js, ligne ~60
if (!event.origin.startsWith(widgetConfig.chatbotUrl)) return;
```

2. **Configurer les headers CORS** sur votre serveur chatbot pour autoriser les iframes :
```
X-Frame-Options: ALLOW-FROM https://votre-portail.com
Content-Security-Policy: frame-ancestors https://votre-portail.com
```

3. **Spécifier l'origine exacte** dans les postMessage (au lieu de `'*'`) :
```javascript
window.parent.postMessage(data, 'https://votre-portail.com');
```

### Authentification

L'authentification Google OAuth fonctionne dans l'iframe. NextAuth gère automatiquement les redirections et les cookies.

## Dépannage

### Le widget ne s'affiche pas

1. **Vérifiez la console** pour les erreurs JavaScript
2. **Vérifiez que le script est chargé** : `console.log(VyBuddyWidget)`
3. **Vérifiez l'URL du chatbot** : doit être accessible depuis le navigateur
4. **Vérifiez les CORS** : l'iframe doit pouvoir charger depuis le chatbot

### L'iframe ne se charge pas

1. **Vérifiez l'URL** : `https://chatbot.vygeek.com/widget` doit être accessible
2. **Vérifiez les headers CORS** : voir section Sécurité
3. **Vérifiez la console** pour les erreurs de chargement

### L'authentification ne fonctionne pas

1. **Vérifiez les cookies** : NextAuth nécessite les cookies tiers (SameSite=None; Secure)
2. **Vérifiez les variables d'environnement** NextAuth dans le chatbot
3. **Vérifiez les redirect URIs** dans Google OAuth Console

### Le bouton est masqué

1. **Vérifiez le z-index** : augmentez-le si nécessaire
2. **Vérifiez les styles CSS** : certains frameworks peuvent masquer le bouton
3. **Vérifiez la position** : essayez une autre position

## Exemple avec React/Next.js (portail externe)

Si votre portail utilise React/Next.js :

```tsx
// pages/_app.tsx ou app/layout.tsx
import { useEffect } from 'react'

export default function App({ Component, pageProps }) {
  useEffect(() => {
    // Charger le script
    const script = document.createElement('script')
    script.src = 'https://chatbot.vygeek.com/chat-widget.js'
    script.async = true
    document.body.appendChild(script)

    script.onload = () => {
      // Initialiser le widget une fois le script chargé
      if (window.VyBuddyWidget) {
        window.VyBuddyWidget.init({
          chatbotUrl: 'https://chatbot.vygeek.com',
          position: 'bottom-right',
          buttonColor: '#6366f1',
          buttonSize: 'large'
        })
      }
    }

    return () => {
      // Nettoyer si nécessaire
      if (window.VyBuddyWidget) {
        window.VyBuddyWidget.destroy()
      }
    }
  }, [])

  return <Component {...pageProps} />
}
```

## Exemple avec Vue.js

```vue
<template>
  <div>
    <!-- Votre contenu -->
  </div>
</template>

<script>
export default {
  mounted() {
    // Charger le script
    const script = document.createElement('script')
    script.src = 'https://chatbot.vygeek.com/chat-widget.js'
    script.async = true
    document.body.appendChild(script)

    script.onload = () => {
      if (window.VyBuddyWidget) {
        window.VyBuddyWidget.init({
          chatbotUrl: 'https://chatbot.vygeek.com',
          position: 'bottom-right',
          buttonColor: '#6366f1',
          buttonSize: 'large'
        })
      }
    }
  },
  beforeUnmount() {
    if (window.VyBuddyWidget) {
      window.VyBuddyWidget.destroy()
    }
  }
}
</script>
```

## Support

Pour toute question ou problème, contactez l'équipe de développement VyBuddy.

## Notes importantes

1. **Performance** : Le widget charge l'iframe uniquement au premier clic
2. **Responsive** : Le widget s'adapte automatiquement aux écrans mobiles
3. **Isolation** : L'iframe isole complètement le chatbot du portail (pas de conflits CSS/JS)
4. **Sécurité** : L'iframe empêche l'accès direct au DOM du portail

