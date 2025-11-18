# Procédure de Support pour Timesheet

**Catégorie:** timesheet
**Description:** Procédure standardisée pour résoudre les problèmes liés aux timesheets (application web).

**⚠️ IMPORTANT:** La timesheet est une **application web**, pas un problème MacBook. Ne pas poser de questions sur le MacBook ou le numéro de série.

## URLs par équipe

La timesheet est une application web dont l'URL dépend de l'équipe :
- **Skeelz:** https://timesheet.skeelz.com/
- **eTail:** https://timesheet.etail-agency.com/
- **The Creatives:** https://timesheet.thecreative-s.com/
- **Vymar:** Board Monday spécial (demander accès au board Monday)
- **Smartelia:** Tableau Sheet (demander accès au tableau)

## Questions de diagnostic

- Quel est le problème spécifique avec la timesheet ?
- À quelle équipe appartenez-vous ? (pour vérifier l'URL correcte)
- Pouvez-vous accéder à la timesheet ?
- Le problème concerne-t-il des données manquantes ou une modification nécessaire ?
- Le problème concerne-t-il l'accès à la timesheet ?

## Étapes de résolution

### Scénario 1: Données manquantes ou modification nécessaire

Si l'utilisateur a besoin de modifier des données ou qu'il manque des informations dans la timesheet :

#### Étape 1.1: Identifier la personne
Confirmer l'identité de la personne concernée.

#### Étape 1.2: Collecter les informations nécessaires
Demander les détails suivants :
- Dates concernées
- Clients concernés
- Projets/tâches concernés
- Description de la modification ou des données manquantes

#### Étape 1.3: Créer un ticket Odoo
Créer immédiatement un ticket avec toutes les informations collectées.

**Champs requis pour le ticket:**
- **title:** Timesheet - Modification/Données manquantes - [Nom de la personne]
- **description:** 
  - Nom de la personne
  - Dates concernées
  - Clients concernés
  - Projets/tâches concernés
  - Description détaillée de la modification ou des données manquantes
- **priority:** Moyenne

### Scénario 2: Problèmes d'accès à la timesheet

Si l'utilisateur ne peut pas accéder à la timesheet :

#### Étape 2.1: Identifier l'équipe et vérifier l'URL
Demander à l'utilisateur à quelle équipe il appartient (Skeelz, eTail, The Creatives, Vymar, ou Smartelia).
- Vérifier que l'utilisateur utilise la bonne URL selon son équipe :
  - **Skeelz:** https://timesheet.skeelz.com/
  - **eTail:** https://timesheet.etail-agency.com/
  - **The Creatives:** https://timesheet.thecreative-s.com/
  - **Vymar:** Board Monday spécial (demander accès au board Monday)
  - **Smartelia:** Tableau Sheet (demander accès au tableau)

#### Étape 2.2: Test en navigation privée
Demander à l'utilisateur d'essayer d'accéder à la timesheet en navigation privée (mode incognito) :
- Sur Chrome/Safari: Cmd+Shift+N
- Vérifier si le problème persiste en navigation privée

#### Étape 2.3: Analyser le message d'erreur
Si un message d'erreur apparaît :
- Demander à l'utilisateur le message d'erreur exact
- Notez toutes les informations affichées (code d'erreur, description, etc.)

#### Étape 2.4: Créer un ticket Odoo
Créer un ticket avec toutes les informations de diagnostic.

**Champs requis pour le ticket:**
- **title:** Timesheet - Problème d'accès - [Nom de la personne]
- **description:**
  - Nom de la personne
  - Équipe (Skeelz/eTail/The Creatives/Vymar/Smartelia)
  - URL utilisée ou attendue selon l'équipe
  - Résultat du test en navigation privée (fonctionne ou non)
  - Message d'erreur complet (s'il y en a un)
  - Navigateur utilisé
  - Étapes de diagnostic déjà effectuées
- **priority:** Moyenne

## Création de ticket Odoo

**Quand créer un ticket:**
- **Immédiatement** pour les données manquantes ou modifications nécessaires
- **Après diagnostic** pour les problèmes d'accès (si test navigation privée + analyse erreur n'ont pas résolu le problème)

## Problèmes fréquents

- Données manquantes dans la timesheet
- Modification de données existantes
- Problèmes d'accès à la timesheet (erreurs de connexion, permissions)
- Messages d'erreur lors de l'accès

---
*Procédure mise à jour selon les standards actuels*
