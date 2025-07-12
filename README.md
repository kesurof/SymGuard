# SymGuard - Vérificateur Avancé de Liens Symboliques

## 🖥️ Optimisé pour serveurs Linux
- **OS**: Ubuntu 20.04+ / Debian 10+
- **Architecture**: x86_64 / aarch64
- **Python**: 3.8+ (environnement virtuel recommandé)

## 📋 Description

SymGuard est un outil avancé de vérification et nettoyage des liens symboliques, spécialement conçu pour les serveurs média avec de gros volumes de données.

### ✨ Fonctionnalités

- **Scan en 2 phases** : basique + vérification ffprobe
- **Traitement parallèle** optimisé pour serveurs multi-cœurs
- **Gestion intelligente des serveurs média** (Sonarr, Radarr, Bazarr, Prowlarr)
- **Modes sécurisés** : dry-run et réel avec confirmation
- **Rapports détaillés** : JSON + logs de suppression
- **Rotation automatique** des logs anciens

## 🚀 Installation

```bash
# Cloner le projet
git clone https://github.com/kesurof/SymGuard.git
cd SymGuard

# Configuration automatique
chmod +x setup.sh
./setup.sh
```

## ⚙️ Configuration automatique détectée

Le script détecte automatiquement votre environnement :

```bash
# Variables d'environnement utilisées
USER=$USER
HOME=$HOME
SETTINGS_SOURCE=$HOME/seedbox-compose (ou configuré)
VIRTUAL_ENV=$VIRTUAL_ENV (si disponible)
```

## 🎯 Utilisation

### Exécution simple
```bash
# Avec l'alias configuré
symguard

# Ou directement
python3 script.py
```

### Options avancées
```bash
# Mode dry-run forcé
python3 script.py --dry-run

# Mode réel forcé
python3 script.py --real

# Scan basique uniquement (rapide)
python3 script.py --quick

# Personnaliser les workers (détection automatique)
python3 script.py -j 4

# Répertoire personnalisé
python3 script.py /path/to/your/media
```

## 📊 Fonctionnement

### Phase 1 - Scan basique
- Vérification existence des cibles
- Test d'accès en lecture
- Détection fichiers vides/corrompus
- **Optimisé** : Workers parallèles (détection automatique)

### Phase 2 - Vérification ffprobe
- Validation des fichiers média avec ffprobe
- Détection corruption vidéo/audio
- **Estimation** automatique du temps

### Gestion serveurs média
- **Auto-détection** des conteneurs Docker
- **Récupération** automatique des clés API
- **Déclenchement** des scans post-nettoyage
- **Support** : Sonarr, Radarr, Bazarr, Prowlarr

## 📁 Structure des fichiers

```
/path/to/SymGuard/
├── script.py              # Script principal
├── requirements.txt       # Dépendances Python
├── setup.sh              # Configuration automatique
├── README.md             # Cette documentation
└── logs/
    ├── symlink_maintenance.log     # Logs principaux
    ├── symlink_report_*.json       # Rapports détaillés
    └── deleted_files_*.log         # Logs suppressions
```

## 🔧 Résolution de problèmes

### ffprobe manquant
```bash
sudo apt update && sudo apt install ffmpeg
```

### Problèmes Docker
```bash
# Vérifier l'accès Docker
docker ps

# Ajouter l'utilisateur au groupe docker (si nécessaire)
sudo usermod -aG docker $USER
```

### Permissions insuffisantes
```bash
# Vérifier l'accès au répertoire média
ls -la /path/to/your/media

# Corriger si nécessaire
sudo chown -R $USER:$USER /path/to/your/media
```

## 📊 Monitoring système

Le script surveille automatiquement :
- **Mémoire** : >1GB recommandé
- **Disque** : >5GB libre recommandé  
- **Charge CPU** : <2.0 pour scan optimal
- **Processus** : ffprobe disponible

## 🔒 Sécurité

- **Mode dry-run** par défaut pour tester
- **Confirmation** obligatoire avant suppression
- **Logs détaillés** de toutes les opérations
- **Sauvegarde** des chemins supprimés
- **Rotation** automatique des logs

## 📈 Performance

Optimisations pour serveurs multi-cœurs :
- **Workers parallèles** (détection automatique des cœurs)
- **Traitement par chunks** pour gros volumes
- **Cache intelligent** des résultats
- **Gestion mémoire** optimisée

## 🔗 Intégrations

### Serveurs média supportés
- **Sonarr** : Scan séries + recherche manquants
- **Radarr** : Scan films + recherche manquants  
- **Bazarr** : Recherche sous-titres
- **Prowlarr** : Test indexeurs

### Chemins de configuration détectés
```
$SETTINGS_SOURCE/docker/$USER/[service]/config/config.xml
/opt/seedbox/docker/$USER/[service]/config/config.xml
$HOME/.config/[service]/config.xml
```

## 📞 Support

En cas de problème :

1. **Vérifiez les logs** : `tail -f ~/symlink_maintenance.log`
2. **Testez en dry-run** : `python3 script.py --dry-run`
3. **Réduisez les workers** : `python3 script.py -j 2`
4. **Mode quick** si problème : `python3 script.py --quick`

## 🏷️ Version

- **Script** : 2.0.0
- **Compatible** : Linux (x86_64/aarch64)
- **Python** : 3.8+
- **OS** : Ubuntu 20.04+ / Debian 10+
