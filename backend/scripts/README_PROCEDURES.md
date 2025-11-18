# Système de Base de Connaissances Procédurale

Ce système transforme les tickets résolus en procédures réutilisables pour améliorer le support IT.

## Architecture

### Étape 1: Catégorisation automatique
Le script `categorize_tickets.py` analyse tous les tickets résolus et les catégorise automatiquement en utilisant un LLM.

**Catégories principales:**
- `email_accounts`: Gestion des comptes email
- `monday_access`: Accès et configuration Monday.com
- `drive_access`: Accès Google Drive
- `software_installation`: Installation de logiciels
- `network_wifi`: Problèmes réseau et WiFi
- `macos_issues`: Problèmes macOS et MacBook
- `licenses`: Gestion des licences
- `workspace_tools`: Outils workspace (DocuSign, LastPass, etc.)
- `timesheet`: Gestion Timesheet
- `meeting_rooms`: Réservation de salles de réunion
- `other`: Autres

### Étape 2: Structuration en procédures
Le script `create_procedures.py` crée des procédures réutilisables à partir des tickets catégorisés.

**Structure d'une procédure:**
- **Titre et description**
- **Questions de diagnostic**: Questions à poser comme un support N1
- **Étapes de résolution**: Actions à effectuer étape par étape
- **Création de ticket Odoo**: Quand et comment créer un ticket
- **Problèmes fréquents**: Issues communes et solutions

### Étape 3: Chargement dans Pinecone
Les procédures sont chargées dans Pinecone pour la recherche vectorielle (RAG).

### Étape 4: Agents procéduraux
Les agents utilisent les procédures pour:
- Poser les bonnes questions de diagnostic
- Suivre les étapes de résolution
- Créer des tickets Odoo correctement remplis

### Étape 5: Stockage dans Supabase
Les procédures sont stockées dans Supabase pour:
- Accès rapide par les agents
- Suivi d'utilisation
- Amélioration continue

## Utilisation

### Pipeline complet
```bash
python backend/scripts/run_full_pipeline.py
```

### Étapes individuelles

1. **Catégoriser les tickets:**
```bash
python backend/scripts/categorize_tickets.py
```

2. **Créer les procédures:**
```bash
python backend/scripts/create_procedures.py
```

3. **Charger dans Pinecone:**
```bash
python backend/scripts/load_knowledge_base.py
```

4. **Charger dans Supabase:**
```bash
python backend/scripts/load_procedures_to_supabase.py
```

## Fichiers générés

- `backend/knowledge_base/tickets_categorises.json`: Tickets catégorisés
- `backend/knowledge_base/procedures.json`: Procédures au format JSON
- `backend/data/knowledge_base/procedures/*.md`: Procédures au format Markdown

## Schéma Supabase

Les procédures sont stockées dans la table `procedures` avec:
- `category`: Catégorie de la procédure
- `title`: Titre de la procédure
- `description`: Description
- `diagnostic_questions`: Questions de diagnostic (JSONB)
- `resolution_steps`: Étapes de résolution (JSONB)
- `ticket_creation`: Instructions pour créer un ticket (JSONB)
- `common_issues`: Problèmes fréquents (JSONB)

L'utilisation des procédures est suivie dans la table `procedure_usage`.

## Avantages

✅ **Pose exactement les bonnes questions** comme un humain N1
✅ **Suit les procédures internes réelles** basées sur les tickets résolus
✅ **Crée des tickets Odoo parfaitement remplis** avec toutes les informations nécessaires
✅ **Devient meilleur avec le temps** grâce au suivi d'utilisation

