#!/bin/bash

# Configuration et installation de SymGuard pour serveurs Linux
# Installation dans /home/kesurof/scripts/ avec gestion des mises à jour
# Compatible Ubuntu 20.04+ / Debian 10+ - x86_64 / aarch64

set -e  # Arrêt en cas d'erreur

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_VERSION="2.0.1"
INSTALL_DIR="/home/kesurof/scripts"
SCRIPT_NAME="symguard"
REPO_URL="https://github.com/kesurof/SymGuard.git"

echo -e "${BLUE}🚀 SymGuard v${SCRIPT_VERSION} - Installation et mise à jour${NC}"
echo "=============================================="

# Variables d'environnement détectées
USER_NAME=${USER:-$(whoami)}
HOME_DIR=${HOME:-/home/$USER_NAME}
SETTINGS_SOURCE=${SETTINGS_SOURCE:-$HOME_DIR/seedbox-compose}
VIRTUAL_ENV_PATH=${VIRTUAL_ENV:-$SETTINGS_SOURCE/venv}

echo -e "${BLUE}📋 Informations détectées:${NC}"
echo "   Utilisateur: $USER_NAME"
echo "   Home: $HOME_DIR"
echo "   Répertoire d'installation: $INSTALL_DIR"
echo "   Settings: $SETTINGS_SOURCE"
echo "   Virtual Env: $VIRTUAL_ENV_PATH"

# Création du répertoire d'installation
echo -e "\n${BLUE}📁 Préparation répertoire d'installation...${NC}"
mkdir -p "$INSTALL_DIR"

# Fonction de mise à jour depuis GitHub
update_from_github() {
    echo -e "${BLUE}📥 Téléchargement depuis GitHub...${NC}"
    
    if [ -d "$INSTALL_DIR/SymGuard" ]; then
        echo -e "${YELLOW}⚠️ Installation existante détectée${NC}"
        echo -e "${BLUE}🔄 Mise à jour en cours...${NC}"
        cd "$INSTALL_DIR/SymGuard"
        
        # Sauvegarder les logs et configs locaux
        if [ -f "symlink_maintenance.log" ]; then
            cp symlink_maintenance.log ../symlink_maintenance.log.backup
        fi
        
        # Mise à jour
        git fetch origin
        git reset --hard origin/main
        git clean -fd
    else
        echo -e "${BLUE}📦 Première installation...${NC}"
        cd "$INSTALL_DIR"
        git clone "$REPO_URL"
    fi
    
    cd "$INSTALL_DIR/SymGuard"
}

# Si nous sommes dans le repo cloné, copier vers le répertoire final
if [ -f "script.py" ] && [ "$(pwd)" != "$INSTALL_DIR/SymGuard" ]; then
    echo -e "${BLUE}📋 Copie depuis le répertoire actuel...${NC}"
    mkdir -p "$INSTALL_DIR/SymGuard"
    cp -r . "$INSTALL_DIR/SymGuard/"
    cd "$INSTALL_DIR/SymGuard"
else
    update_from_github
fi

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

# Rendre le script exécutable
echo -e "\n${BLUE}🔗 Configuration exécutable...${NC}"
chmod +x script.py

# Créer un script wrapper dans /usr/local/bin pour accès global
echo -e "\n${BLUE}🌐 Configuration accès global...${NC}"

WRAPPER_SCRIPT="/usr/local/bin/$SCRIPT_NAME"
cat > "/tmp/$SCRIPT_NAME" << EOF
#!/bin/bash
# SymGuard Wrapper Script - v$SCRIPT_VERSION
# Installation: $INSTALL_DIR/SymGuard

# Activation de l'environnement virtuel
source "$VIRTUAL_ENV_PATH/bin/activate"

# Exécution du script principal
cd "$INSTALL_DIR/SymGuard"
exec python3 script.py "\$@"
EOF

chmod +x "/tmp/$SCRIPT_NAME"

# Installer le wrapper (nécessite sudo)
if sudo cp "/tmp/$SCRIPT_NAME" "$WRAPPER_SCRIPT" 2>/dev/null; then
    echo -e "${GREEN}✅ Commande globale '$SCRIPT_NAME' installée${NC}"
