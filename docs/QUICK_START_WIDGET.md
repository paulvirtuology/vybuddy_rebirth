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

## Exemple complet

```html
<!DOCTYPE html>
<html>
<head>
  <title>Mon Portail</title>
</head>
<body>
  <!-- Votre contenu -->
  
  <!-- Widget VyBuddy -->
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

## Options disponibles

| Option | Type | Défaut | Description |
|--------|------|--------|-------------|
| `chatbotUrl` | string | requis | URL de votre chatbot |
| `position` | string | `'bottom-right'` | Position du bouton |
| `buttonColor` | string | `'#6366f1'` | Couleur du bouton (hex) |
| `buttonSize` | string | `'large'` | Taille: `'small'`, `'medium'`, `'large'` |

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

## Fichiers créés

- **`/public/chat-widget.js`** : Script loader externe
- **`/app/widget/page.tsx`** : Page iframe du widget
- **`/components/ChatWidgetIframe.tsx`** : Composant React pour l'iframe
- **`/public/widget-example.html`** : Exemple HTML complet

## Documentation complète

- **[INTEGRATION_URL_SIMPLE.md](./INTEGRATION_URL_SIMPLE.md)** - Intégration via URL (recommandé)
- **[INTEGRATION_WIDGET_EXTERNE.md](./INTEGRATION_WIDGET_EXTERNE.md)** - Documentation complète avec toutes les options

