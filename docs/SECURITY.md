# Guide de Sécurité - Génération de Secrets

## Méthodes pour générer des secrets sécurisés

### Méthode 1 : Script Shell (OpenSSL) - Recommandé

```bash
# Exécuter le script
./scripts/generate_secrets.sh

# Ou directement avec OpenSSL
openssl rand -hex 32
```

**Avantages :**
- Disponible sur la plupart des systèmes Unix/Linux/Mac
- Utilise le générateur cryptographique du système
- Très rapide

### Méthode 2 : Script Python

```bash
# Exécuter le script
python3 scripts/generate_secrets.py

# Ou directement dans Python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Avantages :**
- Utilise le module `secrets` de Python (cryptographiquement sécurisé)
- Disponible si Python est installé
- Peut sauvegarder automatiquement dans un fichier

### Méthode 3 : Script Node.js

```bash
# Exécuter le script
node scripts/generate_secrets.js

# Ou directement avec Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

**Avantages :**
- Utilise le module `crypto` de Node.js
- Disponible si Node.js est installé
- Peut sauvegarder automatiquement dans un fichier

### Méthode 4 : En ligne de commande (une seule valeur)

**Linux/Mac :**
```bash
openssl rand -hex 32
```

**Windows (PowerShell) :**
```powershell
-join ((48..57) + (97..102) | Get-Random -Count 64 | % {[char]$_})
```

**Python :**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Node.js :**
```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

## Longueur recommandée

- **Minimum :** 32 bytes (64 caractères hex) pour les secrets JWT
- **Recommandé :** 32-64 bytes (64-128 caractères hex)
- **Maximum :** Pas de limite pratique, mais 64 bytes est généralement suffisant

## Bonnes pratiques

### ✅ À FAIRE

1. **Utiliser des secrets différents pour chaque environnement**
   - Développement
   - Staging
   - Production

2. **Générer des secrets uniques pour chaque application**
   - Ne pas réutiliser le même secret entre applications

3. **Stockage sécurisé**
   - Variables d'environnement (`.env` non versionné)
   - Gestionnaires de secrets (AWS Secrets Manager, HashiCorp Vault, etc.)
   - Services cloud (Vercel, Railway, etc.) avec variables d'environnement chiffrées

4. **Rotation régulière**
   - Changer les secrets tous les 6-12 mois
   - Planifier la rotation pour éviter les interruptions

5. **Vérifier que les secrets ne sont pas dans Git**
   ```bash
   # Vérifier dans l'historique Git
   git log --all --full-history -- .env
   ```

### ❌ À NE PAS FAIRE

1. **Ne jamais commiter les secrets dans Git**
   - Vérifier `.gitignore` contient `.env*`
   - Utiliser `git-secrets` ou `truffleHog` pour scanner

2. **Ne pas utiliser de secrets faibles**
   - Éviter : `secret123`, `password`, `changeme`
   - Éviter : dates, noms, mots du dictionnaire

3. **Ne pas partager les secrets par email/Slack**
   - Utiliser des canaux sécurisés
   - Utiliser des gestionnaires de secrets avec partage contrôlé

4. **Ne pas hardcoder les secrets dans le code**
   - Toujours utiliser des variables d'environnement

5. **Ne pas réutiliser les secrets entre environnements**
   - Chaque environnement doit avoir ses propres secrets

## Configuration pour VyBuddy

### Frontend (.env.local)

```env
NEXTAUTH_SECRET=<généré avec 32 bytes>
NEXTAUTH_URL=http://localhost:3000
GOOGLE_CLIENT_ID=<depuis Google Cloud Console>
GOOGLE_CLIENT_SECRET=<depuis Google Cloud Console>
NEXT_PUBLIC_SUPABASE_URL=<depuis Supabase>
SUPABASE_SERVICE_ROLE_KEY=<depuis Supabase>
```

### Backend (.env)

```env
NEXTAUTH_SECRET=<même valeur que frontend>
SECRET_KEY=<généré avec 32 bytes, peut être différent>
# ... autres variables
```

**Note :** `NEXTAUTH_SECRET` doit être identique entre frontend et backend pour que les tokens JWT soient valides.

## Vérification de la sécurité

### Vérifier la force d'un secret

Un secret de 32 bytes (64 caractères hex) a :
- **2^256** combinaisons possibles
- **77 chiffres décimaux** d'entropie
- **Considéré comme sécurisé** pour les applications modernes

### Outils de vérification

```bash
# Vérifier l'entropie (si ent est installé)
echo "votre_secret" | ent

# Vérifier la longueur
echo -n "votre_secret" | wc -c
```

## En cas de compromission

Si un secret est compromis :

1. **Générer immédiatement un nouveau secret**
2. **Mettre à jour toutes les instances** (dev, staging, prod)
3. **Forcer la déconnexion de tous les utilisateurs** (invalider les sessions)
4. **Analyser les logs** pour détecter des accès non autorisés
5. **Notifier les utilisateurs** si nécessaire

## Ressources

- [OWASP - Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [NextAuth.js - Security](https://next-auth.js.org/configuration/options#secret)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)

