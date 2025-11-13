# MacOS - Support MacBook géré par Jamf

## Contexte
- Tous les utilisateurs utilisent **uniquement des MacBook Pro**
- Les MacBook sont gérés par **Jamf (JAMF Pro)**
- Les utilisateurs **ne sont pas administrateurs** de leur MacBook
- Les paramètres système sont gérés par Jamf via profils

## Restrictions utilisateur
- Les utilisateurs ne peuvent pas installer de logiciels nécessitant des droits administrateur
- Les paramètres système sont verrouillés par Jamf
- Les profils de configuration sont déployés automatiquement

## Support MacOS - Guidelines

### Installations de logiciels
- Si l'utilisateur demande d'installer un logiciel → **Créer un ticket**
- Les installations nécessitent une intervention IT
- L'utilisateur ne peut pas installer via Terminal avec sudo

### Paramètres système
- Si problème de permissions → Vérifier les profils Jamf
- L'utilisateur ne peut pas modifier les paramètres système
- Escalade nécessaire si problème de configuration

### Problèmes courants
1. **Permissions refusées** → Normal, utilisateur pas admin → Créer ticket
2. **Paramètres verrouillés** → Géré par Jamf → Créer ticket
3. **Profil manquant** → Problème Jamf → Créer ticket

## Points importants
- Toujours rappeler que l'utilisateur n'est pas administrateur
- Les modifications système nécessitent une intervention IT
- Vérifier les profils Jamf si problème de configuration
- Escalade rapide si problème de permissions ou profils

