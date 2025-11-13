# Base de Connaissances VyBuddy

Ce dossier contient la documentation spécifique à votre environnement qui sera chargée dans Pinecone pour le RAG (Retrieval-Augmented Generation).

## Structure

Tous les fichiers de connaissances sont au format **Markdown uniforme** (`.md`).

### Fichiers disponibles
- `wifi_macbook_jamf.md` : Documentation sur les problèmes WiFi avec MacBook gérés par Jamf
- `macos_jamf.md` : Documentation sur le support MacOS avec restrictions Jamf
- `macbook.md` : FAQ complète sur MacBook et macOS
- `monday.md` : FAQ sur Monday.com
- `lastpass.md` : FAQ sur LastPass Enterprise
- `google_workspace.md` : FAQ sur Google Workspace

## Chargement dans Pinecone

Pour charger la base de connaissances dans Pinecone, exécutez :

```bash
cd backend
python scripts/load_knowledge_base.py
```

## Format standardisé

Tous les fichiers doivent suivre ce format Markdown :

```markdown
# Titre Principal

## Contexte
Description du contexte spécifique à votre environnement...

## FAQ

### Section FAQ 1

**Q: Votre question ici?**
R: Votre réponse ici.

### Section FAQ 2

**Q: Autre question?**
R: Autre réponse.

## Procédures (optionnel)

### Procédure 1
1. Étape 1
2. Étape 2
...
```

## Ajout de nouvelles connaissances

1. Créez un nouveau fichier `.md` dans ce dossier
2. Suivez le format standardisé ci-dessus
3. Utilisez des sections (##) pour organiser le contenu
4. Relancez le script `load_knowledge_base.py`

Le script créera automatiquement :
- Un embedding pour le document complet
- Un embedding pour chaque section (##) pour une recherche plus précise

## Structure des embeddings

Le script crée automatiquement :
1. **Un embedding pour le document complet** - Pour une vue d'ensemble
2. **Un embedding par section (##)** - Pour une recherche plus précise et ciblée

Cela permet au bot de :
- Trouver rapidement le document pertinent
- Extraire la section exacte qui répond à la question
- Fournir des réponses plus précises et contextuelles

## Notes importantes

- **Format uniforme** : Tous les fichiers doivent être en Markdown (`.md`)
- **Structure standardisée** : Utilisez des sections (##) pour organiser le contenu
- **Contexte spécifique** : Le contenu doit être adapté à votre environnement (MacBook, Jamf, etc.)
- **Sections recommandées** : Contexte, FAQ, Procédures

## Migration des fichiers JSON

Les anciens fichiers JSON (`.json`) ont été convertis en Markdown (`.md`) pour uniformiser le format. Les fichiers JSON sont maintenant ignorés par le script de chargement et peuvent être supprimés.

