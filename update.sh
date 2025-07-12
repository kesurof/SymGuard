#!/bin/bash

# SymGuard - Script de mise à jour automatique
# Met à jour SymGuard vers la dernière version

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

# Déterminer le répertoire d'installation
INSTALL_DIR="$HOME/SymGuard"
if [[ ! -d "$INSTALL_DIR" ]]; then
    # Essayer des emplacements alternatifs
    if [[ -d "$HOME/scripts/SymGuard" ]]; then
        INSTALL_DIR="$HOME/scripts/SymGuard"
    elif [[ -d "/opt/SymGuard" ]]; then
        INSTALL_DIR="/opt/SymGuard"
    else
        print_error "Installation de SymGuard non trouvée"
        print_error "Répertoires vérifiés:"
        print_error "  - $HOME/SymGuard"
        print_error "  - $HOME/scripts/SymGuard"
        print_error "  - /opt/SymGuard"
        exit 1
    fi
fi

print_status "SymGuard trouvé dans: $INSTALL_DIR"

# Sauvegarder la configuration actuelle
backup_config() {
    print_status "Sauvegarde de la configuration..."
    
    CONFIG_FILE="$HOME/.symguard_config.json"
    if [[ -f "$CONFIG_FILE" ]]; then
        BACKUP_FILE="$CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$CONFIG_FILE" "$BACKUP_FILE"
        print_success "Configuration sauvegardée: $BACKUP_FILE"
    else
        print_warning "Aucune configuration existante à sauvegarder"
    fi
}

# Vérifier les mises à jour disponibles
check_updates() {
    print_status "Vérification des mises à jour..."
    
    cd "$INSTALL_DIR"
    
    # Récupérer les dernières informations
    git fetch origin main
    
    # Comparer les versions
    LOCAL_COMMIT=$(git rev-parse HEAD)
    REMOTE_COMMIT=$(git rev-parse origin/main)
    
    if [[ "$LOCAL_COMMIT" == "$REMOTE_COMMIT" ]]; then
        print_success "SymGuard est déjà à jour"
        return 1  # Pas de mise à jour nécessaire
    else
        print_status "Mise à jour disponible"
        
        # Afficher les changements
        echo
        print_status "Changements depuis votre version:"
        git log --oneline HEAD..origin/main | head -10
        echo
        
        return 0  # Mise à jour disponible
    fi
}

# Effectuer la mise à jour
perform_update() {
    print_status "Mise à jour en cours..."
    
    cd "$INSTALL_DIR"
    
    # Sauvegarder l'état actuel
    git stash push -m "Backup before update $(date)"
    
    # Mettre à jour
    git pull origin main
    
    # Rendre le script exécutable
    chmod +x script.py
    
    print_success "Mise à jour terminée"
}

# Vérifier que tout fonctionne
verify_update() {
    print_status "Vérification de la mise à jour..."
    
    cd "$INSTALL_DIR"
    
    if python3 script.py --version; then
        print_success "SymGuard fonctionne correctement après mise à jour"
    else
        print_error "Problème détecté après mise à jour"
        return 1
    fi
}

# Restaurer les permissions si nécessaire
fix_permissions() {
    print_status "Vérification des permissions..."
    
    cd "$INSTALL_DIR"
    
    # S'assurer que le script est exécutable
    chmod +x script.py
    
    # Vérifier que les fichiers appartiennent à l'utilisateur
    if [[ $(stat -c %U script.py) != "$USER" ]]; then
        print_warning "Correction des permissions..."
        sudo chown -R "$USER:$USER" "$INSTALL_DIR"
    fi
    
    print_success "Permissions OK"
}

# Afficher les informations de version
show_version_info() {
    cd "$INSTALL_DIR"
    
    # Version actuelle
    CURRENT_VERSION=$(python3 script.py --version 2>&1 | grep -o 'v[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "inconnue")
    
    # Dernier commit
    LAST_COMMIT=$(git log -1 --format="%h - %s (%cr)")
    
    echo
    echo "=============================================="
    echo -e "${GREEN}✅ MISE À JOUR TERMINÉE${NC}"
    echo "=============================================="
    echo -e "${BLUE}📁 Installation:${NC} $INSTALL_DIR"
    echo -e "${BLUE}🏷️ Version:${NC} $CURRENT_VERSION"
    echo -e "${BLUE}📝 Dernier commit:${NC} $LAST_COMMIT"
    echo
    echo -e "${YELLOW}🚀 Pour utiliser:${NC}"
    echo "  python3 $INSTALL_DIR/script.py"
    echo "  # ou avec l'alias: symguard"
    echo
}

# Fonction principale
main() {
    echo "=============================================="
    echo -e "${BLUE}🔄 SymGuard - Mise à jour${NC}"
    echo "=============================================="
    echo
    
    # Vérifications préliminaires
    if [[ ! -d "$INSTALL_DIR/.git" ]]; then
        print_error "Le répertoire $INSTALL_DIR ne semble pas être un repository Git"
        print_error "Réinstallez SymGuard avec le script d'installation"
        exit 1
    fi
    
    # Processus de mise à jour
    backup_config
    
    if check_updates; then
        # Demander confirmation
        echo
        read -p "Effectuer la mise à jour ? (Y/n): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            perform_update
            fix_permissions
            verify_update
            show_version_info
            print_success "Mise à jour terminée avec succès!"
        else
            print_warning "Mise à jour annulée"
        fi
    else
        print_success "Aucune mise à jour nécessaire"
    fi
}

# Exécution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
