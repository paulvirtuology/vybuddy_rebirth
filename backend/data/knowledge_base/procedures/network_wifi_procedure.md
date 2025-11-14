# Procédure de Résolution des Problèmes de Connexion Wi-Fi

**Catégorie:** network_wifi
**Description:** Procédure standardisée pour diagnostiquer et résoudre les problèmes de connexion Wi-Fi.

## Questions de diagnostic

- Le problème concerne-t-il un réseau Wi-Fi spécifique ? Si oui, lequel ?
- Avez-vous redémarré votre routeur/modem récemment ?
- D'autres appareils peuvent-ils se connecter au réseau Wi-Fi ?
- Le problème persiste-t-il après avoir redémarré votre ordinateur ?
- Pouvez-vous voir le réseau Wi-Fi dans la liste des réseaux disponibles ?

## Étapes de résolution

### Étape 1: Vérifier la visibilité du réseau Wi-Fi

Demandez à l'utilisateur de vérifier si le réseau Wi-Fi est visible dans la liste des réseaux disponibles.

### Étape 2: Redémarrer le routeur/modem

Demandez à l'utilisateur de redémarrer son routeur/modem et d'attendre 2 minutes avant de réessayer de se connecter.

### Étape 3: Redémarrer l'ordinateur

Demandez à l'utilisateur de redémarrer son ordinateur pour réinitialiser les paramètres réseau.

### Étape 4: Exécuter une commande Flush DNS

Demandez à l'utilisateur d'ouvrir l'invite de commande et d'exécuter 'ipconfig /flushdns'.

### Étape 5: Vérifier les paramètres de l'adaptateur réseau

Assurez-vous que l'adaptateur réseau est activé et que les paramètres IP sont configurés pour obtenir automatiquement une adresse IP.


## Création de ticket Odoo

**Quand créer un ticket:** Si le problème persiste après avoir suivi toutes les étapes de résolution.

**Champs requis:**
- **title:** Problème de connexion Wi-Fi - [Nom de l'utilisateur]
- **description:** Inclure les détails des étapes suivies, les réponses aux questions de diagnostic, et toute erreur ou message observé.
- **priority:** Moyenne

## Problèmes fréquents

- Réseau Wi-Fi non visible
- Connexion intermittente
- Erreur d'authentification Wi-Fi
- Problème de configuration de l'adaptateur réseau

---
*Procédure générée à partir de 20 tickets résolus*
