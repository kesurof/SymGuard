# SymGuard v2.0.3: Scan intelligent individuel vs en masse

## 🎯 NOUVEAUTÉS MAJEURES

### ✨ Option scan individuel vs en masse
Choix lors de la confirmation de suppression entre :
- **Mode masse** : scan complet rapide (recommandé pour >100 fichiers)
- **Mode individuel** : notifications précises par fichier/titre (recommandé pour <50 fichiers)
- **Mode aucun** : désactiver ponctuellement les notifications

### 🧠 Analyse intelligente des fichiers média
- **Parsing automatique** des noms de séries (format SxxExx)
- **Détection des films** avec année (Movie.2023.mkv)
- **Reconnaissance** des structures de dossiers (/movies/, /series/, etc.)

### 🎯 Notifications ciblées
- **Sonarr** : rafraîchissement par série identifiée
- **Radarr** : rafraîchissement par film identifié
- **Optimisation** : évite les scans complets inutiles

## 🔧 AMÉLIORATIONS TECHNIQUES

- Ajout imports manquants (`gc`, `re`)
- Correction fonction `interactive_config_setup()` incomplète
- Gestion gracieuse des dépendances optionnelles (`psutil`, `requests`)
- Support fallback si modules non disponibles
- Nouvelle option `--no-media-scan` pour ignorer complètement
- Amélioration gestion d'erreurs API

## 🐛 CORRECTIONS DE BUGS

- Erreur "API key manquante" bloquant l'exécution
- Imports manquants causant des crashes
- Fonctions incomplètes dans le setup interactif
- Gestion d'erreur insuffisante pour dépendances

## 📊 PERFORMANCE

- **Mode masse** : scan complet rapide, idéal pour gros volumes
- **Mode individuel** : notifications précises mais plus lentes
- **Mode intelligent** : choix automatique selon le contexte

## 🎮 COMPATIBILITÉ

- **Sonarr v3+** (notifications par série)
- **Radarr v3+** (notifications par film)
- **Python 3.8+** avec fallbacks gracieux
- **Support** dépendances optionnelles (psutil, requests)

## 📚 DOCUMENTATION

- Section troubleshooting dans README.md
- Documentation option `--no-media-scan`
- Exemples de configuration améliorés
- Guide résolution problèmes dépendances
