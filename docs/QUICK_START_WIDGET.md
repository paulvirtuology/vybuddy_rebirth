# Quick Start - Intégration Widget Externe

## 🚀 Intégration Ultra-Simple (1 ligne)

**OUI, vous pouvez intégrer en invoquant juste une URL !**

```html
<script src="https://chatbot.vygeek.com/chat-widget.js"></script>
```

Le widget s'initialise **automatiquement** ! 🎉

## Intégration avec personnalisation (1 ligne)

```html
<script src="https://chatbot.vygeek.com/chat-widget.js?position=bottom-right&buttonColor=%236366f1&buttonSize=large"></script>
```

## Intégration manuelle (2 étapes)

### 1. Ajouter le script dans votre HTML

```html
<script src="https://votre-chatbot.com/chat-widget.js" data-auto-init="false"></script>
```

### 2. Initialiser le widget

```html
<script>
  VyBuddyWidget.init({
    chatbotUrl: 'https://votre-chatbot.com'
  });
</script>
```

## Exemple complet HTML

```html
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Mon Portail</title>
</head>
<body>
  <h1>Mon Portail</h1>
  <p>Contenu de votre portail...</p>
  
  <!-- Widget VyBuddy - Auto-initialisation -->
  <script src="https://chatbot.vygeek.com/chat-widget.js"></script>
</body>
</html>
```

## Paramètres dans l'URL

Vous pouvez passer les paramètres directement dans l'URL du script :

```html
<script src="https://chatbot.vygeek.com/chat-widget.js?position=bottom-left&buttonColor=%2310b981&buttonSize=medium"></script>
```

**Note :** `%23` = `#` dans les URLs (pour `buttonColor=%2310b981` = `#10b981`)

## Options disponibles

| Option | Type | Défaut | Description |
|--------|------|--------|-------------|
| `chatbotUrl` | string | Auto-détecté | URL de votre chatbot (détecté depuis l'URL du script) |
| `position` | string | `'bottom-right'` | Position: `'bottom-right'`, `'bottom-left'`, `'top-right'`, `'top-left'` |
| `buttonColor` | string | `'#6366f1'` | Couleur du bouton en hex (encoder `#` comme `%23` dans l'URL) |
| `buttonSize` | string | `'large'` | Taille: `'small'` (48px), `'medium'` (56px), `'large'` (64px) |
| `zIndex` | number | `9999` | Z-index du widget |

## API JavaScript

```javascript
// Ouvrir le widget
VyBuddyWidget.open();

// Fermer le widget
VyBuddyWidget.close();

// Toggle
VyBuddyWidget.toggle();

// Détruire le widget
VyBuddyWidget.destroy();
```

## Fichiers du widget

- **`/public/chat-widget.js`** : Script loader externe (à charger depuis votre portail)
- **`/app/widget/page.tsx`** : Page iframe du widget (servie automatiquement)
- **`/components/ChatWidgetIframe.tsx`** : Composant React pour l'iframe

## Documentation complète

Pour plus de détails, consultez :
- **[INTEGRATION_WIDGET_EXTERNE.md](./INTEGRATION_WIDGET_EXTERNE.md)** - Documentation complète avec toutes les options
- **[AUTHENTIFICATION_WIDGET.md](./AUTHENTIFICATION_WIDGET.md)** - Comment fonctionne l'authentification Google OAuth dans l'iframe

