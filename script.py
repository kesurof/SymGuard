#!/usr/bin/env python3

# SymGuard - Vérificateur Avancé de Liens Symboliques
# Version 2.0.3
# Optimisé pour serveurs Linux avec gestion des mises à jour
# Dernière optimisation: Corrections majeures et robustesse améliorée

import os
import subprocess
import json
import time
import logging
import argparse
import shutil
import glob
import gc
import re
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Version du script
SCRIPT_VERSION = "2.0.3"

# Détection automatique de l'utilisateur et environnement serveur
current_user = os.environ.get('USER', os.environ.get('USERNAME', 'user'))

# Configuration adaptée aux serveurs Linux
SERVER_CONFIG = {
    'max_workers': 8,  # Optimisé pour serveurs multi-cœurs
    'user': current_user,
    'home_dir': os.environ.get('HOME', f'/home/{current_user}'),
    'settings_source': os.environ.get('SETTINGS_SOURCE', f'/home/{current_user}/seedbox-compose'),
    'virtual_env': os.environ.get('VIRTUAL_ENV', f'/home/{current_user}/seedbox-compose/venv'),
    'python_executable': f'{os.environ.get("VIRTUAL_ENV", f"/home/{current_user}/seedbox-compose/venv")}/bin/python3'
}

# Configuration du logging avec rotation et gestion d'espace disque
log_file = os.path.join(SERVER_CONFIG['home_dir'], 'symlink_maintenance.log')

# Configuration du handler de fichier avec rotation optimisée
from logging.handlers import RotatingFileHandler
import gc

