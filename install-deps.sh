#!/bin/bash

# Script d'installation des dépendances pour SymGuard
# Version 2.0.2

echo "🔧 Installation des dépendances SymGuard..."

# Vérifier si Python3 est installé
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    exit 1
fi

# Vérifier si pip3 est installé
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 n'est pas installé"
    echo "💡 Installez-le avec: sudo apt update && sudo apt install python3-pip"
    exit 1
fi

# Installer les dépendances
echo "📦 Installation des packages Python..."

# Vérifier si le fichier requirements.txt existe
if [ ! -f "requirements.txt" ]; then
    echo "❌ Fichier requirements.txt non trouvé"
    echo "💡 Assurez-vous d'être dans le répertoire SymGuard"
    exit 1
fi

pip3 install --user -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dépendances installées avec succès"
    echo ""
    echo "🚀 Vous pouvez maintenant utiliser SymGuard:"
    echo "   python3 script.py --help"
    echo "   python3 script.py --version"
    echo ""
    echo "💡 Pour ignorer les scans des serveurs média:"
    echo "   python3 script.py --no-media-scan"
    echo ""
    echo "🔧 Pour configurer les serveurs média:"
    echo "   python3 script.py --config"
else
    echo "❌ Erreur lors de l'installation des dépendances"
    exit 1
fi
