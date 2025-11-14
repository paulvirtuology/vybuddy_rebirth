#!/bin/bash
# Script pour générer des secrets sécurisés pour l'authentification

echo "=========================================="
echo "Génération de secrets sécurisés"
echo "=========================================="
echo ""

# Générer NEXTAUTH_SECRET (32 bytes = 64 caractères hex)
NEXTAUTH_SECRET=$(openssl rand -hex 32)
echo "NEXTAUTH_SECRET=$NEXTAUTH_SECRET"
echo ""

# Générer SECRET_KEY (32 bytes = 64 caractères hex)
SECRET_KEY=$(openssl rand -hex 32)
echo "SECRET_KEY=$SECRET_KEY"
echo ""

# Générer un secret pour JWT (32 bytes = 64 caractères hex)
JWT_SECRET=$(openssl rand -hex 32)
echo "JWT_SECRET=$JWT_SECRET"
echo ""

echo "=========================================="
echo "Copiez ces valeurs dans vos fichiers .env"
echo "=========================================="
echo ""
echo "⚠️  IMPORTANT: Ne partagez JAMAIS ces secrets !"
echo "⚠️  Stockez-les de manière sécurisée (variables d'environnement, gestionnaires de secrets)"

