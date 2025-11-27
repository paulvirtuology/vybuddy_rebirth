# Intégration Ultra-Simple via URL

## ✅ OUI, c'est possible !

Vous pouvez intégrer le widget en invoquant **juste une URL** avec des paramètres.

## Méthode 1 : URL avec paramètres (Recommandé)

```html
<script src="https://chatbot.vygeek.com/chat-widget.js?chatbotUrl=https://chatbot.vygeek.com&position=bottom-right&buttonColor=%236366f1&buttonSize=large"></script>
```

Le widget s'initialise **automatiquement** ! 🎉

## Méthode 2 : URL simple (auto-détection)

```html
<script src="https://chatbot.vygeek.com/chat-widget.js"></script>
```

Le widget détecte automatiquement l'URL du chatbot depuis l'URL du script et s'initialise avec les valeurs par défaut.

## Méthode 3 : Attributs data-* (Alternative)

```html
<script 
  src="https://chatbot.vygeek.com/chat-widget.js"
  data-chatbot-url="https://chatbot.vygeek.com"
  data-position="bottom-right"
  data-button-color="#6366f1"
  data-button-size="large">
</script>
```

## Paramètres disponibles dans l'URL

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| `chatbotUrl` | URL de votre chatbot | Auto-détecté depuis l'URL du script |
| `position` | Position: `bottom-right`, `bottom-left`, `top-right`, `top-left` | `bottom-right` |
| `buttonColor` | Couleur en hex (encoder `#` comme `%23`) | `#6366f1` |
| `buttonSize` | Taille: `small`, `medium`, `large` | `large` |

## Exemples pratiques

### Exemple minimal (tout automatique)

```html
<script src="https://chatbot.vygeek.com/chat-widget.js"></script>
```

### Exemple avec personnalisation

```html
<script src="https://chatbot.vygeek.com/chat-widget.js?position=bottom-left&buttonColor=%2310b981&buttonSize=medium"></script>
```

**Note :** `%23` = `#` dans les URLs (pour `buttonColor=%2310b981` = `#10b981`)

### Exemple complet HTML

```html
<!DOCTYPE html>
<html>
<head>
  <title>Mon Portail</title>
</head>
<body>
  <h1>Mon Portail</h1>
  <p>Contenu de votre portail...</p>
  
  <!-- Widget VyBuddy - Une seule ligne ! -->
  <script src="https://chatbot.vygeek.com/chat-widget.js?position=bottom-right&buttonColor=%236366f1"></script>
</body>
</html>
```

## Désactiver l'auto-initialisation

Si vous voulez contrôler manuellement l'initialisation :

```html
<script src="https://chatbot.vygeek.com/chat-widget.js" data-auto-init="false"></script>
<script>
  // Initialiser manuellement plus tard
  VyBuddyWidget.init({
    chatbotUrl: 'https://chatbot.vygeek.com',
    position: 'bottom-right'
  });
</script>
```

## Comparaison des méthodes

| Méthode | Simplicité | Flexibilité | Recommandé pour |
|---------|------------|-------------|-----------------|
| **URL avec paramètres** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Intégration rapide |
| **URL simple** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Configuration par défaut |
| **Attributs data-*** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | HTML propre |
| **Init manuelle** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Contrôle total |

## Résumé

**OUI**, vous pouvez intégrer le chatbot en invoquant juste une URL ! 

La solution actuelle supporte déjà cette fonctionnalité via :
- ✅ Auto-initialisation depuis l'URL du script
- ✅ Paramètres dans l'URL de requête
- ✅ Attributs data-* sur le script

**Aucun changement nécessaire** - c'est déjà implémenté ! 🎉