# Optimisation garbage collection pour gros volumes
gc.set_threshold(700, 10, 10)  # Réduction du seuil pour libérer plus souvent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(funcName)s] %(message)s',  # Ajout du nom de fonction
    handlers=[
        RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5),  # 5MB max, 5 backups (optimisé)
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AdvancedSymlinkChecker:
    def __init__(self, max_workers: int = None):
        # Utilise la config serveur ou la valeur par défaut optimisée
        self.max_workers = max_workers or SERVER_CONFIG['max_workers']
        self.user = SERVER_CONFIG['user']
        self.home_dir = SERVER_CONFIG['home_dir']
        self.settings_source = SERVER_CONFIG['settings_source']
        
        self.stats = {
            'total_analyzed': 0,
            'phase1_ok': 0,
            'phase1_broken': 0,
            'phase1_inaccessible': 0,
            'phase1_small': 0,
            'phase1_io_error': 0,
            'phase2_analyzed': 0,
            'phase2_corrupted': 0,
            'files_deleted': 0,
            'server_info': {
                'hostname': os.uname().nodename,
                'architecture': os.uname().machine,
                'user': self.user,
                'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
            }
        }
        self.deleted_files = []
        self.all_problems = []
        
        # Configuration des serveurs média adaptée au serveur
        self.media_config = self.load_media_config()
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Crée une session HTTP avec retry automatique et configuration optimisée"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3, 
            backoff_factor=1, 
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],  # Méthodes autorisées pour retry
            raise_on_status=False  # Évite les exceptions sur retry
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        # Timeout par défaut pour éviter les blocages
        session.timeout = 30
        return session
    
    def rotate_old_files(self, pattern: str, max_files: int = 3):
        """Rotation des anciens fichiers de logs et rapports"""
        try:
            files = glob.glob(pattern)
            if not files:
                return
            
            # Trier par date de modification (plus ancien en premier)
            files.sort(key=lambda x: os.path.getmtime(x))
            
            # Supprimer les fichiers en excès
            files_to_delete = files[:-max_files] if len(files) >= max_files else []
            
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    logger.info(f"Fichier ancien supprimé: {os.path.basename(file_path)}")
                except Exception as e:
                    logger.error(f"Erreur suppression {file_path}: {e}")
                    
        except Exception as e:
            logger.error(f"Erreur rotation fichiers {pattern}: {e}")
    
    def cleanup_old_logs(self):
        """Nettoie les anciens logs et rapports avec optimisation mémoire"""
        print("🧹 Nettoyage des anciens fichiers...")
        
        # Rotation des rapports JSON (garder 3)
        self.rotate_old_files("symlink_report_*.json", 3)
        
        # Rotation des logs de suppression (garder 3)
        self.rotate_old_files("deleted_files_*.log", 3)
        
        # Rotation des logs principaux (garder 3)
        self.rotate_old_files("symlink_maintenance*.log", 3)
        
        # Forcer le garbage collection après nettoyage
        gc.collect()
        logger.info("Nettoyage terminé avec libération mémoire")
    
    def choose_execution_mode(self) -> str:
        """Choix du mode d'exécution"""
        print("\n" + "="*60)
        print("🔧 MODE D'EXÉCUTION")
        print("="*60)
        print("1) DRY-RUN   → Détecte sans supprimer + scan Sonarr/Radarr")
        print("2) RÉEL      → Détecte et supprime + scan Sonarr/Radarr")
        
        while True:
            try:
                choice = input(f"\n👉 Votre choix (1-2): ").strip()
                if choice == '1':
                    print("✅ Mode DRY-RUN sélectionné")
                    return 'dry-run'
                elif choice == '2':
                    print("⚠️  Mode RÉEL sélectionné")
                    return 'real'
                else:
                    print("❌ Choix invalide. Utilisez 1 ou 2")
            except KeyboardInterrupt:
                print("\n❌ Opération annulée")
                exit(0)
    
    def list_directories_with_counts(self, base_path: str) -> Dict[str, int]:
        """Liste les répertoires avec le nombre de liens symboliques"""
        print(f"\n📊 Analyse des répertoires dans: {base_path}")
        directory_counts = {}
        
        if not os.path.exists(base_path):
            print(f"❌ Répertoire inexistant: {base_path}")
            return {}
        
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if os.path.isdir(item_path) and not item.startswith('.'):
                link_count = 0
                try:
                    for root, dirs, files in os.walk(item_path):
                        for name in files:
                            full_path = os.path.join(root, name)
                            if os.path.islink(full_path):
                                link_count += 1
                except Exception as e:
                    logger.warning(f"Erreur dans {item}: {e}")
                    link_count = -1
                
                directory_counts[item] = link_count
        
        return directory_counts
    
    def interactive_directory_selection(self, base_path: str) -> List[str]:
        """Sélection interactive des répertoires à scanner"""
        directory_counts = self.list_directories_with_counts(base_path)
        
        if not directory_counts:
            return [base_path]
        
        print("\n" + "="*60)
        print(f"📊 Répertoires disponibles dans {base_path}:")
        print("-" * 60)
        
        sorted_dirs = sorted(directory_counts.items(), key=lambda x: x[1], reverse=True)
        total_links = sum(count for count in directory_counts.values() if count > 0)
        
        for i, (dirname, count) in enumerate(sorted_dirs, 1):
            if count == -1:
                status = "❌ Erreur"
            elif count == 0:
                status = "⚪ Aucun lien"
            elif count < 100:
                status = f"🟢 {count:,} liens"
            elif count < 1000:
                status = f"🟡 {count:,} liens"
            else:
                status = f"🔴 {count:,} liens"
            
            print(f"{i:2d}. {dirname:<30} {status}")
        
        print("-" * 60)
        print(f"📈 Total: {total_links:,} liens symboliques")
        
        print(f"\n🎯 OPTIONS DE SÉLECTION:")
        print("  'all' ou 'a'     → Tout scanner")
        print("  '1,3,5'          → Scanner les répertoires 1, 3 et 5")
        print("  '1-5'            → Scanner les répertoires 1 à 5")
        print("  'big'            → Seulement les gros répertoires (>1000 liens)")
        print("  'small'          → Seulement les petits répertoires (<100 liens)")
        print("  'medium'         → Répertoires moyens (100-1000 liens)")
        print("  'exit' ou 'q'    → Annuler")
        
        while True:
            try:
                choice = input(f"\n👉 Votre choix: ").strip().lower()
                
                if choice in ['exit', 'q', '']:
                    print("❌ Scan annulé")
                    return []
                
                if choice in ['all', 'a']:
                    selected_dirs = [dirname for dirname, count in sorted_dirs if count > 0]
                    break
                
                elif choice == 'big':
                    selected_dirs = [dirname for dirname, count in sorted_dirs if count > 1000]
                    break
                
                elif choice == 'small':
                    selected_dirs = [dirname for dirname, count in sorted_dirs if 0 < count < 100]
                    break
                
                elif choice == 'medium':
                    selected_dirs = [dirname for dirname, count in sorted_dirs if 100 <= count <= 1000]
                    break
                
                elif '-' in choice:
                    start, end = map(int, choice.split('-'))
                    selected_indices = list(range(start-1, min(end, len(sorted_dirs))))
                    selected_dirs = [sorted_dirs[i][0] for i in selected_indices if sorted_dirs[i][1] > 0]
                    break
                
                elif ',' in choice:
                    indices = [int(x.strip()) - 1 for x in choice.split(',')]
                    selected_dirs = []
                    for idx in indices:
                        if 0 <= idx < len(sorted_dirs) and sorted_dirs[idx][1] > 0:
                            selected_dirs.append(sorted_dirs[idx][0])
                    break
                
                elif choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(sorted_dirs) and sorted_dirs[idx][1] > 0:
                        selected_dirs = [sorted_dirs[idx][0]]
                        break
                    else:
                        raise ValueError("Numéro invalide")
                
                else:
                    raise ValueError("Format non reconnu")
                    
            except (ValueError, IndexError):
                print("❌ Choix invalide. Utilisez le format indiqué (ex: 1,3,5 ou 1-5 ou 'all')")
                continue
        
        if not selected_dirs:
            print("❌ Aucun répertoire sélectionné")
            return []
        
        # Construire les chemins complets et afficher la sélection
        base_path = f"{self.home_dir}/Medias"  # Adapté au serveur
        selected_paths = [os.path.join(base_path, dirname) for dirname in selected_dirs]
        total_selected_links = sum(directory_counts[dirname] for dirname in selected_dirs)
        
        print(f"\n✅ Répertoires sélectionnés ({len(selected_dirs)}):")
        for dirname in selected_dirs:
            count = directory_counts[dirname]
            print(f"   📁 {dirname} ({count:,} liens)")
        
        print(f"\n📊 Total à scanner: {total_selected_links:,} liens symboliques")
        
        return selected_paths
    
    def check_ffprobe_and_estimate(self, selected_paths: List[str]) -> Tuple[bool, int, str]:
        """Vérifie ffprobe et estime le nombre de fichiers médias"""
        # Vérification de ffprobe
        try:
            result = subprocess.run(['ffprobe', '-version'], 
                                  stdout=subprocess.DEVNULL, 
                                  stderr=subprocess.DEVNULL, 
                                  check=True, timeout=5)
            ffprobe_available = True
            print("✅ ffprobe trouvé")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            ffprobe_available = False
            print("❌ ffprobe non trouvé")
            return False, 0, "unavailable"
        
        # Estimation du nombre de fichiers médias
        media_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', 
                          '.m4v', '.webm', '.mp3', '.flac', '.wav', '.aac'}
        media_count = 0
        
        print("📊 Estimation des fichiers médias...")
        for path in selected_paths:
            for root, dirs, files in os.walk(path):
                for name in files:
                    full_path = os.path.join(root, name)
                    if os.path.islink(full_path):
                        if Path(name).suffix.lower() in media_extensions:
                            media_count += 1
        
        # Estimation du temps (environ 1-2 secondes par fichier média)
        estimated_minutes = max(1, media_count // 30)  # 30 fichiers par minute
        time_str = f"~{estimated_minutes} min" if estimated_minutes < 60 else f"~{estimated_minutes//60}h{estimated_minutes%60}m"
        
        print(f"📊 ~{media_count:,} fichiers médias estimés ({time_str})")
        
        return ffprobe_available, media_count, time_str
    
    def choose_verification_depth(self, ffprobe_available: bool, time_estimate: str) -> str:
        """Choix de la profondeur de vérification"""
        print(f"\nOptions de vérification:")
        print(f"1) Basique seulement (30 sec)")
        
        if ffprobe_available:
            print(f"2) Basique + ffprobe complet ({time_estimate})")
            max_choice = 2
        else:
            print("2) [INDISPONIBLE] ffprobe non installé")
            max_choice = 1
        
        while True:
            try:
                choice = input(f"\n👉 Choix (1-{max_choice}): ").strip()
                if choice == '1':
                    return 'basic'
                elif choice == '2' and ffprobe_available:
                    return 'full'
                else:
                    print(f"❌ Choix invalide. Utilisez 1{' ou 2' if ffprobe_available else ''}")
            except KeyboardInterrupt:
                print("\n❌ Opération annulée")
                exit(0)
    
    def check_symlink_basic(self, path: str) -> Optional[Dict]:
        """Phase 1: Vérification basique d'un lien symbolique"""
        try:
            if not os.path.islink(path):
                return None
                
            target = os.readlink(path)
            
            # Test d'existence
            if not os.path.exists(path):
                return {
                    'path': path,
                    'target': target,
                    'status': 'BROKEN',
                    'phase': 1,
                    'size': 0
                }
            
            # Test d'accès
            if not os.access(path, os.R_OK):
                return {
                    'path': path,
                    'target': target,
                    'status': 'INACCESSIBLE',
                    'phase': 1,
                    'size': 0
                }
            
            # Test de taille et lecture
            try:
                file_size = os.path.getsize(path)
                if file_size < 1024:  # < 1KB suspect
                    return {
                        'path': path,
                        'target': target,
                        'status': 'SMALL_FILE',
                        'phase': 1,
                        'size': file_size
                    }
                
                # Test de lecture basique
                with open(path, 'rb') as f:
                    f.read(1024)  # Lecture test
                    
            except OSError as e:
                return {
                    'path': path,
                    'target': target,
                    'status': 'IO_ERROR',
                    'phase': 1,
                    'size': 0,
                    'error': str(e)
                }
            
            # Fichier OK pour la phase 1
            return {
                'path': path,
                'target': target,
                'status': 'OK',
                'phase': 1,
                'size': file_size
            }
            
        except Exception as e:
            return {
                'path': path,
                'target': '',
                'status': 'ERROR',
                'phase': 1,
                'size': 0,
                'error': str(e)
            }
    
    def check_ffprobe_validity(self, path: str) -> bool:
        """Phase 2: Vérification ffprobe d'un fichier média"""
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                "-of", "csv=p=0", path
            ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15)
            
            output = result.stdout.decode("utf-8").strip()
            if not output:
                return False
            if "video" not in output and "audio" not in output:
                return False
            return True
        except:
            return False
    
    def is_media_file(self, path: str) -> bool:
        """Vérifie si le fichier est un média par extension"""
        media_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', 
                          '.m4v', '.webm', '.mp3', '.flac', '.wav', '.aac'}
        return Path(path).suffix.lower() in media_extensions
    
    def phase1_scan(self, paths: List[str]) -> Tuple[List[Dict], List[Dict]]:
        """Phase 1: Scan basique de tous les liens"""
        print(f"\n🔍 PHASE 1 - SCAN BASIQUE")
        print("="*50)
        
        all_symlinks = []
        for path in paths:
            print(f"📂 Collecte des liens dans: {os.path.basename(path)}")
            for root, dirs, files in os.walk(path):
                for name in files:
                    full_path = os.path.join(root, name)
                    if os.path.islink(full_path):
                        all_symlinks.append(full_path)
        
        print(f"📊 {len(all_symlinks):,} liens symboliques trouvés")
        
        if not all_symlinks:
            return [], []
        
        # Traitement parallèle
        ok_files = []
        problem_files = []
        
        print("⚡ Vérification en cours...")
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_symlink = {executor.submit(self.check_symlink_basic, link): link for link in all_symlinks}
            
            completed = 0
            for future in as_completed(future_to_symlink):
                try:
                    result = future.result()
                    if result:
                        self.stats['total_analyzed'] += 1
                        completed += 1
                        
                        if result['status'] == 'OK':
                            ok_files.append(result)
                            self.stats['phase1_ok'] += 1
                        else:
                            problem_files.append(result)
                            if result['status'] == 'BROKEN':
                                self.stats['phase1_broken'] += 1
                            elif result['status'] == 'INACCESSIBLE':
                                self.stats['phase1_inaccessible'] += 1
                            elif result['status'] == 'SMALL_FILE':
                                self.stats['phase1_small'] += 1
                            elif result['status'] == 'IO_ERROR':
                                self.stats['phase1_io_error'] += 1
                            
                            print(f"[{result['status']}] {os.path.basename(result['path'])}")
                        
                        # Progression
                        if completed % 1000 == 0:
                            print(f"📈 Progression: {completed:,}/{len(all_symlinks):,}")
                            
                except Exception as e:
                    logger.error(f"Erreur lors du traitement: {e}")
        
        # Résumé Phase 1
        print(f"\n📊 RÉSULTATS PHASE 1:")
        print(f"✅ OK: {len(ok_files):,}")
        print(f"💔 Problèmes: {len(problem_files):,}")
        if problem_files:
            status_count = {}
            for pf in problem_files:
                status_count[pf['status']] = status_count.get(pf['status'], 0) + 1
            for status, count in status_count.items():
                print(f"   {status}: {count:,}")
        
        return ok_files, problem_files
    
    def phase2_scan(self, ok_files: List[Dict]) -> List[Dict]:
        """Phase 2: Scan ffprobe des fichiers médias OK"""
        print(f"\n🔍 PHASE 2 - VÉRIFICATION FFPROBE")
        print("="*50)
        
        # Filtrer les fichiers médias
        media_files = [f for f in ok_files if self.is_media_file(f['path'])]
        print(f"📊 {len(media_files):,} fichiers médias à vérifier")
        
        if not media_files:
            print("ℹ️ Aucun fichier média à vérifier")
            return []
        
        corrupted_files = []
        
        print("🔧 Vérification ffprobe en cours...")
        completed = 0
        
        for media_file in media_files:
            try:
                if not self.check_ffprobe_validity(media_file['path']):
                    corrupted_file = media_file.copy()
                    corrupted_file['status'] = 'CORRUPTED'
                    corrupted_file['phase'] = 2
                    corrupted_files.append(corrupted_file)
                    print(f"[CORRUPTED] {os.path.basename(media_file['path'])}")
                
                self.stats['phase2_analyzed'] += 1
                completed += 1
                
                # Progression
                if completed % 100 == 0:
                    print(f"📈 Progression: {completed:,}/{len(media_files):,}")
                    
            except KeyboardInterrupt:
                print(f"\n⚠️ Interruption utilisateur après {completed}/{len(media_files)} fichiers")
                break
            except Exception as e:
                logger.error(f"Erreur ffprobe sur {media_file['path']}: {e}")
        
        self.stats['phase2_corrupted'] = len(corrupted_files)
        
        print(f"\n📊 RÉSULTATS PHASE 2:")
        print(f"🔧 Analysés: {completed:,}/{len(media_files):,}")
        print(f"🔨 Corrompus: {len(corrupted_files):,}")
        
        return corrupted_files
    
    def confirm_deletion(self, all_problems: List[Dict]) -> Tuple[bool, str]:
        """Confirmation globale avant suppression avec choix du mode de scan"""
        if not all_problems:
            return False, 'mass'
        
        print(f"\n⚠️  MODE RÉEL - {len(all_problems):,} fichiers problématiques détectés")
        print("\nFICHIERS À SUPPRIMER:")
        
        # Grouper par type de problème
        problem_groups = {}
        for problem in all_problems:
            status = problem['status']
            problem_groups[status] = problem_groups.get(status, 0) + 1
        
        for status, count in problem_groups.items():
            status_names = {
                'BROKEN': 'liens cassés',
                'INACCESSIBLE': 'fichiers inaccessibles', 
                'SMALL_FILE': 'fichiers trop petits',
                'IO_ERROR': 'erreurs I/O',
                'CORRUPTED': 'fichiers corrompus (ffprobe)'
            }
            print(f"- {count:,} {status_names.get(status, status.lower())}")
        
        print(f"\nConfirmer la suppression de ces {len(all_problems):,} fichiers ? (y/N): ", end="")
        try:
            response = input().strip().lower()
            if response not in ['y', 'yes', 'o', 'oui']:
                print("\n❌ Suppression annulée")
                return False, 'mass'
        except KeyboardInterrupt:
            print("\n❌ Suppression annulée")
            return False, 'mass'
        
        # Choix du mode de scan des serveurs média
        print(f"\n🔄 MODE DE SCAN DES SERVEURS MÉDIA:")
        print("1) Scan en masse (rapide) - Lance un scan global")
        print("2) Scan individuel (lent) - Notifie chaque fichier supprimé")
        print("3) Pas de scan - Ignorer les serveurs média")
        
        while True:
            try:
                choice = input(f"\n👉 Votre choix (1-3): ").strip()
                if choice == '1':
                    print("✅ Mode scan en masse sélectionné")
                    return True, 'mass'
                elif choice == '2':
                    print("✅ Mode scan individuel sélectionné (plus lent)")
                    return True, 'individual'
                elif choice == '3':
                    print("✅ Scan des serveurs média désactivé")
                    return True, 'none'
                else:
                    print("❌ Choix invalide. Utilisez 1, 2 ou 3")
            except KeyboardInterrupt:
                print("\n❌ Suppression annulée")
                return False, 'mass'
    
    def delete_files(self, problem_files: List[Dict]) -> List[str]:
        """Supprime les fichiers problématiques et log les suppressions (version robuste)"""
        deleted_files = []
        
        print(f"\n🗑️ Suppression de {len(problem_files):,} fichiers...")
        
        for i, problem in enumerate(problem_files, 1):
            try:
                file_path = problem['path']
                file_deleted = False
                
                # Vérifier d'abord si c'est un lien symbolique (cassé ou non)
                if os.path.islink(file_path):
                    os.unlink(file_path)
                    file_deleted = True
                # Sinon vérifier si c'est un fichier normal qui existe
                elif os.path.exists(file_path):
                    os.remove(file_path)
                    file_deleted = True
                
                if file_deleted:
                    deleted_files.append({
                        'path': file_path,
                        'target': problem.get('target', ''),
                        'status': problem['status'],
                        'size': problem.get('size', 0),
                        'deleted_at': datetime.now().isoformat()
                    })
                    
                    if i % 100 == 0:
                        print(f"📈 Suppression: {i:,}/{len(problem_files):,}")
                else:
                    logger.warning(f"Fichier non trouvé pour suppression: {file_path}")
                            
            except Exception as e:
                logger.error(f"Erreur suppression {problem['path']}: {e}")
        
        self.stats['files_deleted'] = len(deleted_files)
        print(f"✅ {len(deleted_files):,} fichiers supprimés")
        
        return deleted_files
    
    def save_deletion_log(self, deleted_files: List[Dict]) -> str:
        """Sauvegarde le log des fichiers supprimés"""
        if not deleted_files:
            return ""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f"deleted_files_{timestamp}.log"
        
        with open(log_file, 'w') as f:
            f.write(f"# Fichiers supprimés - {datetime.now()}\n")
            f.write(f"# Total: {len(deleted_files)} fichiers\n\n")
            
            for item in deleted_files:
                f.write(f"[{item['status']}] {item['path']} -> {item['target']} ({item['size']} bytes)\n")
        
        print(f"📝 Log de suppression: {log_file}")
        return log_file
    
    def save_full_report(self, all_problems: List[Dict], mode: str) -> str:
        """Sauvegarde le rapport complet"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"symlink_report_{timestamp}.json"
        
        report = {
            'scan_date': datetime.now().isoformat(),
            'mode': mode,
            'statistics': self.stats,
            'problems_found': all_problems,
            'deleted_files': self.deleted_files if mode == 'real' else []
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Rapport complet: {report_file}")
        return report_file
    
    def load_media_config(self) -> Dict[str, Dict]:
        """Charge la configuration des serveurs média depuis un fichier de config ou utilise les valeurs par défaut"""
        config_file = os.path.join(self.home_dir, '.symguard_config.json')
        
        # Configuration par défaut basée sur des URLs standard
        default_config = {
            'sonarr': {
                'url': 'http://localhost:8989',
                'api_key': None,
                'enabled': True
            },
            'radarr': {
                'url': 'http://localhost:7878', 
                'api_key': None,
                'enabled': True
            },
            'bazarr': {
                'url': 'http://localhost:6767',
                'api_key': None,
                'enabled': True
            },
            'prowlarr': {
                'url': 'http://localhost:9696',
                'api_key': None,
                'enabled': True
            }
        }
        
        # Essayer de charger depuis le fichier de config existant
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Fusionner avec la config par défaut
                    for service in default_config:
                        if service in loaded_config:
                            default_config[service].update(loaded_config[service])
                logger.info(f"Configuration chargée depuis {config_file}")
            except Exception as e:
                logger.warning(f"Erreur lecture config {config_file}: {e}")
        
        return default_config
    
    def save_media_config(self, config: Dict[str, Dict]):
        """Sauvegarde la configuration des serveurs média"""
        config_file = os.path.join(self.home_dir, '.symguard_config.json')
        try:
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Configuration sauvegardée dans {config_file}")
        except Exception as e:
            logger.error(f"Erreur sauvegarde config: {e}")
    
    def get_service_url_and_key(self, service: str):
        """Récupère l'URL et la clé API d'un service
        Returns:
            Tuple[Optional[str], Optional[str]]: URL et clé API du service
        """
        # Charger la configuration
        media_config = self.load_media_config()
        service_config = media_config.get(service, {})
        
        if not service_config.get('enabled', True):
            return None, None
        
        url = service_config.get('url')
        api_key = service_config.get('api_key')
        
        # Si pas d'API key, essayer de la détecter automatiquement
        if not api_key:
            api_key = self._detect_api_key(service, url)
            if api_key:
                # Sauvegarder la clé détectée
                service_config['api_key'] = api_key
                media_config[service] = service_config
                self.save_media_config(media_config)
        
        return url, api_key
    
    def _detect_api_key(self, service: str, base_url: str) -> Optional[str]:
        """Essaie de détecter automatiquement l'API key depuis les fichiers de config"""
        try:
            # Chemins possibles pour les configurations
            config_paths = [
                f"{self.settings_source}/docker/{self.user}/{service}/config/config.xml",
                f"/opt/seedbox/docker/{self.user}/{service}/config/config.xml", 
                f"{self.home_dir}/.config/{service}/config.xml",
                f"/docker/{self.user}/{service}/config/config.xml",
                f"/home/{self.user}/seedbox-compose/includes/config/{service}/config.xml"
            ]
            
            for config_path in config_paths:
                if os.path.exists(config_path):
                    try:
                        # Lecture directe du fichier XML
                        with open(config_path, 'r') as f:
                            content = f.read()
                            import re
                            match = re.search(r'<ApiKey>([^<]+)</ApiKey>', content)
                            if match:
                                api_key = match.group(1)
                                if len(api_key) > 10:
                                    logger.info(f"API key détectée pour {service} dans {config_path}")
                                    return api_key
                    except Exception as e:
                        logger.debug(f"Erreur lecture {config_path}: {e}")
                        continue
            
            logger.debug(f"Aucune API key automatiquement détectée pour {service}")
            return None
            
        except Exception as e:
            logger.error(f"Erreur détection API key {service}: {e}")
            return None
    
    def trigger_media_scans(self):
        """Déclenche les scans Sonarr/Radarr/Bazarr/Prowlarr avec configuration améliorée"""
        print(f"\n🔄 Déclenchement des scans serveurs média...")
        print(f"💡 Utilisez --no-media-scan pour ignorer cette étape")
        
        scan_results = {}
        
        # Vérifier d'abord si au moins un service a une config valide
        has_valid_config = False
        for service in ['sonarr', 'radarr', 'bazarr', 'prowlarr']:
            url, api_key = self.get_service_url_and_key(service)
            if url and api_key:
                has_valid_config = True
                break
        
        if not has_valid_config:
            print("⚠️ Aucune configuration valide trouvée pour les serveurs média")
            print("💡 Utilisez --config pour configurer ou --create-config pour créer le fichier")
            return {}
        
        # Services disponibles avec leurs commandes
        services_commands = {
            'sonarr': [
                {'name': 'RescanSeries', 'desc': 'Scan séries'},
                {'name': 'MissingEpisodeSearch', 'desc': 'Recherche épisodes manquants'}
            ],
            'radarr': [
                {'name': 'RescanMovie', 'desc': 'Scan films'},
                {'name': 'MissingMoviesSearch', 'desc': 'Recherche films manquants'}
            ],
            'bazarr': [
                {'name': 'SeriesSearchMissing', 'desc': 'Recherche sous-titres séries'},
                {'name': 'MoviesSearchMissing', 'desc': 'Recherche sous-titres films'}
            ],
            'prowlarr': [
                {'name': 'IndexerSearch', 'desc': 'Test indexeurs'}
            ]
        }
        
        for service in services_commands.keys():
            scan_results[service] = {'status': 'unknown', 'commands': []}
            
            try:
                # Récupérer URL et API key
                url, api_key = self.get_service_url_and_key(service)
                
                if not url:
                    print(f"⚠️ {service}: service désactivé")
                    scan_results[service]['status'] = 'disabled'
                    continue
                    
                if not api_key:
                    print(f"⚠️ {service}: API key manquante")
                    print(f"   💡 Configurez manuellement dans ~/.symguard_config.json")
                    scan_results[service]['status'] = 'no_api_key'
                    continue
                
                # Test de connexion
                headers = {"Content-Type": "application/json", "X-Api-Key": api_key}
                
                try:
                    test_response = self.session.get(f"{url}/api/v3/system/status", headers=headers, timeout=10)
                    if test_response.status_code != 200:
                        print(f"⚠️ {service}: connexion échouée (HTTP {test_response.status_code})")
                        scan_results[service]['status'] = 'connection_failed'
                        continue
                except Exception as e:
                    print(f"⚠️ {service}: connexion impossible ({str(e)})")
                    scan_results[service]['status'] = 'connection_error'
                    continue
                
                # Exécuter les commandes
                successful_commands = []
                service_commands = services_commands.get(service, [])
                
                for command_info in service_commands:
                    try:
                        command = command_info['name']
                        description = command_info['desc']
                        
                        data = {"name": command}
                        response = self.session.post(f"{url}/api/v3/command", json=data, headers=headers, timeout=30)
                        response.raise_for_status()
                        
                        print(f"✅ {service}: {description} lancé")
                        successful_commands.append(command)
                        time.sleep(2)  # Pause entre commandes
                        
                    except requests.exceptions.RequestException as e:
                        print(f"❌ {service} ({command}): {e}")
                        logger.error(f"Erreur commande {service}/{command}: {e}")
                
                scan_results[service] = {
                    'status': 'success' if successful_commands else 'failed',
                    'commands': successful_commands,
                    'url': url
                }
                    
            except Exception as e:
                print(f"❌ {service}: erreur générale - {e}")
                scan_results[service]['status'] = 'error'
                logger.error(f"Erreur générale {service}: {e}")
        
        # Résumé des scans
        print(f"\n📊 Résumé des scans média:")
        for service, result in scan_results.items():
            status = result['status']
            if status == 'success':
                print(f"✅ {service}: {len(result['commands'])} commandes exécutées")
            elif status == 'disabled':
                print(f"⏭️ {service}: désactivé")
            elif status == 'no_api_key':
                print(f"⚠️ {service}: API key manquante")
            elif status == 'connection_failed':
                print(f"⚠️ {service}: connexion échouée")
            elif status == 'connection_error':
                print(f"⚠️ {service}: erreur de connexion")
            else:
                print(f"❌ {service}: échec")
        
        # Afficher les instructions de configuration si nécessaire
        missing_config = [s for s, r in scan_results.items() if r['status'] == 'no_api_key']
        if missing_config:
            self._show_config_instructions(missing_config)
        
        return scan_results
    
    def _show_config_instructions(self, missing_services):
        """Affiche les instructions de configuration"""
        print(f"\n📝 CONFIGURATION REQUISE")
        print("="*50)
        print(f"Pour activer les scans des services manquants, créez le fichier:")
        print(f"📁 {self.home_dir}/.symguard_config.json")
        print(f"\nContenu exemple:")
        
        example_config = {}
        for service in missing_services:
            if service in ['sonarr', 'radarr']:
                example_config[service] = {
                    "url": f"http://localhost:{8989 if service == 'sonarr' else 7878}",
                    "api_key": f"your_{service}_api_key_here",
                    "enabled": True
                }
            elif service == 'bazarr':
                example_config[service] = {
                    "url": "http://localhost:6767",
                    "api_key": f"your_{service}_api_key_here", 
                    "enabled": True
                }
            elif service == 'prowlarr':
                example_config[service] = {
                    "url": "http://localhost:9696",
                    "api_key": f"your_{service}_api_key_here",
                    "enabled": True
                }
        
        print(json.dumps(example_config, indent=2))
        print(f"\n💡 Trouvez vos API keys dans les paramètres de chaque application")
    
    def print_final_summary(self, mode: str):
        """Affiche le résumé final avec informations serveur"""
        print("\n" + "="*60)
        print("📊 RÉSUMÉ FINAL")
        print("="*60)
        print(f"🖥️ Serveur: {self.stats['server_info']['hostname']} ({self.stats['server_info']['architecture']})")
        print(f"👤 Utilisateur: {self.stats['server_info']['user']}")
        print(f"🐍 Python: {self.stats['server_info']['python_version']}")
        print(f"⚙️ Workers: {self.max_workers}")
        print(f"📁 Mode: {mode.upper()}")
        
        print(f"\n=== PHASE 1 (tests basiques) ===")
        print(f"Total analysé: {self.stats['total_analyzed']:,}")
        print(f"✅ OK: {self.stats['phase1_ok']:,}")
        print(f"💔 Liens cassés: {self.stats['phase1_broken']:,}")
        print(f"🚫 Inaccessibles: {self.stats['phase1_inaccessible']:,}")
        print(f"📁 Fichiers vides: {self.stats['phase1_small']:,}")
        print(f"⚠️ Erreurs I/O: {self.stats['phase1_io_error']:,}")
        
        if self.stats['phase2_analyzed'] > 0:
            print(f"\n=== PHASE 2 (vérification ffprobe) ===")
            print(f"Analysés: {self.stats['phase2_analyzed']:,}")
            print(f"🔨 Corrompus: {self.stats['phase2_corrupted']:,}")
            if self.stats['phase2_analyzed'] > 0:
                corruption_rate = (self.stats['phase2_corrupted'] / self.stats['phase2_analyzed']) * 100
                print(f"Taux de corruption: {corruption_rate:.1f}%")
        
        total_problems = (self.stats['phase1_broken'] + self.stats['phase1_inaccessible'] + 
                         self.stats['phase1_small'] + self.stats['phase1_io_error'] + 
                         self.stats['phase2_corrupted'])
        
        if mode == 'real' and self.stats['files_deleted'] > 0:
            print(f"\n=== SUPPRESSIONS ===")
            print(f"🗑️ Fichiers supprimés: {self.stats['files_deleted']:,}")
        
        print(f"\n=== TOTAL ===")
        if total_problems > 0:
            print(f"⚠️ PROBLÈMES TROUVÉS: {total_problems:,}")
        else:
            print(f"🎉 AUCUN PROBLÈME DÉTECTÉ!")
        
        # Informations système
        print(f"\n=== SYSTÈME ===")
        print(f"💾 Logs: {log_file}")
        print(f"🏠 Home: {self.home_dir}")
        print(f"⚙️ Settings: {self.settings_source}")
    
    def check_system_resources(self) -> Dict[str, any]:
        """Vérifie l'état des ressources système avant le scan"""
        resources = {
            'memory': {'available': False, 'usage': 0},
            'disk': {'available': False, 'usage': 0},
            'load': {'average': 0, 'acceptable': False},
            'ffprobe': {'available': False, 'version': ''}
        }
        
        try:
            # Vérification mémoire (optionnel)
            try:
                import psutil
                memory = psutil.virtual_memory()
                resources['memory'] = {
                    'available': memory.available > 1024**3,  # > 1GB disponible
                    'usage': memory.percent,
                    'available_gb': memory.available / (1024**3)
                }
                
                # Vérification espace disque
                disk = psutil.disk_usage(self.home_dir)
                resources['disk'] = {
                    'available': disk.free > 5 * 1024**3,  # > 5GB libre
                    'usage': (disk.used / disk.total) * 100,
                    'free_gb': disk.free / (1024**3)
                }
            except ImportError:
                logger.debug("psutil non disponible - monitoring système limité")
                resources['memory'] = {'available': True, 'usage': 0, 'available_gb': 'unknown'}
                resources['disk'] = {'available': True, 'usage': 0, 'free_gb': 'unknown'}
            
            # Charge système
            try:
                load_avg = os.getloadavg()[0]  # 1 minute
                resources['load'] = {
                    'average': load_avg,
                    'acceptable': load_avg < 2.0  # Acceptable pour 4 cœurs
                }
            except (OSError, AttributeError):
                resources['load'] = {'average': 0, 'acceptable': True}
            
        except ImportError:
            # Fallback si psutil non disponible
            try:
                # Méthode basique pour la charge
                with open('/proc/loadavg', 'r') as f:
                    load_avg = float(f.read().split()[0])
                    resources['load'] = {
                        'average': load_avg,
                        'acceptable': load_avg < 2.0
                    }
            except:
                pass
        
        # Vérification ffprobe
        try:
            result = subprocess.run(['ffprobe', '-version'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.DEVNULL, 
                                  timeout=5)
            if result.returncode == 0:
                version_line = result.stdout.decode().split('\n')[0]
                resources['ffprobe'] = {
                    'available': True,
                    'version': version_line.split()[-1] if version_line else 'unknown'
                }
        except:
            resources['ffprobe'] = {'available': False, 'version': ''}
        
        return resources
    
    def print_system_status(self):
        """Affiche l'état du système avant le scan"""
        print(f"\n🔍 VÉRIFICATION SYSTÈME")
        print("="*50)
        
        resources = self.check_system_resources()
        
        # Mémoire
        if 'available_gb' in resources['memory']:
            status = "✅" if resources['memory']['available'] else "⚠️"
            print(f"{status} Mémoire: {resources['memory']['usage']:.1f}% utilisée, "
                  f"{resources['memory']['available_gb']:.1f}GB disponible")
        
        # Disque
        if 'free_gb' in resources['disk']:
            status = "✅" if resources['disk']['available'] else "⚠️"
            print(f"{status} Disque: {resources['disk']['usage']:.1f}% utilisé, "
                  f"{resources['disk']['free_gb']:.1f}GB libre")
        
        # Charge système
        if resources['load']['average']:
            status = "✅" if resources['load']['acceptable'] else "⚠️"
            print(f"{status} Charge: {resources['load']['average']:.2f} "
                  f"({'acceptable' if resources['load']['acceptable'] else 'élevée'})")
        
        # ffprobe
        status = "✅" if resources['ffprobe']['available'] else "❌"
        version = f" ({resources['ffprobe']['version']})" if resources['ffprobe']['version'] else ""
        print(f"{status} ffprobe: {'disponible' if resources['ffprobe']['available'] else 'non trouvé'}{version}")
        
        # Recommandations
        warnings = []
        if not resources['memory'].get('available', True):
            warnings.append("Mémoire faible - réduisez le nombre de workers")
        if not resources['disk'].get('available', True):
            warnings.append("Espace disque faible - vérifiez les logs")
        if not resources['load'].get('acceptable', True):
            warnings.append("Charge système élevée - reportez le scan")
        
        if warnings:
            print(f"\n⚠️ RECOMMANDATIONS:")
            for warning in warnings:
                print(f"   • {warning}")
        else:
            print(f"\n✅ Système prêt pour le scan")
        
        return resources

    def check_for_updates(self):
        """Vérifie s'il y a des mises à jour disponibles sur GitHub"""
        try:
            # Vérifier si requests est disponible
            try:
                import requests
            except ImportError:
                print("⚠️ Module 'requests' non disponible - vérification des mises à jour ignorée")
                print("💡 Installez-le avec: pip3 install --user requests")
                return False
            
            # Version actuelle
            current_version = SCRIPT_VERSION
            
            # Récupérer la dernière version depuis GitHub API
            api_url = "https://api.github.com/repos/kesurof/SymGuard/releases/latest"
            
            print(f"\n🔍 Vérification des mises à jour...")
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                latest_release = response.json()
                latest_version = latest_release.get('tag_name', '').lstrip('v')
                
                if latest_version and latest_version != current_version:
                    print(f"🆕 Nouvelle version disponible: v{latest_version} (actuelle: v{current_version})")
                    print(f"📝 Notes: {latest_release.get('name', 'Pas de description')}")
                    
                    # Proposer la mise à jour
                    try:
                        update = input("Voulez-vous mettre à jour maintenant ? (y/N): ").strip().lower()
                        if update in ['y', 'yes', 'o', 'oui']:
                            self.update_script()
                            return True
                    except KeyboardInterrupt:
                        print("\n⏭️ Mise à jour ignorée")
                else:
                    print(f"✅ Version actuelle (v{current_version}) - à jour")
            elif response.status_code == 404:
                print(f"📦 Aucune release disponible sur GitHub pour le moment")
                print(f"✅ Version actuelle: v{current_version}")
            else:
                print(f"⚠️ Impossible de vérifier les mises à jour (GitHub API: {response.status_code})")
                
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Erreur de connexion pour la vérification des mises à jour: {e}")
        except Exception as e:
            print(f"⚠️ Erreur vérification mise à jour: {e}")
        
        return False
    
    def update_script(self):
        """Met à jour le script depuis GitHub"""
        try:
            install_dir = "/home/kesurof/scripts"
            update_script = f"{install_dir}/update-symguard.sh"
            
            if os.path.exists(update_script):
                print(f"🔄 Exécution du script de mise à jour...")
                result = subprocess.run([update_script], check=True)
                print(f"✅ Mise à jour terminée ! Relancez le script.")
                exit(0)
            else:
                print(f"❌ Script de mise à jour non trouvé: {update_script}")
                print(f"💡 Relancez l'installation: cd {install_dir}/SymGuard && ./setup.sh")
                
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour: {e}")
    
    def create_default_config(self):
        """Crée un fichier de configuration par défaut"""
        config_file = os.path.join(self.home_dir, '.symguard_config.json')
        example_file = os.path.join(os.path.dirname(__file__), '.symguard_config.json.example')
        
        if os.path.exists(config_file):
            return False  # Fichier déjà existant
        
        print(f"\n📝 Création du fichier de configuration...")
        print(f"📁 Emplacement: {config_file}")
        
        default_config = {
            "sonarr": {
                "url": "http://localhost:8989",
                "api_key": "",
                "enabled": True
            },
            "radarr": {
                "url": "http://localhost:7878",
                "api_key": "",
                "enabled": True
            },
            "bazarr": {
                "url": "http://localhost:6767",
                "api_key": "",
                "enabled": True
            },
            "prowlarr": {
                "url": "http://localhost:9696",
                "api_key": "",
                "enabled": True
            }
        }
        
        try:
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            
            print(f"✅ Fichier créé avec succès!")
            print(f"💡 Éditez-le pour ajouter vos clés API:")
            print(f"   nano {config_file}")
            
            if os.path.exists(example_file):
                print(f"📖 Consultez l'exemple: {example_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur création fichier: {e}")
            return False

    def interactive_config_setup(self):
        """Configuration interactive des serveurs média"""
        config_file = os.path.join(self.home_dir, '.symguard_config.json')
        
        print(f"\n⚙️ CONFIGURATION INTERACTIVE")
        print("="*50)
        
        if os.path.exists(config_file):
            print(f"📁 Configuration existante trouvée: {config_file}")
            try:
                response = input("Voulez-vous la reconfigurer ? (y/N): ").strip().lower()
                if response not in ['y', 'yes', 'o', 'oui']:
                    return False
            except KeyboardInterrupt:
                print("\n⏭️ Configuration ignorée")
                return False
        
        # Charger la config existante ou créer une nouvelle
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
            else:
                config = self.load_media_config()
        except:
            config = self.load_media_config()
        
        services = ['sonarr', 'radarr', 'bazarr', 'prowlarr']
        default_ports = {'sonarr': 8989, 'radarr': 7878, 'bazarr': 6767, 'prowlarr': 9696}
        
        print(f"\nConfiguration des services média:")
        print(f"💡 Laissez vide pour conserver la valeur actuelle")
        print(f"💡 Utilisez 'disable' pour désactiver un service")
        
        for service in services:
            print(f"\n--- {service.upper()} ---")
            service_config = config.get(service, {})
            current_url = service_config.get('url', f'http://localhost:{default_ports[service]}')
            current_enabled = service_config.get('enabled', True)
            
            try:
                # URL
                new_url = input(f"URL [{current_url}]: ").strip()
                if new_url:
                    service_config['url'] = new_url
                else:
                    service_config['url'] = current_url
                    service_config['url'] = current_url
                
                # Activation/désactivation
                if current_enabled:
                    enable = input(f"Activer ce service ? [Y/n]: ").strip().lower()
                    service_config['enabled'] = enable not in ['n', 'no', 'non', 'disable']
                else:
                    enable = input(f"Activer ce service ? [y/N]: ").strip().lower()
                    service_config['enabled'] = enable in ['y', 'yes', 'o', 'oui']
                
                # Clé API si activé
                if service_config['enabled']:
                    current_key = service_config.get('api_key', '')
                    key_display = f"[{current_key[:8]}...]" if current_key else "[non configurée]"
                    new_key = input(f"Clé API {key_display}: ").strip()
                    if new_key:
                        service_config['api_key'] = new_key
                    elif not current_key:
                        # Essayer de détecter automatiquement
                        detected_key = self._detect_api_key(service, service_config['url'])
                        if detected_key:
                            print(f"✅ Clé API détectée automatiquement")
                            service_config['api_key'] = detected_key
                        else:
                            print(f"⚠️ Aucune clé API détectée automatiquement")
                            service_config['api_key'] = ""
                else:
                    service_config['api_key'] = ""
                
                config[service] = service_config
                
            except KeyboardInterrupt:
                print(f"\n⏭️ Configuration de {service} ignorée")
                continue
        
        # Sauvegarder
        try:
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"\n✅ Configuration sauvegardée dans {config_file}")
            
            # Afficher un résumé
            print(f"\n📊 Résumé de la configuration:")
            for service, service_config in config.items():
                if service_config.get('enabled', False):
                    has_key = "✅" if service_config.get('api_key') else "⚠️"
                    print(f"  {service}: {service_config['url']} {has_key}")
                else:
                    print(f"  {service}: désactivé")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde: {e}")
            return False

    def parse_media_file_info(self, file_path: str) -> Dict[str, any]:
        """Analyse un chemin de fichier pour extraire les informations série/film"""
        path_parts = Path(file_path).parts
        
        # Recherche de patterns dans le chemin
        info = {
            'type': 'unknown',
            'series_name': None,
            'season': None,
            'episode': None,
            'movie_name': None,
            'year': None
        }
        
        path_str = str(file_path).lower()
        
        # Détection série (patterns courants)
        import re
        
        # Pattern série avec saison/épisode
        series_pattern = r'(.*?)[\s\.]s(\d{2})e(\d{2})'
        series_match = re.search(series_pattern, path_str)
        
        if series_match:
            info['type'] = 'series'
            info['series_name'] = series_match.group(1).replace('.', ' ').replace('_', ' ').strip()
            info['season'] = int(series_match.group(2))
            info['episode'] = int(series_match.group(3))
        else:
            # Pattern film avec année
            movie_pattern = r'(.*?)[\s\.](\d{4})[\s\.]'
            movie_match = re.search(movie_pattern, path_str)
            
            if movie_match:
                info['type'] = 'movie'
                info['movie_name'] = movie_match.group(1).replace('.', ' ').replace('_', ' ').strip()
                info['year'] = int(movie_match.group(2))
            else:
                # Essayer de détecter depuis le répertoire parent
                if 'movies' in path_str or 'films' in path_str:
                    info['type'] = 'movie'
                    # Prendre le nom du fichier sans extension
                    info['movie_name'] = Path(file_path).stem
                elif 'series' in path_str or 'tv' in path_str or 'shows' in path_str:
                    info['type'] = 'series'
                    # Chercher dans les parties du chemin
                    for part in path_parts:
                        if 'season' in part.lower() or 's0' in part.lower():
                            info['series_name'] = path_parts[path_parts.index(part) - 1] if path_parts.index(part) > 0 else None
                            break
        
        return info

    def notify_media_servers_individual(self, deleted_files: List[Dict]) -> Dict[str, int]:
        """Notifie individuellement les serveurs média pour chaque fichier supprimé"""
        print(f"\n🔄 Notification individuelle des serveurs média...")
        print(f"📊 {len(deleted_files):,} fichiers à traiter")
        
        results = {
            'sonarr_series_refreshed': 0,
            'radarr_movies_refreshed': 0,
            'total_notifications': 0,
            'errors': 0
        }
        
        # Grouper les fichiers par type et nom
        series_to_refresh = set()
        movies_to_refresh = set()
        
        print("🔍 Analyse des fichiers supprimés...")
        for deleted_file in deleted_files:
            file_path = deleted_file['path']
            media_info = self.parse_media_file_info(file_path)
            
            if media_info['type'] == 'series' and media_info['series_name']:
                series_to_refresh.add(media_info['series_name'])
            elif media_info['type'] == 'movie' and media_info['movie_name']:
                movies_to_refresh.add(media_info['movie_name'])
        
        print(f"📺 {len(series_to_refresh)} séries à rafraîchir")
        print(f"🎬 {len(movies_to_refresh)} films à rafraîchir")
        
        # Notifier Sonarr pour les séries
        if series_to_refresh:
            results['sonarr_series_refreshed'] = self._refresh_sonarr_series(series_to_refresh)
        
        # Notifier Radarr pour les films
        if movies_to_refresh:
            results['radarr_movies_refreshed'] = self._refresh_radarr_movies(movies_to_refresh)
        
        results['total_notifications'] = results['sonarr_series_refreshed'] + results['radarr_movies_refreshed']
        
        print(f"\n📊 Résumé notifications individuelles:")
        print(f"✅ Séries rafraîchies: {results['sonarr_series_refreshed']}")
        print(f"✅ Films rafraîchis: {results['radarr_movies_refreshed']}")
        print(f"📈 Total: {results['total_notifications']} notifications")
        
        return results

    def _refresh_sonarr_series(self, series_names: set) -> int:
        """Rafraîchit individuellement les séries dans Sonarr"""
        try:
            # Vérifier si requests est disponible
            try:
                import requests
            except ImportError:
                print("⚠️ Module 'requests' non disponible pour Sonarr")
                return 0
            
            url, api_key = self.get_service_url_and_key('sonarr')
            if not url or not api_key:
                print("⚠️ Sonarr non configuré")
                return 0
            
            headers = {"Content-Type": "application/json", "X-Api-Key": api_key}
            refreshed = 0
            
            # Récupérer la liste des séries Sonarr
            try:
                response = self.session.get(f"{url}/api/v3/series", headers=headers, timeout=10)
                if response.status_code != 200:
                    print(f"⚠️ Impossible de récupérer la liste Sonarr")
                    return 0
                
                sonarr_series = response.json()
                
                for series_name in series_names:
                    # Chercher la série dans Sonarr
                    for series in sonarr_series:
                        if series_name.lower() in series['title'].lower():
                            # Rafraîchir cette série
                            refresh_data = {"name": "RefreshSeries", "seriesId": series['id']}
                            refresh_response = self.session.post(f"{url}/api/v3/command", 
                                                               json=refresh_data, 
                                                               headers=headers, 
                                                               timeout=10)
                            if refresh_response.status_code in [200, 201]:
                                print(f"✅ Sonarr: {series['title']} rafraîchi")
                                refreshed += 1
                            else:
                                print(f"⚠️ Sonarr: Erreur rafraîchissement {series['title']}")
                            break
                    else:
                        print(f"⚠️ Série non trouvée dans Sonarr: {series_name}")
                
            except Exception as e:
                print(f"❌ Erreur communication Sonarr: {e}")
                
        except Exception as e:
            print(f"❌ Erreur générale Sonarr: {e}")
        
        return refreshed

    def _refresh_radarr_movies(self, movie_names: set) -> int:
        """Rafraîchit individuellement les films dans Radarr"""
        try:
            # Vérifier si requests est disponible
            try:
                import requests
            except ImportError:
                print("⚠️ Module 'requests' non disponible pour Radarr")
                return 0
            
            url, api_key = self.get_service_url_and_key('radarr')
            if not url or not api_key:
                print("⚠️ Radarr non configuré")
                return 0
            
            headers = {"Content-Type": "application/json", "X-Api-Key": api_key}
            refreshed = 0
            
            # Récupérer la liste des films Radarr
            try:
                response = self.session.get(f"{url}/api/v3/movie", headers=headers, timeout=10)
                if response.status_code != 200:
                    print(f"⚠️ Impossible de récupérer la liste Radarr")
                    return 0
                
                radarr_movies = response.json()
                
                for movie_name in movie_names:
                    # Chercher le film dans Radarr
                    for movie in radarr_movies:
                        if movie_name.lower() in movie['title'].lower():
                            # Rafraîchir ce film
                            refresh_data = {"name": "RefreshMovie", "movieId": movie['id']}
                            refresh_response = self.session.post(f"{url}/api/v3/command", 
                                                               json=refresh_data, 
                                                               headers=headers, 
                                                               timeout=10)
                            if refresh_response.status_code in [200, 201]:
                                print(f"✅ Radarr: {movie['title']} rafraîchi")
                                refreshed += 1
                            else:
                                print(f"⚠️ Radarr: Erreur rafraîchissement {movie['title']}")
                            break
                    else:
                        print(f"⚠️ Film non trouvé dans Radarr: {movie_name}")
                
            except Exception as e:
                print(f"❌ Erreur communication Radarr: {e}")
                
        except Exception as e:
            print(f"❌ Erreur générale Radarr: {e}")
        
        return refreshed
