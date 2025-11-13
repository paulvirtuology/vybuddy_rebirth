#!/usr/bin/env python3
"""
Script de test des health checks
Peut être exécuté indépendamment pour tester les connexions
"""
import asyncio
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.health_check import HealthChecker


async def main():
    """Test des health checks"""
    print("Démarrage des tests de santé des services...\n")
    
    checker = HealthChecker()
    results = await checker.check_all()
    all_ok = checker.print_results(results)
    
    # Code de sortie
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    asyncio.run(main())

