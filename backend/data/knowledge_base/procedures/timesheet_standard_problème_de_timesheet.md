# Problème de timesheet

**Catégorie:** timesheet
**Description:** Procédure standard pour problème de timesheet (application web)

**⚠️ IMPORTANT:** La timesheet est une **application web**. Ne PAS poser de questions sur le MacBook ou le numéro de série.

## URLs par équipe

- **Skeelz:** https://timesheet.skeelz.com/
- **eTail:** https://timesheet.etail-agency.com/
- **The Creatives:** https://timesheet.thecreative-s.com/
- **Vymar:** Board Monday spécial
- **Smartelia:** Tableau Sheet

## Questions de diagnostic

- Quel/Quelle est la personne ?
- À quelle équipe appartient la personne ? (pour vérifier l'URL)
- Le problème concerne-t-il des données manquantes ou une modification nécessaire ?
- Le problème concerne-t-il l'accès à la timesheet ?

## Étapes de résolution

### Scénario 1: Données manquantes ou modification nécessaire

#### Étape 1: Identifier la personne

#### Étape 2: Collecter les informations nécessaires
- Dates concernées
- Clients concernés
- Projets/tâches concernés
- Description de la modification ou des données manquantes

#### Étape 3: Envoi de ticket vers odoo avec les détails
Créer immédiatement un ticket avec : dates, clients, projets/tâches, description

### Scénario 2: Problèmes d'accès

#### Étape 1: Identifier l'équipe et vérifier l'URL
Demander l'équipe (Skeelz/eTail/The Creatives/Vymar/Smartelia) et vérifier que l'URL correspond :
- Skeelz → https://timesheet.skeelz.com/
- eTail → https://timesheet.etail-agency.com/
- The Creatives → https://timesheet.thecreative-s.com/
- Vymar → Board Monday spécial
- Smartelia → Tableau Sheet

#### Étape 2: Test en navigation privée
Demander à l'utilisateur d'essayer en navigation privée (Cmd+Shift+N)

#### Étape 3: Analyser le message d'erreur
Noter le message d'erreur complet (code, description, etc.)

#### Étape 4: Créer un ticket Odoo
Créer un ticket avec toutes les informations de diagnostic collectées

## Création de ticket Odoo

**Quand créer un ticket:**
- **Immédiatement** pour les données manquantes ou modifications nécessaires (avec dates, clients, etc.)
- **Après diagnostic** pour les problèmes d'accès (après vérification URL, test navigation privée, analyse erreur)

**Champs requis:**
- **title:** Timesheet - [Type de problème] - [Nom de la personne]
- **description:** 
  - Pour données manquantes/modification: Nom, dates, clients, projets/tâches, description
  - Pour problèmes d'accès: Nom, équipe (Skeelz/eTail/The Creatives/Vymar/Smartelia), URL utilisée ou attendue, résultat navigation privée, message d'erreur, navigateur, étapes de diagnostic
- **priority:** Moyenne

---
*Procédure standard mise à jour*