def main():
    parser = argparse.ArgumentParser(description='Vérificateur avancé de liens symboliques - 2 phases')
    parser.add_argument('path', nargs='?', default=f'{SERVER_CONFIG["home_dir"]}/Medias', 
                       help=f'Répertoire de base à scanner (défaut: {SERVER_CONFIG["home_dir"]}/Medias)')
    parser.add_argument('-j', '--jobs', type=int, default=SERVER_CONFIG['max_workers'], 
                       help=f'Nombre de workers parallèles (défaut: {SERVER_CONFIG["max_workers"]} - détection automatique)')
    parser.add_argument('--dry-run', action='store_true', help='Force le mode dry-run')
    parser.add_argument('--real', action='store_true', help='Force le mode réel')
    parser.add_argument('--quick', action='store_true', help='Scan basique uniquement')
    parser.add_argument('--no-update-check', action='store_true', help='Ignorer la vérification de mise à jour')
    parser.add_argument('--no-media-scan', action='store_true', help='Ignorer les scans des serveurs média')
    parser.add_argument('--config', action='store_true', help='Configuration interactive des serveurs média')
    parser.add_argument('--create-config', action='store_true', help='Créer un fichier de configuration par défaut')
    parser.add_argument('--version', action='version', version=f'SymGuard v{SCRIPT_VERSION}')
    
    args = parser.parse_args()
    
    # Gestion des commandes spéciales
    checker = AdvancedSymlinkChecker(max_workers=args.jobs)
    
    if args.create_config:
        if checker.create_default_config():
            print("\n💡 Éditez maintenant le fichier pour ajouter vos clés API")
        return 0
    
    if args.config:
        checker.interactive_config_setup()
        return 0
    
    print("🚀 Vérificateur avancé de liens symboliques - 2 phases")
    print(f"🖥️ Serveur: {os.uname().nodename} ({os.uname().machine})")
    print(f"👤 Utilisateur: {SERVER_CONFIG['user']}")
    print(f"📁 Répertoire de base: {args.path}")
    print(f"⚡ Workers parallèles: {args.jobs}")
    print(f"🐍 Python: {SERVER_CONFIG['python_executable']}")
    
    # Vérifications préliminaires
    if not os.path.exists(args.path):
        print(f"❌ Répertoire inexistant: {args.path}")
        return 1
    
    if not os.access(args.path, os.R_OK):
        print(f"❌ Pas d'accès en lecture: {args.path}")
        return 1
    
    try:
        # Vérification des mises à jour (sauf si --no-update-check)
        if not args.no_update_check:
            if checker.check_for_updates():
                return 0  # Script mis à jour, arrêter l'exécution actuelle
        
        # 0. Vérification système
        system_resources = checker.print_system_status()
        
        # 1. Nettoyage des anciens logs
        checker.cleanup_old_logs()
        
        # 1. Choix du mode d'exécution
        if args.dry_run:
            mode = 'dry-run'
            print("✅ Mode DRY-RUN forcé par --dry-run")
        elif args.real:
            mode = 'real'
            print("⚠️ Mode RÉEL forcé par --real")
        else:
            mode = checker.choose_execution_mode()
        
        # 2. Vérification interactive des répertoires
        selected_paths = checker.interactive_directory_selection(args.path)
        if not selected_paths:
            print("❌ Aucun répertoire sélectionné, arrêt")
            return 1
        
        # 2. Vérification préalable des permissions
        print("\n🔐 Vérification des permissions...")
        for path in [args.path]:
            if not os.access(path, os.R_OK):
                print(f"❌ Pas d'accès en lecture: {path}")
                return 1
            if mode == 'real' and not os.access(path, os.W_OK):
                print(f"❌ Pas d'accès en écriture (requis pour mode réel): {path}")
                return 1
        print("✅ Permissions vérifiées")
        
        # 3. Vérification ffprobe et choix de profondeur
        if args.quick:
            verification_depth = 'basic'
            print("✅ Scan basique forcé par --quick")
        else:
            ffprobe_available, media_count, time_estimate = checker.check_ffprobe_and_estimate(selected_paths)
            verification_depth = checker.choose_verification_depth(ffprobe_available, time_estimate)
        
        # 4. Vérification de l'état du système et des ressources
        checker.print_system_status()
        
        start_time = time.time()
        
        # 5. Phase 1 - Scan basique
        ok_files, phase1_problems = checker.phase1_scan(selected_paths)
        
        # 6. Phase 2 - Scan ffprobe (si choisi)
        phase2_problems = []
        if verification_depth == 'full' and ok_files:
            phase2_problems = checker.phase2_scan(ok_files)
        
        # 7. Regroupement de tous les problèmes
        all_problems = phase1_problems + phase2_problems
        checker.all_problems = all_problems
        
        # 8. Traitement selon le mode
        if mode == 'real' and all_problems:
            confirmed, scan_mode = checker.confirm_deletion(all_problems)
            if confirmed:
                deleted_files = checker.delete_files(all_problems)
                checker.deleted_files = deleted_files
                checker.save_deletion_log(deleted_files)
                
                # Notification des serveurs média selon le mode choisi
                if scan_mode and not args.no_media_scan and any([checker.config.get('sonarr'), checker.config.get('radarr')]):
                    if scan_mode == 'individual':
                        print("\n🎯 Mode individuel sélectionné - Notification précise par fichier")
                        checker.notify_media_servers_individual(deleted_files)
                    elif scan_mode == 'mass':
                        print("\n⚡ Mode en masse sélectionné - Scan complet rapide")
                        checker.notify_media_servers(deleted_files)
                elif scan_mode == 'none':
                    print("\n⏭️ Notification des serveurs média désactivée pour cette session")
            else:
                print("❌ Suppression annulée")
                mode = 'dry-run'  # Traiter comme un dry-run
        
        # 9. Sauvegarde des rapports
        checker.save_full_report(all_problems, mode)
        
        # 10. Scan des serveurs média (optionnel) - seulement si pas déjà fait
        if not args.no_media_scan and mode == 'dry-run':
            checker.trigger_media_scans()
        elif args.no_media_scan:
            print("\n⏭️ Scans des serveurs média ignorés (--no-media-scan)")
        
        # 11. Résumé final
        elapsed = time.time() - start_time
        checker.print_final_summary(mode)
        print(f"\n⏱️ Temps total: {elapsed//60:.0f}m{elapsed%60:.0f}s")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n❌ Opération interrompue par l'utilisateur")
        return 130
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        print(f"❌ Erreur fatale: {e}")
        return 1

if __name__ == "__main__":
    main()