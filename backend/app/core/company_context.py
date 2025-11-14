"""
Contexte de l'entreprise - Informations spécifiques à l'environnement
"""
from typing import Dict, Any

# Contexte spécifique de l'entreprise
COMPANY_CONTEXT = {
    "environment": {
        "devices": {
            "primary": "MacBook Pro uniquement",
            "managed_by": "Jamf (JAMF Pro)",
            "user_permissions": "Les utilisateurs ne sont pas administrateurs de leur MacBook",
            "wifi": {
                "bureau_network": "Réseau WiFi du bureau - UNIQUEMENT pour MacBook",
                "other_devices": "Les téléphones (iPhone/Android) et Windows ne se connectent PAS au WiFi du bureau",
                "connection_method": "Profils de configuration WiFi gérés par Jamf",
                "security_policies": "Politiques de sécurité gérées par Jamf via profils"
            }
        },
        "management": {
            "mdm": "Jamf Pro",
            "profiles": "Profils de configuration WiFi et politiques de sécurité déployés via Jamf",
            "admin_access": "Les utilisateurs n'ont pas les droits administrateur",
            "support_scope": "Support uniquement pour MacBook Pro gérés par Jamf"
        }
    },
    "support_guidelines": {
        "wifi_troubleshooting": [
            "1. Vérifier que l'utilisateur utilise un MacBook (pas iPhone/Android/Windows)",
            "2. Vérifier que le MacBook est bien géré par Jamf",
            "3. Les profils WiFi sont déployés automatiquement via Jamf",
            "4. Si problème de connexion: redémarrer le MacBook complètement",
            "5. Si problème persiste: vérifier les profils Jamf (utilisateur ne peut pas les modifier)",
            "6. Escalade nécessaire si problème de profil Jamf ou configuration réseau"
        ],
        "macos_troubleshooting": [
            "1. Rappeler que l'utilisateur n'est pas administrateur",
            "2. Les installations nécessitent une intervention IT",
            "3. Les paramètres système sont gérés par Jamf",
            "4. L'utilisateur NE PEUT PAS modifier: Réglages système, Login Items, paramètres de sécurité, installations",
            "5. L'utilisateur PEUT: redémarrer, redémarrer Finder, vider le cache Safari, fermer/rouvrir des apps",
            "6. Si problème nécessite modifications système → Proposer IMMÉDIATEMENT un ticket",
            "7. Vérifier les profils de configuration Jamf si problème de permissions"
        ]
    }
}

def get_company_context() -> str:
    """Retourne le contexte de l'entreprise formaté pour les prompts"""
    context = f"""CONTEXTE DE L'ENTREPRISE - INFORMATIONS CRITIQUES:

⚠️ RÈGLE ABSOLUE - À RESPECTER EN TOUTES CIRCONSTANCES:
- TOUS les utilisateurs utilisent UNIQUEMENT des MacBook Pro
- NE PROPOSEZ JAMAIS de solutions pour Windows, iPhone, Android, iPad ou tout autre appareil
- NE MENTIONNEZ JAMAIS Windows, iPhone, Android, iPad dans vos réponses
- TOUTES vos solutions doivent être UNIQUEMENT pour MacBook Pro

ENVIRONNEMENT:
- Tous les utilisateurs utilisent UNIQUEMENT des MacBook Pro
- Les MacBook sont gérés par Jamf (JAMF Pro)
- Les utilisateurs NE SONT PAS administrateurs de leur MacBook
- Les téléphones (iPhone/Android) et ordinateurs Windows NE SE CONNECTENT PAS au WiFi du bureau
- Il n'y a AUCUN utilisateur avec Windows, iPhone ou Android dans cette entreprise pour le support IT

WI-FI DU BUREAU:
- Le réseau WiFi du bureau est UNIQUEMENT pour les MacBook
- La connexion WiFi est gérée par des profils de configuration déployés via Jamf
- Les politiques de sécurité sont gérées par Jamf via profils
- Les utilisateurs ne peuvent pas modifier les paramètres WiFi (gérés par Jamf)

IMPLICATIONS POUR LE SUPPORT:
- ❌ Ne JAMAIS demander si l'utilisateur utilise Windows, iPhone ou Android
- ❌ Ne JAMAIS proposer de solutions pour Windows, iPhone ou Android
- ✅ Toujours supposer que l'utilisateur utilise un MacBook Pro
- ✅ TOUTES les solutions doivent être UNIQUEMENT pour MacBook Pro
- Les problèmes de WiFi sont souvent liés aux profils Jamf
- Les utilisateurs ne peuvent pas modifier les paramètres système (pas d'accès admin)
- Les solutions doivent tenir compte des restrictions Jamf

GUIDELINES DE DIAGNOSTIC:
{chr(10).join(COMPANY_CONTEXT['support_guidelines']['wifi_troubleshooting'])}
"""
    return context

