# Changelog

Toutes les modifications notables de SymGuard seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Versionnage Sémantique](https://semver.org/lang/fr/).

## [2.0.3] - 2025-01-13

### ✨ Nouvelles fonctionnalités
- **Option scan individuel vs en masse** : Choix lors de la confirmation entre :
  - Mode masse : scan complet rapide (comme avant)
  - Mode individuel : notifications précises par fichier/titre
  - Mode aucun : désactiver ponctuellement les notifications
- **Analyse intelligente des fichiers média** : 
  - Parsing automatique des noms de séries (SxxExx)
  - Détection des films avec année
  - Reconnaissance des structures de dossiers
- **Notifications ciblées** :
  - Sonarr : rafraîchissement par série identifiée
  - Radarr : rafraîchissement par film identifié
  - Évite les scans complets inutiles

### 🔧 Améliorations techniques  
- Ajout imports manquants (`gc`, `re`)
- Correction fonction `interactive_config_setup()` incomplète
- Gestion gracieuse des dépendances optionnelles (`psutil`, `requests`)
- Support fallback si modules non disponibles
- Nouvelle option `--no-media-scan` pour ignorer complètement
- Amélioration gestion d'erreurs API

### 🐛 Corrections de bugs
- Erreur "API key manquante" bloquant l'exécution
- Imports manquants causant des crashes
- Fonctions incomplètes dans le setup interactif
- Gestion d'erreur insuffisante pour dépendances

### 📚 Documentation
- Section troubleshooting dans README.md
- Documentation option `--no-media-scan`
- Exemples de configuration améliorés
- Guide résolution problèmes dépendances

## [2.0.2] - 2025-01-13

### ✨ Ajouté
- **Option --no-media-scan** : Permet d'ignorer les scans des serveurs média
- **Script install-deps.sh** : Installation simplifiée des dépendances Python
- **Gestion des imports optionnels** : Le script fonctionne même si certains modules manquent
- **Configuration d'exemple améliorée** : Fichier .symguard_config.json.example détaillé
- **Documentation dépannage** : Section complète dans le README

### 🔧 Amélioré
- **Gestion des erreurs** : Imports optionnels pour psutil et requests
- **Robustesse du code** : Meilleure gestion des cas où les dépendances manquent
- **Messages informatifs** : Instructions claires quand les API keys sont manquantes
- **Performance optimisée** : Garbage collection amélioré et timeouts configurables
- **Configuration HTTP** : Pool de connexions et retry automatique

### 🐛 Corrigé
- **Imports manquants** : Ajout de gc et re dans les imports
- **Code incomplet** : Finalisation de toutes les fonctions
- **Gestion psutil** : Fonctionnement en fallback si psutil absent
- **Erreurs API keys** : Option pour ignorer les scans média
- **Permissions** : Vérification préalable des droits d'accès

### 🧹 Nettoyage
- **Code simplifié** : Suppression du code de migration et désinstallation
- **Structure allégée** : Focus sur les fonctionnalités principales
- **Documentation mise à jour** : Instructions d'installation et utilisation claires

## [2.0.1] - 2025-01-13

### ✨ Ajouté
- **Configuration interactive** : Commande `--config` pour configurer les serveurs média étape par étape
- **Création automatique de config** : Commande `--create-config` pour générer le fichier de configuration
- **Script d'installation** : `install.sh` pour installation automatisée (Ubuntu/Debian/CentOS/RHEL)
- **Auto-détection améliorée** : Détection automatique des clés API depuis les fichiers Docker
- **Gestion d'erreurs GitHub API** : Meilleure gestion des cas 404 et timeouts

### 🔧 Amélioré
- **Messages d'erreur** : Plus informatifs et contextuels
- **UX de configuration** : Interface pas à pas avec aide intégrée
- **Documentation** : README complet avec instructions détaillées
- **Gestion des sessions HTTP** : Retry automatique et timeouts configurés

### 🐛 Corrigé
- **Erreurs "API key manquante"** : Système de fallback et auto-détection
- **GitHub API 404** : Gestion propre quand aucune release n'existe
- **Permissions de fichiers** : Scripts d'installation avec permissions correctes

## [2.0.0] - 2025-01-12

### ✨ Ajouté
- **Intégration Media Server v2.0** : Support complet de Sonarr, Radarr, Bazarr, Prowlarr
- **Configuration JSON** : Système de configuration basé sur fichier `.symguard_config.json`
- **Scans automatiques** : Déclenchement des scans media après nettoyage
- **Sessions HTTP** : Gestion robuste avec retry et timeouts
- **Monitoring système** : Vérification des ressources avant scan

### 🔧 Amélioré
- **Architecture** : Refactorisation complète du code d'intégration media
- **Performance** : Optimisation pour serveurs multi-cœurs
- **Logging** : Système de logs rotatifs avec gestion d'espace
- **Rapports** : Formats JSON et logs détaillés

### 🗑️ Supprimé
- **Détection Docker** : Remplacée par le système de configuration JSON
- **Méthodes legacy** : Ancien code d'intégration media simplifié

## [1.9.x] - Versions antérieures

### Principales fonctionnalités héritées
- **Scan en 2 phases** : Vérification basique + ffprobe avancé
- **Mode dry-run/réel** : Sécurité avec confirmation avant suppression
- **Traitement parallèle** : Scan multi-threadé optimisé
- **Sélection interactive** : Choix des répertoires à scanner
- **Rapports détaillés** : Statistiques complètes et logs

---

## Format des versions

### Types de changements
- `✨ Ajouté` : Nouvelles fonctionnalités
- `🔧 Amélioré` : Améliorations de fonctionnalités existantes  
- `🐛 Corrigé` : Corrections de bugs
- `🗑️ Supprimé` : Fonctionnalités supprimées
- `🔒 Sécurité` : Corrections de vulnérabilités

### Numérotation sémantique
- **MAJOR** (X.0.0) : Changements incompatibles
- **MINOR** (0.X.0) : Nouvelles fonctionnalités compatibles
- **PATCH** (0.0.X) : Corrections de bugs compatibles