else
    echo -e "${YELLOW}⚠️ Installation globale échouée (sudo requis)${NC}"
    echo -e "${BLUE}ℹ️ Installation de l'alias local...${NC}"
    
    # Créer un alias dans .bashrc si pas déjà présent
    BASHRC_FILE="$HOME_DIR/.bashrc"
    ALIAS_LINE="alias $SCRIPT_NAME='cd $INSTALL_DIR/SymGuard && source $VIRTUAL_ENV_PATH/bin/activate && python3 script.py'"
    
    if [ -f "$BASHRC_FILE" ]; then
        if ! grep -q "alias $SCRIPT_NAME=" "$BASHRC_FILE"; then
            echo "" >> "$BASHRC_FILE"
            echo "# SymGuard alias - v$SCRIPT_VERSION" >> "$BASHRC_FILE"
            echo "$ALIAS_LINE" >> "$BASHRC_FILE"
            echo -e "${GREEN}✅ Alias '$SCRIPT_NAME' ajouté à .bashrc${NC}"
        else
            # Mettre à jour l'alias existant
            sed -i "s|alias $SCRIPT_NAME=.*|$ALIAS_LINE|" "$BASHRC_FILE"
            echo -e "${GREEN}✅ Alias '$SCRIPT_NAME' mis à jour${NC}"
        fi
    fi
fi

# Créer un script de mise à jour
UPDATE_SCRIPT="$INSTALL_DIR/update-symguard.sh"
cat > "$UPDATE_SCRIPT" << EOF
#!/bin/bash
# Script de mise à jour SymGuard
echo "🔄 Mise à jour SymGuard..."
cd "$INSTALL_DIR/SymGuard"
git fetch origin
git reset --hard origin/main
git clean -fd
echo "✅ Mise à jour terminée"
echo "ℹ️ Relancez la configuration: $INSTALL_DIR/SymGuard/setup.sh"
EOF

chmod +x "$UPDATE_SCRIPT"
echo -e "${GREEN}✅ Script de mise à jour créé: $UPDATE_SCRIPT${NC}"

# Test d'exécution
echo -e "\n${BLUE}🧪 Test d'exécution...${NC}"

if python3 script.py --help &> /dev/null; then
    echo -e "${GREEN}✅ Script fonctionnel${NC}"
else
    echo -e "${RED}❌ Erreur lors du test${NC}"
    echo "Vérifiez les logs pour plus de détails"
fi

# Vérification du répertoire média par défaut
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
echo -e "\n${GREEN}🎉 INSTALLATION TERMINÉE${NC}"
echo "=============================================="
echo -e "${BLUE}📍 Installation:${NC} $INSTALL_DIR/SymGuard"
echo -e "${BLUE}📝 Version:${NC} $SCRIPT_VERSION"
echo ""
echo -e "${BLUE}🚀 Pour utiliser SymGuard:${NC}"
if [ -x "$WRAPPER_SCRIPT" ]; then
    echo "   $SCRIPT_NAME                    # Commande globale"
else
    echo "   source ~/.bashrc               # Recharger le shell"
    echo "   $SCRIPT_NAME                   # Alias local"
fi
echo "   cd $INSTALL_DIR/SymGuard && python3 script.py  # Direct"
echo ""
echo -e "${BLUE}🔄 Mise à jour:${NC}"
echo "   $UPDATE_SCRIPT     # Script de mise à jour"
echo "   cd $INSTALL_DIR/SymGuard && git pull  # Manuel"
echo ""
echo -e "${BLUE}📋 Options utiles:${NC}"
echo "   --dry-run     : Mode simulation"
echo "   --real        : Mode réel (suppression)"
echo "   --quick       : Scan basique uniquement"
echo "   -j 4          : 4 workers parallèles"
echo ""
echo -e "${BLUE}📊 Logs et rapports:${NC}"
echo "   Logs: $HOME_DIR/symlink_maintenance.log"
echo "   Rapports: $INSTALL_DIR/SymGuard/symlink_report_*.json"
echo "   Suppressions: $INSTALL_DIR/SymGuard/deleted_files_*.log"

echo -e "\n${GREEN}✅ Prêt à analyser vos liens symboliques !${NC}"
