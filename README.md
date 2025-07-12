# SymGuard - Vérificateur Avancé de Liens Symboliques

## 🖥️ Optimisé pour serveur ssd-83774
- **OS**: Ubuntu 22.04.5 LTS
- **Architecture**: aarch64 (Neoverse-N1)
- **Utilisateur**: kesurof
- **Python**: 3.10.12 (environnement virtuel)

## 📋 Description

SymGuard est un outil avancé de vérification et nettoyage des liens symboliques, spécialement conçu pour les serveurs média avec de gros volumes de données.

### ✨ Fonctionnalités

- **Scan en 2 phases** : basique + vérification ffprobe
- **Traitement parallèle** optimisé pour 4 cœurs aarch64
- **Gestion intelligente des serveurs média** (Sonarr, Radarr, Bazarr, Prowlarr)
- **Modes sécurisés** : dry-run et réel avec confirmation
- **Rapports détaillés** : JSON + logs de suppression
- **Rotation automatique** des logs anciens

## 🚀 Installation

```bash
# Cloner le projet
git clone <repository> /home/kesurof/SymGuard
cd /home/kesurof/SymGuard

# Configuration automatique
chmod +x setup.sh
./setup.sh
```

## ⚙️ Configuration automatique détectée

Le script détecte automatiquement votre environnement :

```bash
# Variables d'environnement utilisées
USER=kesurof
HOME=/home/kesurof
SETTINGS_SOURCE=/home/kesurof/seedbox-compose
VIRTUAL_ENV=/home/kesurof/seedbox-compose/venv
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

# Personnaliser les workers (défaut: 8 pour votre serveur)
python3 script.py -j 4

# Répertoire personnalisé
python3 script.py /home/kesurof/Medias/Films
```

## 📊 Fonctionnement

### Phase 1 - Scan basique
- Vérification existence des cibles
- Test d'accès en lecture
- Détection fichiers vides/corrompus
- **Optimisé** : 8 workers parallèles

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
/home/kesurof/SymGuard/
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
sudo usermod -aG docker kesurof
```

### Permissions insuffisantes
```bash
# Vérifier l'accès au répertoire média
ls -la /home/kesurof/Medias

# Corriger si nécessaire
sudo chown -R kesurof:kesurof /home/kesurof/Medias
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

Optimisations pour votre serveur :
- **8 workers** parallèles (2x vos 4 cœurs)
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
/home/kesurof/seedbox-compose/docker/kesurof/[service]/config/config.xml
/opt/seedbox/docker/kesurof/[service]/config/config.xml
/home/kesurof/.config/[service]/config.xml
```

## 📞 Support

En cas de problème :

1. **Vérifiez les logs** : `tail -f ~/symlink_maintenance.log`
2. **Testez en dry-run** : `python3 script.py --dry-run`
3. **Réduisez les workers** : `python3 script.py -j 2`
4. **Mode quick** si problème : `python3 script.py --quick`

## 🏷️ Version

- **Script** : 2.0.0
- **Optimisé pour** : ssd-83774 (aarch64)
- **Python** : 3.10.12+
- **OS** : Ubuntu 22.04.5 LTS
