#!/bin/bash

# Configuration et installation de SymGuard pour serveur ssd-83774
# Ubuntu 22.04.5 LTS - aarch64 - utilisateur kesurof

set -e  # Arrêt en cas d'erreur

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Configuration SymGuard pour serveur ssd-83774${NC}"
echo "=============================================="

# Variables d'environnement détectées
USER_NAME=${USER:-kesurof}
HOME_DIR=${HOME:-/home/$USER_NAME}
SETTINGS_SOURCE=${SETTINGS_SOURCE:-$HOME_DIR/seedbox-compose}
VIRTUAL_ENV_PATH=${VIRTUAL_ENV:-$SETTINGS_SOURCE/venv}

echo -e "${BLUE}📋 Informations détectées:${NC}"
echo "   Utilisateur: $USER_NAME"
echo "   Home: $HOME_DIR"
echo "   Settings: $SETTINGS_SOURCE"
echo "   Virtual Env: $VIRTUAL_ENV_PATH"

# Vérification de l'environnement virtuel
echo -e "\n${BLUE}🐍 Vérification environnement Python...${NC}"

if [ -d "$VIRTUAL_ENV_PATH" ]; then
    echo -e "${GREEN}✅ Environnement virtuel trouvé: $VIRTUAL_ENV_PATH${NC}"
    
    # Activation de l'environnement virtuel
    source "$VIRTUAL_ENV_PATH/bin/activate"
    
    echo "   Python: $(python3 --version)"
    echo "   Pip: $(pip --version | cut -d' ' -f1-2)"
    
else
    echo -e "${RED}❌ Environnement virtuel non trouvé${NC}"
    echo -e "${YELLOW}⚠️ Création d'un nouvel environnement virtuel...${NC}"
    
    python3 -m venv "$VIRTUAL_ENV_PATH"
    source "$VIRTUAL_ENV_PATH/bin/activate"
    pip install --upgrade pip
fi

# Installation des dépendances
echo -e "\n${BLUE}📦 Installation des dépendances...${NC}"

if [ -f "requirements.txt" ]; then
    echo "Installation depuis requirements.txt..."
    pip install -r requirements.txt
else
    echo "Installation manuelle des dépendances essentielles..."
    pip install requests urllib3 psutil
fi

# Vérification de ffprobe
echo -e "\n${BLUE}🔧 Vérification ffprobe...${NC}"

if command -v ffprobe &> /dev/null; then
    FFPROBE_VERSION=$(ffprobe -version 2>/dev/null | head -n1 | awk '{print $3}')
    echo -e "${GREEN}✅ ffprobe trouvé: $FFPROBE_VERSION${NC}"
else
    echo -e "${YELLOW}⚠️ ffprobe non trouvé${NC}"
    echo "Pour installer ffmpeg/ffprobe:"
    echo "   sudo apt update && sudo apt install ffmpeg"
fi

# Vérification de Docker
echo -e "\n${BLUE}🐳 Vérification Docker...${NC}"

if command -v docker &> /dev/null; then
    if docker ps &> /dev/null; then
        echo -e "${GREEN}✅ Docker accessible${NC}"
        
        # Liste des conteneurs média
        echo "Conteneurs média détectés:"
        for container in sonarr radarr bazarr prowlarr; do
            if docker ps --filter name=$container --format "{{.Names}}" | grep -q $container; then
                STATUS=$(docker ps --filter name=$container --format "{{.Status}}")
                echo -e "   ${GREEN}✅ $container${NC}: $STATUS"
            else
                echo -e "   ${YELLOW}⚠️ $container${NC}: non trouvé"
            fi
        done
    else
        echo -e "${YELLOW}⚠️ Docker installé mais non accessible (permissions?)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ Docker non trouvé${NC}"
fi

# Création du lien symbolique pour faciliter l'exécution
echo -e "\n${BLUE}🔗 Configuration raccourcis...${NC}"

# Rendre le script exécutable
chmod +x script.py

# Créer un alias dans .bashrc si pas déjà présent
BASHRC_FILE="$HOME_DIR/.bashrc"
ALIAS_LINE="alias symguard='cd $(pwd) && python3 script.py'"

if [ -f "$BASHRC_FILE" ]; then
    if ! grep -q "alias symguard=" "$BASHRC_FILE"; then
        echo "" >> "$BASHRC_FILE"
        echo "# SymGuard alias" >> "$BASHRC_FILE"
        echo "$ALIAS_LINE" >> "$BASHRC_FILE"
        echo -e "${GREEN}✅ Alias 'symguard' ajouté à .bashrc${NC}"
    else
        echo -e "${YELLOW}⚠️ Alias 'symguard' déjà présent${NC}"
    fi
fi

# Test d'exécution rapide
echo -e "\n${BLUE}🧪 Test d'exécution...${NC}"

if python3 script.py --help &> /dev/null; then
    echo -e "${GREEN}✅ Script fonctionnel${NC}"
else
    echo -e "${RED}❌ Erreur lors du test${NC}"
fi

# Vérification des permissions sur /home/kesurof/Medias
MEDIA_DIR="$HOME_DIR/Medias"
echo -e "\n${BLUE}📁 Vérification répertoire média...${NC}"

if [ -d "$MEDIA_DIR" ]; then
    if [ -r "$MEDIA_DIR" ]; then
        SYMLINK_COUNT=$(find "$MEDIA_DIR" -type l 2>/dev/null | wc -l)
        echo -e "${GREEN}✅ $MEDIA_DIR accessible${NC}"
        echo "   Liens symboliques détectés: $SYMLINK_COUNT"
    else
        echo -e "${RED}❌ $MEDIA_DIR non accessible en lecture${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ $MEDIA_DIR non trouvé${NC}"
fi

# Résumé final
echo -e "\n${GREEN}🎉 CONFIGURATION TERMINÉE${NC}"
echo "=============================================="
echo -e "${BLUE}Pour utiliser SymGuard:${NC}"
echo "1. Source votre .bashrc: source ~/.bashrc"
echo "2. Utilisez la commande: symguard"
echo "3. Ou directement: python3 script.py"
echo ""
echo -e "${BLUE}Options utiles:${NC}"
echo "   --dry-run     : Mode simulation"
echo "   --real        : Mode réel (suppression)"
echo "   --quick       : Scan basique uniquement"
echo "   -j 4          : 4 workers parallèles"
echo ""
echo -e "${BLUE}Logs système:${NC}"
echo "   Logs: $HOME_DIR/symlink_maintenance.log"
echo "   Rapports: ./symlink_report_*.json"
echo "   Suppressions: ./deleted_files_*.log"

echo -e "\n${GREEN}✅ Prêt à analyser vos liens symboliques !${NC}"
