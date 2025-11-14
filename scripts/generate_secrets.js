#!/usr/bin/env node
/**
 * Script pour générer des secrets sécurisés pour l'authentification
 */
const crypto = require('crypto');
const fs = require('fs');
const readline = require('readline');

function generateSecret(length = 32) {
  /**
   * Génère un secret sécurisé de longueur spécifiée (en bytes)
   * Retourne une chaîne hexadécimale
   */
  return crypto.randomBytes(length).toString('hex');
}

function main() {
  console.log('='.repeat(50));
  console.log('Génération de secrets sécurisés');
  console.log('='.repeat(50));
  console.log();

  // Générer NEXTAUTH_SECRET (32 bytes = 64 caractères hex)
  const nextauthSecret = generateSecret(32);
  console.log(`NEXTAUTH_SECRET=${nextauthSecret}`);
  console.log();

  // Générer SECRET_KEY (32 bytes = 64 caractères hex)
  const secretKey = generateSecret(32);
  console.log(`SECRET_KEY=${secretKey}`);
  console.log();

  // Générer un secret pour JWT (32 bytes = 64 caractères hex)
  const jwtSecret = generateSecret(32);
  console.log(`JWT_SECRET=${jwtSecret}`);
  console.log();

  console.log('='.repeat(50));
  console.log('Copiez ces valeurs dans vos fichiers .env');
  console.log('='.repeat(50));
  console.log();
  console.log('⚠️  IMPORTANT: Ne partagez JAMAIS ces secrets !');
  console.log('⚠️  Stockez-les de manière sécurisée (variables d\'environnement, gestionnaires de secrets)');
  console.log();

  // Option pour sauvegarder dans un fichier (non versionné)
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  rl.question('Voulez-vous sauvegarder ces secrets dans un fichier .secrets.local ? (o/N): ', (answer) => {
    if (answer.toLowerCase() === 'o') {
      const content = `NEXTAUTH_SECRET=${nextauthSecret}\nSECRET_KEY=${secretKey}\nJWT_SECRET=${jwtSecret}\n`;
      fs.writeFileSync('.secrets.local', content);
      console.log('✅ Secrets sauvegardés dans .secrets.local');
      console.log('⚠️  Assurez-vous que ce fichier est dans .gitignore !');
    }
    rl.close();
  });
}

main();

