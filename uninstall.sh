#!/bin/bash

# SymGuard - Script de désinstallation
# Supprime complètement SymGuard du système

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

# Fonction de confirmation
confirm_action() {
    local message="$1"
    echo -e "${YELLOW}⚠️  $message${NC}"
    read -p "Continuer ? (y/N): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# Rechercher les installations existantes
find_installations() {
    print_status "Recherche des installations SymGuard..."
    
    local installations=()
    
    # Emplacements possibles
    local possible_locations=(
        "$HOME/SymGuard"
        "$HOME/scripts/SymGuard"
        "/opt/SymGuard"
        "/usr/local/bin/SymGuard"
        "/home/$USER/SymGuard"
        "/home/kesurof/scripts/SymGuard"
    )
    
    for location in "${possible_locations[@]}"; do
        if [[ -d "$location" ]] && [[ -f "$location/script.py" ]]; then
            installations+=("$location")
            print_status "Installation trouvée: $location"
        fi
    done
    
    # Recherche de fichiers script.py isolés
    local script_files=$(find /home -name "script.py" -path "*/SymGuard/*" 2>/dev/null || true)
    for script_file in $script_files; do
        local dir=$(dirname "$script_file")
        if [[ ! " ${installations[@]} " =~ " ${dir} " ]]; then
            installations+=("$dir")
            print_status "Script isolé trouvé: $dir"
        fi
    done
    
    echo "${installations[@]}"
}

# Supprimer les répertoires d'installation
remove_installations() {
    local installations=("$@")
    
    if [[ ${#installations[@]} -eq 0 ]]; then
        print_warning "Aucune installation trouvée"
        return
    fi
    
    print_status "Suppression des installations..."
    
    for installation in "${installations[@]}"; do
        if confirm_action "Supprimer l'installation: $installation"; then
            if [[ -d "$installation" ]]; then
                # Sauvegarder la configuration si elle existe
                if [[ -f "$installation/.symguard_config.json" ]]; then
                    local backup_config="$HOME/.symguard_config.json.backup.$(date +%Y%m%d_%H%M%S)"
                    cp "$installation/.symguard_config.json" "$backup_config" 2>/dev/null || true
                    print_success "Configuration sauvegardée: $backup_config"
                fi
                
                # Supprimer le répertoire
                if [[ "$installation" == "/opt/"* ]] || [[ "$installation" == "/usr/"* ]]; then
                    sudo rm -rf "$installation"
                else
                    rm -rf "$installation"
                fi
                print_success "Installation supprimée: $installation"
            fi
        else
            print_warning "Installation conservée: $installation"
        fi
    done
}

# Supprimer les fichiers de configuration
remove_config_files() {
    print_status "Recherche des fichiers de configuration..."
    
    local config_files=(
        "$HOME/.symguard_config.json"
        "/home/$USER/.symguard_config.json"
        "/root/.symguard_config.json"
    )
    
    for config_file in "${config_files[@]}"; do
        if [[ -f "$config_file" ]]; then
            print_status "Fichier de configuration trouvé: $config_file"
            if confirm_action "Supprimer la configuration: $config_file"; then
                # Créer une sauvegarde
                local backup_file="$config_file.backup.$(date +%Y%m%d_%H%M%S)"
                cp "$config_file" "$backup_file" 2>/dev/null || true
                rm -f "$config_file"
                print_success "Configuration supprimée (sauvegarde: $backup_file)"
            else
                print_warning "Configuration conservée: $config_file"
            fi
        fi
    done
}

# Supprimer les logs et rapports
remove_logs() {
    print_status "Recherche des logs et rapports..."
    
    local log_patterns=(
        "$HOME/symlink_maintenance*.log"
        "$HOME/symlink_report_*.json"
        "$HOME/deleted_files_*.log"
        "/var/log/symguard*.log"
        "/tmp/symguard*.tmp"
    )
    
    local found_logs=()
    for pattern in "${log_patterns[@]}"; do
        for file in $pattern; do
            if [[ -f "$file" ]]; then
                found_logs+=("$file")
            fi
        done
    done
    
    if [[ ${#found_logs[@]} -gt 0 ]]; then
        print_status "Logs trouvés: ${#found_logs[@]} fichiers"
        if confirm_action "Supprimer tous les logs et rapports SymGuard"; then
            for log_file in "${found_logs[@]}"; do
                rm -f "$log_file"
                print_success "Log supprimé: $(basename "$log_file")"
            done
        else
            print_warning "Logs conservés"
        fi
    else
        print_status "Aucun log trouvé"
    fi
}

# Supprimer les alias et raccourcis
remove_aliases() {
    print_status "Suppression des alias et raccourcis..."
    
    local shell_files=(
        "$HOME/.bashrc"
        "$HOME/.zshrc"
        "$HOME/.profile"
        "/root/.bashrc"
    )
    
    for shell_file in "${shell_files[@]}"; do
        if [[ -f "$shell_file" ]] && grep -q "symguard" "$shell_file" 2>/dev/null; then
            print_status "Alias SymGuard trouvé dans: $shell_file"
            if confirm_action "Supprimer l'alias de $shell_file"; then
                # Créer une sauvegarde
                cp "$shell_file" "$shell_file.backup.$(date +%Y%m%d_%H%M%S)"
                
                # Supprimer les lignes contenant symguard
                sed -i.bak '/symguard/d' "$shell_file" 2>/dev/null || {
                    grep -v "symguard" "$shell_file" > "${shell_file}.tmp" && mv "${shell_file}.tmp" "$shell_file"
                }
                
                print_success "Alias supprimé de: $shell_file"
            fi
        fi
    done
    
    # Supprimer les liens symboliques
    local bin_dirs=("/usr/local/bin" "/usr/bin" "$HOME/.local/bin")
    for bin_dir in "${bin_dirs[@]}"; do
        if [[ -L "$bin_dir/symguard" ]]; then
            print_status "Lien symbolique trouvé: $bin_dir/symguard"
            if confirm_action "Supprimer le lien symbolique"; then
                if [[ "$bin_dir" == "/usr/"* ]]; then
                    sudo rm -f "$bin_dir/symguard"
                else
                    rm -f "$bin_dir/symguard"
                fi
                print_success "Lien symbolique supprimé: $bin_dir/symguard"
            fi
        fi
    done
}

# Supprimer les tâches cron
remove_cron_jobs() {
    print_status "Vérification des tâches cron..."
    
    if crontab -l 2>/dev/null | grep -q "symguard\|SymGuard" 2>/dev/null; then
        print_status "Tâches cron SymGuard trouvées"
        if confirm_action "Supprimer les tâches cron SymGuard"; then
            # Sauvegarder la crontab actuelle
            crontab -l > "$HOME/crontab.backup.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
            
            # Supprimer les lignes contenant symguard
            (crontab -l 2>/dev/null | grep -v -i "symguard" | crontab -) || true
            print_success "Tâches cron SymGuard supprimées"
        fi
    else
        print_status "Aucune tâche cron SymGuard trouvée"
    fi
}

# Nettoyer les processus en cours
cleanup_processes() {
    print_status "Vérification des processus SymGuard en cours..."
    
    local symguard_pids=$(pgrep -f "script.py\|symguard" 2>/dev/null || true)
    if [[ -n "$symguard_pids" ]]; then
        print_warning "Processus SymGuard en cours détectés"
        if confirm_action "Arrêter les processus SymGuard"; then
            echo "$symguard_pids" | xargs kill 2>/dev/null || true
            sleep 2
            echo "$symguard_pids" | xargs kill -9 2>/dev/null || true
            print_success "Processus arrêtés"
        fi
    else
        print_status "Aucun processus SymGuard en cours"
    fi
}

# Vérifier la désinstallation
verify_removal() {
    print_status "Vérification de la désinstallation..."
    
    local remaining_items=()
    
    # Vérifier les installations
    local remaining_installations=($(find_installations))
    for installation in "${remaining_installations[@]}"; do
        remaining_items+=("Installation: $installation")
    done
    
    # Vérifier les configurations
    if [[ -f "$HOME/.symguard_config.json" ]]; then
        remaining_items+=("Configuration: $HOME/.symguard_config.json")
    fi
    
    # Vérifier les alias
    if grep -q "symguard" "$HOME/.bashrc" "$HOME/.zshrc" 2>/dev/null; then
        remaining_items+=("Alias dans shell")
    fi
    
    if [[ ${#remaining_items[@]} -eq 0 ]]; then
        print_success "Désinstallation complète réussie!"
    else
        print_warning "Éléments restants détectés:"
        for item in "${remaining_items[@]}"; do
            echo "  - $item"
        done
    fi
}

# Afficher un résumé des sauvegardes
show_backups() {
    print_status "Sauvegardes créées:"
    
    local backup_files=(
        "$HOME/.symguard_config.json.backup.*"
        "$HOME/crontab.backup.*"
        "$HOME/.bashrc.backup.*"
        "$HOME/.zshrc.backup.*"
    )
    
    local found_backups=()
    for pattern in "${backup_files[@]}"; do
        for file in $pattern; do
            if [[ -f "$file" ]]; then
                found_backups+=("$file")
            fi
        done
    done
    
    if [[ ${#found_backups[@]} -gt 0 ]]; then
        for backup in "${found_backups[@]}"; do
            print_success "Sauvegarde: $backup"
        done
    else
        print_status "Aucune sauvegarde créée"
    fi
}

# Fonction principale
main() {
    echo "=============================================="
    echo -e "${RED}🗑️  SymGuard - Désinstallation${NC}"
    echo "=============================================="
    echo
    
    print_warning "Ce script va supprimer complètement SymGuard de votre système"
    print_warning "Des sauvegardes seront créées pour les configurations importantes"
    echo
    
    if ! confirm_action "Continuer avec la désinstallation complète"; then
        print_status "Désinstallation annulée"
        exit 0
    fi
    
    echo
    print_status "Début de la désinstallation..."
    
    # Étapes de désinstallation
    cleanup_processes
    
    # Trouver et supprimer les installations
    local installations=($(find_installations))
    remove_installations "${installations[@]}"
    
    remove_config_files
    remove_logs
    remove_aliases
    remove_cron_jobs
    
    # Vérification finale
    echo
    verify_removal
    show_backups
    
    echo
    echo "=============================================="
    echo -e "${GREEN}✅ DÉSINSTALLATION TERMINÉE${NC}"
    echo "=============================================="
    echo
    print_success "SymGuard a été supprimé de votre système"
    print_warning "Redémarrez votre terminal pour supprimer les alias restants"
    echo
    print_status "Pour réinstaller SymGuard:"
    echo "  curl -fsSL https://raw.githubusercontent.com/kesurof/SymGuard/main/install.sh | bash"
}

# Exécution avec gestion d'erreur
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
