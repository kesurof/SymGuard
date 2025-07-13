#!/bin/bash

# Script de vérification rapide pour SymGuard
# Vérifie si les dépendances sont installées et disponibles

echo "🔍 Vérification rapide SymGuard v2.0.2"
echo "========================================"

# Vérifier Python 3
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version 2>&1)
    echo "✅ Python: $python_version"
else
    echo "❌ Python 3 non trouvé"
    exit 1
fi

# Vérifier les modules Python
echo ""
echo "📦 Vérification des modules Python:"

modules=("requests" "urllib3" "psutil")
missing_modules=()

for module in "${modules[@]}"; do
    if python3 -c "import $module" 2>/dev/null; then
        echo "✅ $module: disponible"
    else
        echo "⚠️ $module: manquant (optionnel)"
        missing_modules+=("$module")
    fi
done

# Vérifier le script principal
echo ""
echo "🧪 Vérification du script principal:"

if [ -f "script.py" ]; then
    echo "✅ script.py: trouvé"
    
    # Test d'import basique
    if python3 -c "import script" 2>/dev/null; then
        echo "✅ Import du module: réussi"
    else
        echo "⚠️ Import du module: problème détecté"
    fi
    
    # Test de l'aide
    if timeout 5 python3 script.py --version &>/dev/null; then
        echo "✅ Exécution basique: réussie"
    else
        echo "⚠️ Exécution basique: problème détecté"
    fi
else
    echo "❌ script.py: non trouvé"
    exit 1
fi

# Résumé
echo ""
echo "📊 Résumé:"
if [ ${#missing_modules[@]} -eq 0 ]; then
    echo "🎉 Toutes les dépendances sont installées!"
    echo ""
    echo "🚀 Commandes suggérées:"
    echo "   python3 script.py --help"
    echo "   python3 script.py --no-media-scan"
    echo "   python3 script.py --create-config"
else
    echo "⚠️ ${#missing_modules[@]} modules optionnels manquants"
    echo ""
    echo "💡 Pour installer les dépendances manquantes:"
    echo "   ./install-deps.sh"
    echo ""
    echo "🚀 Le script peut fonctionner avec des fonctionnalités limitées:"
    echo "   python3 script.py --no-media-scan --no-update-check"
fi
