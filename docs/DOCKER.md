# Guide Docker - VyBuddy Rebirth Backend

Ce guide explique comment utiliser Docker pour déployer le backend VyBuddy Rebirth.

## Prérequis

- Docker installé (version 20.10+)
- Docker Compose installé (version 2.0+)
- Fichier `.env` configuré avec toutes les variables nécessaires

## Structure

- `Dockerfile` : Image Docker pour le backend
- `docker-compose.yml` : Configuration pour la production
- `docker-compose.dev.yml` : Configuration pour le développement
- `.dockerignore` : Fichiers à exclure du build Docker

## Utilisation

### Production

1. **Construire et démarrer les services**

```bash
docker-compose up -d
```

2. **Voir les logs**

```bash
docker-compose logs -f backend
```

3. **Arrêter les services**

```bash
docker-compose down
```

4. **Reconstruire l'image**

```bash
docker-compose build --no-cache
docker-compose up -d
```

### Développement

Pour le développement avec hot-reload :

```bash
docker-compose -f docker-compose.dev.yml up
```

Le code sera monté en volume, permettant les modifications en temps réel.

## Commandes Utiles

### Vérifier les conteneurs

```bash
docker-compose ps
```

### Accéder au shell du conteneur

```bash
docker-compose exec backend bash
```

### Voir les logs en temps réel

```bash
docker-compose logs -f backend
```

### Redémarrer un service

```bash
docker-compose restart backend
```

### Nettoyer

```bash
# Arrêter et supprimer les conteneurs
docker-compose down

# Supprimer aussi les volumes
docker-compose down -v

# Supprimer les images
docker-compose down --rmi all
```

## Configuration

### Variables d'environnement

Le fichier `.env` est automatiquement chargé par docker-compose. Assurez-vous qu'il contient toutes les variables nécessaires :

- API Keys (OpenAI, Anthropic, Google)
- Supabase
- Redis Cloud
- Pinecone
- Odoo

### Ports

Par défaut, le backend est accessible sur le port `8000`. Pour changer le port :

```yaml
ports:
  - "VOTRE_PORT:8000"
```

### Volumes

En production, seul le volume `logs` est monté. En développement, le code source est aussi monté pour le hot-reload.

## Healthcheck

Le conteneur inclut un healthcheck qui vérifie `/health` toutes les 30 secondes. Vous pouvez vérifier le statut avec :

```bash
docker-compose ps
```

## Optimisations

### Build multi-stage

Le Dockerfile utilise un build multi-stage pour réduire la taille de l'image finale :
- Stage 1 : Installation des dépendances
- Stage 2 : Image runtime minimale

### Utilisateur non-root

Le conteneur s'exécute avec un utilisateur non-root (`appuser`) pour la sécurité.

### Cache des layers

Les dépendances sont installées dans une étape séparée pour optimiser le cache Docker.

## Dépannage

### Le conteneur ne démarre pas

1. Vérifiez les logs : `docker-compose logs backend`
2. Vérifiez que le fichier `.env` existe et est correct
3. Vérifiez que le port 8000 n'est pas déjà utilisé

### Erreurs de connexion aux services externes

1. Vérifiez que les variables d'environnement sont correctes
2. Vérifiez que les URLs et clés API sont valides
3. Vérifiez la connectivité réseau depuis le conteneur

### Rebuild nécessaire

Si vous modifiez les dépendances (`requirements.txt`), reconstruisez l'image :

```bash
docker-compose build --no-cache backend
docker-compose up -d
```

## Déploiement en Production

### Recommandations

1. **Utilisez des secrets Docker** pour les clés API sensibles
2. **Configurez un reverse proxy** (nginx, traefik) devant le conteneur
3. **Activez HTTPS** avec Let's Encrypt
4. **Configurez la rotation des logs**
5. **Utilisez un orchestrateur** (Kubernetes, Docker Swarm) pour la haute disponibilité

### Exemple avec secrets Docker

```yaml
services:
  backend:
    secrets:
      - openai_api_key
      - anthropic_api_key
    environment:
      - OPENAI_API_KEY_FILE=/run/secrets/openai_api_key
```

Créez les secrets avec :
```bash
echo "your-key" | docker secret create openai_api_key -
```

## Intégration CI/CD

### GitHub Actions

```yaml
- name: Build and push Docker image
  run: |
    docker build -t vybuddy-backend:${{ github.sha }} .
    docker push vybuddy-backend:${{ github.sha }}
```

### GitLab CI

```yaml
build:
  script:
    - docker build -t vybuddy-backend:$CI_COMMIT_SHA .
    - docker push vybuddy-backend:$CI_COMMIT_SHA
```

## Support

Pour plus d'informations, consultez :
- [Documentation Docker](https://docs.docker.com/)
- [Documentation Docker Compose](https://docs.docker.com/compose/)

