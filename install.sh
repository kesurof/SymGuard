#!/bin/bash

# SymGuard v2.0.1 - Script d'installation automatique
# Compatible Ubuntu/Debian et CentOS/RHEL

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction d'affichage coloré
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Détection de l'OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        print_error "Impossible de détecter l'OS"
        exit 1
    fi
    
    print_status "OS détecté: $OS $VERSION"
}

# Installation des dépendances système
install_system_deps() {
    print_status "Installation des dépendances système..."
    
    case $OS in
        ubuntu|debian)
            sudo apt update
            sudo apt install -y python3 python3-pip ffmpeg curl git
            ;;
        centos|rhel|fedora)
            if command -v dnf &> /dev/null; then
                sudo dnf install -y python3 python3-pip ffmpeg curl git
            else
                sudo yum install -y python3 python3-pip ffmpeg curl git
            fi
            ;;
        *)
            print_warning "OS non supporté officiellement: $OS"
            print_warning "Assurez-vous d'avoir: python3, pip, ffmpeg, curl, git"
            ;;
    esac
    
    print_success "Dépendances système installées"
}

# Installation des dépendances Python
install_python_deps() {
    print_status "Installation des dépendances Python..."
    
    # Vérifier si pip3 existe
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 non trouvé. Installation requise."
        exit 1
    fi
    
    # Installer les modules Python
    pip3 install --user requests urllib3 psutil
    
    print_success "Dépendances Python installées"
}

# Vérification des outils
check_tools() {
    print_status "Vérification des outils..."
    
    # Python 3
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python 3 disponible (version $PYTHON_VERSION)"
    else
        print_error "Python 3 non trouvé"
        exit 1
    fi
    
    # ffprobe
    if command -v ffprobe &> /dev/null; then
        FFPROBE_VERSION=$(ffprobe -version 2>/dev/null | head -n1 | cut -d' ' -f3)
        print_success "ffprobe disponible (version $FFPROBE_VERSION)"
    else
        print_warning "ffprobe non trouvé - la vérification avancée sera désactivée"
    fi
    
    # Git
    if command -v git &> /dev/null; then
        print_success "Git disponible"
    else
        print_error "Git non trouvé"
        exit 1
    fi
}

# Installation de SymGuard
install_symguard() {
    print_status "Installation de SymGuard..."
    
    # Répertoire d'installation
    INSTALL_DIR="$HOME/SymGuard"
    
    # Cloner ou mettre à jour le repository
    if [[ -d "$INSTALL_DIR" ]]; then
        print_status "Mise à jour du repository existant..."
        cd "$INSTALL_DIR"
        git pull origin main
    else
        print_status "Clonage du repository..."
        git clone https://github.com/kesurof/SymGuard.git "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
    
    # Rendre le script exécutable
    chmod +x script.py
    
    print_success "SymGuard installé dans $INSTALL_DIR"
}

# Configuration initiale
setup_config() {
    print_status "Configuration initiale..."
    
    # Copier l'exemple de configuration si pas existant
    if [[ ! -f "$HOME/.symguard_config.json" ]]; then
        if [[ -f ".symguard_config.json.example" ]]; then
            cp .symguard_config.json.example "$HOME/.symguard_config.json"
            print_success "Fichier de configuration créé: $HOME/.symguard_config.json"
            print_warning "Éditez ce fichier pour ajouter vos clés API"
        else
            print_warning "Fichier d'exemple de configuration non trouvé"
        fi
    else
        print_success "Fichier de configuration existant trouvé"
    fi
}

# Création d'un alias optionnel
create_alias() {
    print_status "Création d'un alias optionnel..."
    
    ALIAS_LINE="alias symguard='python3 $INSTALL_DIR/script.py'"
    
    # Ajouter l'alias au bashrc s'il n'existe pas déjà
    if ! grep -q "alias symguard=" "$HOME/.bashrc" 2>/dev/null; then
        echo "" >> "$HOME/.bashrc"
        echo "# SymGuard alias" >> "$HOME/.bashrc"
        echo "$ALIAS_LINE" >> "$HOME/.bashrc"
        print_success "Alias 'symguard' ajouté à ~/.bashrc"
        print_warning "Redémarrez votre terminal ou exécutez: source ~/.bashrc"
    else
        print_success "Alias 'symguard' déjà existant"
    fi
}

# Test de l'installation
test_installation() {
    print_status "Test de l'installation..."
    
    cd "$INSTALL_DIR"
    
    # Test basique
    if python3 script.py --version; then
        print_success "SymGuard fonctionne correctement"
    else
        print_error "Problème avec l'installation de SymGuard"
        exit 1
    fi
}

# Affichage des informations finales
show_final_info() {
    echo
    echo "=============================================="
    echo -e "${GREEN}🎉 INSTALLATION TERMINÉE${NC}"
    echo "=============================================="
    echo
    echo -e "${BLUE}📁 Installation:${NC} $INSTALL_DIR"
    echo -e "${BLUE}⚙️ Configuration:${NC} $HOME/.symguard_config.json"
    echo
    echo -e "${YELLOW}🚀 UTILISATION:${NC}"
    echo "  # Via le chemin complet:"
    echo "  python3 $INSTALL_DIR/script.py"
    echo
    echo "  # Via l'alias (après redémarrage terminal):"
    echo "  symguard"
    echo
    echo -e "${YELLOW}📝 CONFIGURATION:${NC}"
    echo "  # Configuration interactive:"
    echo "  python3 $INSTALL_DIR/script.py --config"
    echo
    echo "  # Édition manuelle:"
    echo "  nano $HOME/.symguard_config.json"
    echo
    echo -e "${YELLOW}📖 AIDE:${NC}"
    echo "  python3 $INSTALL_DIR/script.py --help"
    echo
    echo -e "${GREEN}✅ Prêt à utiliser!${NC}"
}

# Script principal
main() {
    echo "=============================================="
    echo -e "${BLUE}🚀 SymGuard v2.0.1 - Installation${NC}"
    echo "=============================================="
    echo
    
    # Vérifications préliminaires
    if [[ $EUID -eq 0 ]]; then
        print_error "N'exécutez pas ce script en tant que root"
        exit 1
    fi
    
    # Étapes d'installation
    detect_os
    install_system_deps
    install_python_deps
    check_tools
    install_symguard
    setup_config
    create_alias
    test_installation
    show_final_info
    
    echo
    print_success "Installation terminée avec succès!"
}

# Exécution avec gestion d'erreur
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
