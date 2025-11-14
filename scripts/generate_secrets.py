#!/usr/bin/env python3
"""
Script pour générer des secrets sécurisés pour l'authentification
"""
import secrets
import sys

def generate_secret(length=32):
    """
    Génère un secret sécurisé de longueur spécifiée (en bytes)
    Retourne une chaîne hexadécimale
    """
    return secrets.token_hex(length)

def main():
    print("=" * 50)
    print("Génération de secrets sécurisés")
    print("=" * 50)
    print()
    
    # Générer NEXTAUTH_SECRET (32 bytes = 64 caractères hex)
    nextauth_secret = generate_secret(32)
    print(f"NEXTAUTH_SECRET={nextauth_secret}")
    print()
    
    # Générer SECRET_KEY (32 bytes = 64 caractères hex)
    secret_key = generate_secret(32)
    print(f"SECRET_KEY={secret_key}")
    print()
    
    # Générer un secret pour JWT (32 bytes = 64 caractères hex)
    jwt_secret = generate_secret(32)
    print(f"JWT_SECRET={jwt_secret}")
    print()
    
    print("=" * 50)
    print("Copiez ces valeurs dans vos fichiers .env")
    print("=" * 50)
    print()
    print("⚠️  IMPORTANT: Ne partagez JAMAIS ces secrets !")
    print("⚠️  Stockez-les de manière sécurisée (variables d'environnement, gestionnaires de secrets)")
    print()
    
    # Option pour sauvegarder dans un fichier (non versionné)
    save = input("Voulez-vous sauvegarder ces secrets dans un fichier .secrets.local ? (o/N): ")
    if save.lower() == 'o':
        with open('.secrets.local', 'w') as f:
            f.write(f"NEXTAUTH_SECRET={nextauth_secret}\n")
            f.write(f"SECRET_KEY={secret_key}\n")
            f.write(f"JWT_SECRET={jwt_secret}\n")
        print("✅ Secrets sauvegardés dans .secrets.local")
        print("⚠️  Assurez-vous que ce fichier est dans .gitignore !")

if __name__ == "__main__":
    main()

