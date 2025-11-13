# WiFi MacBook - Connexion au réseau du bureau

## Contexte
- Tous les utilisateurs utilisent **uniquement des MacBook Pro**
- Les MacBook sont gérés par **Jamf (JAMF Pro)**
- Les utilisateurs **ne sont pas administrateurs** de leur MacBook
- Le réseau WiFi du bureau est **uniquement pour les MacBook** (pas pour iPhone, Android ou Windows)

## Configuration WiFi
- La connexion WiFi est gérée par des **profils de configuration déployés via Jamf**
- Les politiques de sécurité sont gérées par Jamf via profils
- Les utilisateurs ne peuvent pas modifier les paramètres WiFi (gérés par Jamf)

## Diagnostic WiFi - Étapes

### Étape 1: Vérification de base
1. Vérifier que l'utilisateur utilise bien un MacBook Pro
2. Vérifier que le MacBook est bien géré par Jamf
3. Demander si le réseau WiFi du bureau apparaît dans la liste des réseaux disponibles

### Étape 2: Solutions simples
1. **Redémarrer complètement le MacBook** (souvent résout les problèmes de profil Jamf)
   - Éteindre complètement, attendre quelques secondes, puis rallumer
2. Vérifier l'icône WiFi en haut à gauche de l'écran
3. Vérifier si le réseau apparaît dans la liste

### Étape 3: Si le problème persiste
- Le problème est probablement lié aux **profils Jamf**
- L'utilisateur ne peut pas modifier les profils (pas d'accès admin)
- **Créer un ticket** pour intervention IT (vérification des profils Jamf)

## Points importants
- Ne jamais demander quel type d'appareil (c'est toujours un MacBook)
- Ne pas proposer de modifications système complexes (utilisateur pas admin)
- Les profils sont gérés par Jamf, pas par l'utilisateur
- Escalade nécessaire si problème de profil ou configuration réseau

