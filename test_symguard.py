#!/usr/bin/env python3

"""
Script de test pour SymGuard
Vérifie que les fonctions principales fonctionnent sans erreur
"""

import sys
import os

# Ajouter le répertoire du script au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test des imports principaux"""
    print("🧪 Test des imports...")
    
    try:
        # Test imports de base
        import script
        print("✅ Import du module principal réussi")
        
        # Test de la classe principale
        checker = script.AdvancedSymlinkChecker(max_workers=1)
        print("✅ Création de l'instance réussie")
        
        # Test de la version
        print(f"✅ Version détectée: {script.SCRIPT_VERSION}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur d'import: {e}")
        return False

def test_config():
    """Test des fonctions de configuration"""
    print("\n🧪 Test des fonctions de configuration...")
    
    try:
        import script
        checker = script.AdvancedSymlinkChecker(max_workers=1)
        
        # Test de chargement de config
        config = checker.load_media_config()
        print("✅ Chargement de configuration réussi")
        
        # Test de vérification des ressources (peut échouer si psutil absent)
        resources = checker.check_system_resources()
        print("✅ Vérification des ressources réussie")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur de configuration: {e}")
        return False

def test_help():
    """Test de l'aide du script"""
    print("\n🧪 Test de l'aide...")
    
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, 'script.py', '--help'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Aide affichée correctement")
            return True
        else:
            print(f"❌ Erreur dans l'aide: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test d'aide: {e}")
        return False

def main():
    """Fonction principale de test"""
    print("🚀 Tests de validation SymGuard")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config,
        test_help
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Résultats: {passed}/{total} tests réussis")
    
    if passed == total:
        print("🎉 Tous les tests sont passés!")
        print("\n💡 Le script semble fonctionnel. Vous pouvez l'utiliser avec:")
        print("   python3 script.py --help")
        print("   python3 script.py --no-media-scan")
        return 0
    else:
        print("⚠️ Certains tests ont échoué")
        print("\n💡 Essayez d'installer les dépendances:")
        print("   ./install-deps.sh")
        return 1

if __name__ == "__main__":
    sys.exit(main())
