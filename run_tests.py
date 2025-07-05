#!/usr/bin/env python3
# run_tests.py - Script pour exécuter les tests

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path

def run_command(command, description=""):
    """Exécuter une commande et afficher le résultat."""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    
    start_time = time.time()
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    duration = time.time() - start_time
    
    if result.returncode == 0:
        print(f"✅ {description} - Réussi ({duration:.2f}s)")
        if result.stdout:
            print(result.stdout)
    else:
        print(f"❌ {description} - Échoué ({duration:.2f}s)")
        if result.stderr:
            print("STDERR:", result.stderr)
        if result.stdout:
            print("STDOUT:", result.stdout)
    
    return result.returncode == 0

def run_unit_tests():
    """Exécuter les tests unitaires."""
    return run_command(
        "python -m pytest tests/unit/ -v --tb=short -m unit",
        "Tests unitaires"
    )

def run_integration_tests():
    """Exécuter les tests d'intégration."""
    return run_command(
        "python -m pytest tests/integration/ -v --tb=short -m integration",
        "Tests d'intégration"
    )

def run_e2e_tests():
    """Exécuter les tests end-to-end."""
    return run_command(
        "python -m pytest tests/e2e/ -v --tb=short -m e2e",
        "Tests end-to-end"
    )

def run_performance_tests():
    """Exécuter les tests de performance."""
    return run_command(
        "python -m pytest tests/performance/ -v --tb=short -m slow",
        "Tests de performance"
    )

def run_coverage():
    """Exécuter les tests avec couverture de code."""
    return run_command(
        "python -m pytest --cov=backend --cov-report=html --cov-report=term-missing tests/",
        "Tests avec couverture de code"
    )

def run_linting():
    """Exécuter le linting du code."""
    commands = [
        ("flake8 backend/ --max-line-length=100 --extend-ignore=E203,W503", "Flake8 linting"),
        ("black --check backend/", "Black formatting check"),
        ("isort --check-only backend/", "Import sorting check"),
        ("mypy backend/ --ignore-missing-imports", "Type checking")
    ]
    
    all_passed = True
    for command, description in commands:
        if not run_command(command, description):
            all_passed = False
    
    return all_passed

def run_security_tests():
    """Exécuter les tests de sécurité."""
    commands = [
        ("bandit -r backend/ -f json -o security_report.json", "Bandit security scan"),
        ("safety check --json --output safety_report.json", "Safety dependency check")
    ]
    
    all_passed = True
    for command, description in commands:
        if not run_command(command, description):
            all_passed = False
    
    return all_passed

def setup_test_environment():
    """Configurer l'environnement de test."""
    print("🔧 Configuration de l'environnement de test...")
    
    # Variables d'environnement pour les tests
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['REDIS_URL'] = 'redis://localhost:6379/15'  # DB de test
    os.environ['HERE_API_KEY'] = 'test_api_key'
    
    # Créer les dossiers nécessaires
    Path('logs').mkdir(exist_ok=True)
    Path('coverage_html').mkdir(exist_ok=True)
    
    print("✅ Environnement de test configuré")

def cleanup_test_environment():
    """Nettoyer après les tests."""
    print("🧹 Nettoyage de l'environnement de test...")
    
    # Supprimer les fichiers temporaires
    temp_files = [
        'security_report.json',
        'safety_report.json',
        '.coverage'
    ]
    
    for file_path in temp_files:
        if os.path.exists(file_path):
            os.remove(file_path)
    
    print("✅ Nettoyage terminé")

def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Exécuter les tests Smart Route")
    parser.add_argument('--unit', action='store_true', help='Exécuter les tests unitaires')
    parser.add_argument('--integration', action='store_true', help='Exécuter les tests d\'intégration')
    parser.add_argument('--e2e', action='store_true', help='Exécuter les tests end-to-end')
    parser.add_argument('--performance', action='store_true', help='Exécuter les tests de performance')
    parser.add_argument('--coverage', action='store_true', help='Exécuter avec couverture de code')
    parser.add_argument('--lint', action='store_true', help='Exécuter le linting')
    parser.add_argument('--security', action='store_true', help='Exécuter les tests de sécurité')
    parser.add_argument('--all', action='store_true', help='Exécuter tous les tests')
    parser.add_argument('--quick', action='store_true', help='Tests rapides (unit + integration)')
    parser.add_argument('--ci', action='store_true', help='Mode CI/CD (tous les tests sauf e2e)')
    
    args = parser.parse_args()
    
    # Configuration
    setup_test_environment()
    
    try:
        success = True
        start_time = time.time()
        
        # Déterminer quels tests exécuter
        if args.all:
            tests_to_run = ['unit', 'integration', 'e2e', 'performance', 'lint', 'security', 'coverage']
        elif args.quick:
            tests_to_run = ['unit', 'integration']
        elif args.ci:
            tests_to_run = ['unit', 'integration', 'performance', 'lint', 'security', 'coverage']
        else:
            tests_to_run = []
            if args.unit: tests_to_run.append('unit')
            if args.integration: tests_to_run.append('integration')
            if args.e2e: tests_to_run.append('e2e')
            if args.performance: tests_to_run.append('performance')
            if args.lint: tests_to_run.append('lint')
            if args.security: tests_to_run.append('security')
            if args.coverage: tests_to_run.append('coverage')
        
        # Si aucun test spécifié, exécuter les tests rapides
        if not tests_to_run:
            tests_to_run = ['unit', 'integration']
        
        # Exécuter les tests
        test_functions = {
            'unit': run_unit_tests,
            'integration': run_integration_tests,
            'e2e': run_e2e_tests,
            'performance': run_performance_tests,
            'lint': run_linting,
            'security': run_security_tests,
            'coverage': run_coverage
        }
        
        for test_type in tests_to_run:
            if test_type in test_functions:
                if not test_functions[test_type]():
                    success = False
        
        # Résumé
        total_time = time.time() - start_time
        print(f"\n{'='*60}")
        if success:
            print(f"🎉 Tous les tests ont réussi ! ({total_time:.2f}s)")
        else:
            print(f"💥 Certains tests ont échoué ! ({total_time:.2f}s)")
        print(f"{'='*60}")
        
        return 0 if success else 1
        
    finally:
        cleanup_test_environment()

if __name__ == '__main__':
    sys.exit(main())