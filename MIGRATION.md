# Guide de Migration SymGuard

Ce guide vous aide à migrer depuis une ancienne version de SymGuard vers la v2.0.1.

## 🔄 Migration Automatique (Recommandée)

### Étape 1 : Sauvegarde de l'ancienne configuration
```bash
# Sauvegarder vos paramètres actuels
cp ~/.symguard_config.json ~/.symguard_config.json.old 2>/dev/null || echo "Aucune config existante"

# Sauvegarder les logs importants
cp ~/symlink_maintenance.log ~/symlink_maintenance.log.old 2>/dev/null || echo "Aucun log existant"
```

### Étape 2 : Désinstallation de l'ancienne version
```bash
# Télécharger et exécuter le script de désinstallation
curl -fsSL https://raw.githubusercontent.com/kesurof/SymGuard/main/uninstall.sh | bash
```

### Étape 3 : Installation de la nouvelle version
```bash
# Installation automatique v2.0.1
curl -fsSL https://raw.githubusercontent.com/kesurof/SymGuard/main/install.sh | bash
```

### Étape 4 : Configuration interactive
```bash
# Configuration guidée des serveurs média
symguard --config
```

## 🛠️ Migration Manuelle

### Si vous avez une ancienne version < 2.0

#### 1. Identifier votre installation actuelle
```bash
# Trouver les scripts existants
find ~ -name "*symguard*" -o -name "*symlink*" 2>/dev/null

# Vérifier les alias
grep -r "symguard\|symlink" ~/.bashrc ~/.zshrc 2>/dev/null
```

#### 2. Sauvegarder vos données importantes
```bash
# Créer un dossier de sauvegarde
mkdir -p ~/symguard_migration_backup
cd ~/symguard_migration_backup

# Sauvegarder les configurations
cp ~/.symguard_config.json . 2>/dev/null || echo "Pas de config JSON"
cp ~/symlink_maintenance.log . 2>/dev/null || echo "Pas de log principal"
cp ~/symlink_report_*.json . 2>/dev/null || echo "Pas de rapports"

# Sauvegarder les scripts personnalisés si modifiés
cp ~/SymGuard/script.py script_old.py 2>/dev/null || echo "Pas de script personnalisé"
```

#### 3. Nettoyer l'ancienne installation
```bash
# Supprimer les anciens répertoires
rm -rf ~/SymGuard
rm -rf ~/scripts/SymGuard
rm -rf ~/symlink-checker

# Nettoyer les alias (sauvegarder d'abord)
cp ~/.bashrc ~/.bashrc.backup
sed -i '/symguard\|symlink/d' ~/.bashrc

# Nettoyer les tâches cron
crontab -l > ~/crontab.backup
crontab -l | grep -v symguard | crontab -
```

#### 4. Installer la nouvelle version
```bash
# Installation standard
curl -fsSL https://raw.githubusercontent.com/kesurof/SymGuard/main/install.sh | bash

# Configuration interactive
symguard --config
```

## 📋 Différences Principales v2.0.1

### 🆕 Nouveautés
| Fonctionnalité | v1.x | v2.0.1 |
|----------------|------|--------|
| Configuration | Variables dans script | Fichier JSON séparé |
| Serveurs média | Détection Docker | Configuration manuelle + auto-détection |
| Installation | Manuel | Scripts automatiques |
| Mise à jour | Git pull | Script dédié |
| Interface | Basique | Interactive guidée |

### 🔧 Améliorations
- **Performance** : Sessions HTTP avec retry automatique
- **Fiabilité** : Gestion d'erreurs améliorée
- **UX** : Configuration pas à pas
- **Maintenance** : Scripts d'installation/mise à jour
- **Documentation** : Guide complet

### 🗑️ Fonctionnalités supprimées
- **Détection Docker automatique** : Remplacée par configuration JSON
- **Variables hard-codées** : Remplacées par configuration externe

## 📂 Migration des Configurations

### Ancienne configuration (v1.x)
```python
# Dans le script
SONARR_URL = "http://localhost:8989"
SONARR_API_KEY = "votre_clé"
```

### Nouvelle configuration (v2.0.1)
```json
{
  "sonarr": {
    "url": "http://localhost:8989",
    "api_key": "votre_clé",
    "enabled": true
  }
}
```

### Script de conversion automatique
```bash
# Créer la nouvelle configuration depuis l'ancienne
cat > ~/.symguard_config.json << 'EOF'
{
  "sonarr": {
    "url": "http://localhost:8989",
    "api_key": "VOTRE_CLE_SONARR",
    "enabled": true
  },
  "radarr": {
    "url": "http://localhost:7878",
    "api_key": "VOTRE_CLE_RADARR",
    "enabled": true
  },
  "bazarr": {
    "url": "http://localhost:6767",
    "api_key": "VOTRE_CLE_BAZARR",
    "enabled": true
  },
  "prowlarr": {
    "url": "http://localhost:9696",
    "api_key": "VOTRE_CLE_PROWLARR",
    "enabled": true
  }
}
EOF

# Puis éditer avec vos vraies clés
nano ~/.symguard_config.json
```

## 🧪 Test après Migration

### Vérifier l'installation
```bash
# Test de base
symguard --version

# Test de configuration
symguard --config

# Test de scan (dry-run)
symguard --dry-run --quick
```

### Vérifier les serveurs média
```bash
# Test de connexion aux APIs
curl -H "X-Api-Key: VOTRE_CLE" http://localhost:8989/api/v3/system/status
curl -H "X-Api-Key: VOTRE_CLE" http://localhost:7878/api/v3/system/status
```

## 🆘 Résolution de Problèmes

### Problème : "Command not found: symguard"
```bash
# Vérifier l'installation
ls -la ~/SymGuard/

# Recharger le shell
source ~/.bashrc

# Réinstaller si nécessaire
curl -fsSL https://raw.githubusercontent.com/kesurof/SymGuard/main/install.sh | bash
```

### Problème : "API key manquante"
```bash
# Vérifier la configuration
cat ~/.symguard_config.json

# Reconfigurer interactivement
symguard --config

# Créer une nouvelle configuration
symguard --create-config
```

### Problème : Permissions refusées
```bash
# Corriger les permissions
chmod +x ~/SymGuard/script.py
chmod +x ~/SymGuard/install.sh
chmod +x ~/SymGuard/update.sh
```

## 📞 Support

Si vous rencontrez des problèmes lors de la migration :

1. **Vérifiez les logs** : `~/symlink_maintenance.log`
2. **Consultez la documentation** : `README.md`
3. **Issues GitHub** : [SymGuard Issues](https://github.com/kesurof/SymGuard/issues)
4. **Discussions** : [SymGuard Discussions](https://github.com/kesurof/SymGuard/discussions)

## 🔄 Rollback (Retour en Arrière)

Si la migration pose problème :

```bash
# Restaurer l'ancienne version depuis la sauvegarde
cd ~/symguard_migration_backup
cp script_old.py ~/SymGuard/script.py

# Restaurer les configs shell
cp ~/.bashrc.backup ~/.bashrc

# Restaurer les tâches cron
crontab ~/crontab.backup

# Recharger le shell
source ~/.bashrc
```

---

*Guide de migration SymGuard v2.0.1 - Pour une transition en douceur* 🚀
