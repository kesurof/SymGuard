#!/usr/bin/env python3

import os
import subprocess
import json
import time
import logging
import argparse
import shutil
import glob
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Détection automatique de l'utilisateur
current_user = os.environ.get('USER', os.environ.get('USERNAME', 'user'))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('symlink_maintenance.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AdvancedSymlinkChecker:
    def __init__(self, max_workers: int = 6):
        self.max_workers = max_workers
        self.stats = {
            'total_analyzed': 0,
            'phase1_ok': 0,
            'phase1_broken': 0,
            'phase1_inaccessible': 0,
            'phase1_small': 0,
            'phase1_io_error': 0,
            'phase2_analyzed': 0,
            'phase2_corrupted': 0,
            'files_deleted': 0
        }
        self.deleted_files = []
        self.all_problems = []
        
        # Configuration des serveurs média
        self.media_config = {
            'sonarr': {'port': 8989, 'api_version': 'v3'},
            'radarr': {'port': 7878, 'api_version': 'v3'}
        }
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Crée une session HTTP avec retry automatique"""
        session = requests.Session()
        retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
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
        """Nettoie les anciens logs et rapports"""
        print("🧹 Nettoyage des anciens fichiers...")
        
        # Rotation des rapports JSON (garder 3)
        self.rotate_old_files("symlink_report_*.json", 3)
        
        # Rotation des logs de suppression (garder 3)
        self.rotate_old_files("deleted_files_*.log", 3)
        
        # Rotation des logs principaux (garder 3)
        self.rotate_old_files("symlink_maintenance*.log", 3)
    
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
        base_path = "/home/kesurof/Medias"
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
    
    def confirm_deletion(self, all_problems: List[Dict]) -> bool:
        """Confirmation globale avant suppression"""
        if not all_problems:
            return False
        
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
            return response in ['y', 'yes', 'o', 'oui']
        except KeyboardInterrupt:
            print("\n❌ Suppression annulée")
            return False
    
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
    
    def get_container_ip(self, container_name: str) -> Optional[str]:
        """Récupère l'IP d'un conteneur Docker"""
        try:
            cmd = f"docker inspect {container_name} --format='{{{{.NetworkSettings.Networks.traefik_proxy.IPAddress}}}}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception as e:
            logger.error(f"Erreur IP container {container_name}: {e}")
        return None
    
    def get_api_key(self, service: str) -> Optional[str]:
        """Récupère la clé API d'un service"""
        try:
            settings_storage = os.environ.get('SETTINGS_STORAGE', '/opt/seedbox/docker')
            current_user = os.environ.get('USER', 'kesurof')
            config_path = f"{settings_storage}/docker/{current_user}/{service}/config/config.xml"
            
            if not os.path.exists(config_path):
                return None
                
            cmd = f"sed -n 's/.*<ApiKey>\\(.*\\)<\\/ApiKey>.*/\\1/p' '{config_path}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout.strip() if result.returncode == 0 else None
            
        except Exception as e:
            logger.error(f"Erreur API key {service}: {e}")
            return None
    
    def trigger_media_scans(self):
        """Déclenche les scans Sonarr/Radarr"""
        print(f"\n🔄 Déclenchement des scans serveurs média...")
        
        for service, config in self.media_config.items():
            try:
                ip = self.get_container_ip(service)
                api_key = self.get_api_key(service)
                
                if not ip or not api_key:
                    print(f"⚠️ {service}: IP ou API key manquante")
                    continue
                
                url = f"http://{ip}:{config['port']}/api/{config['api_version']}/command"
                headers = {"Content-Type": "application/json", "X-Api-Key": api_key}
                
                commands = {
                    'sonarr': ['RescanSeries', 'missingEpisodeSearch'],
                    'radarr': ['RescanMovie', 'MissingMoviesSearch']
                }
                
                for command in commands.get(service, []):
                    data = {"name": command}
                    response = self.session.post(url, json=data, headers=headers, timeout=30)
                    response.raise_for_status()
                    print(f"✅ {service}: {command} lancé")
                    time.sleep(2)
                    
            except Exception as e:
                print(f"❌ {service}: {e}")
    
    def print_final_summary(self, mode: str):
        """Affiche le résumé final"""
        print("\n" + "="*60)
        print("📊 RÉSUMÉ FINAL")
        print("="*60)
        print(f"Mode d'exécution: {mode.upper()}")
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

def main():
    parser = argparse.ArgumentParser(description='Vérificateur avancé de liens symboliques - 2 phases')
    parser.add_argument('path', nargs='?', default='/home/kesurof/Medias', help='Répertoire de base à scanner')
    parser.add_argument('-j', '--jobs', type=int, default=6, help='Nombre de workers parallèles (défaut: 6)')
    
    args = parser.parse_args()
    
    print("🚀 Vérificateur avancé de liens symboliques - 2 phases")
    print(f"📁 Répertoire de base: {args.path}")
    print(f"⚡ Workers parallèles: {args.jobs}")
    
    try:
        checker = AdvancedSymlinkChecker(max_workers=args.jobs)
        
        # 0. Nettoyage des anciens logs
        checker.cleanup_old_logs()
        
        # 1. Choix du mode d'exécution
        mode = checker.choose_execution_mode()
        
        # 2. Sélection interactive des répertoires
        selected_paths = checker.interactive_directory_selection(args.path)
        if not selected_paths:
            print("❌ Aucun répertoire sélectionné, arrêt")
            return
        
        # 3. Vérification ffprobe et choix de profondeur
        ffprobe_available, media_count, time_estimate = checker.check_ffprobe_and_estimate(selected_paths)
        verification_depth = checker.choose_verification_depth(ffprobe_available, time_estimate)
        
        start_time = time.time()
        
        # 4. Phase 1 - Scan basique
        ok_files, phase1_problems = checker.phase1_scan(selected_paths)
        
        # 5. Phase 2 - Scan ffprobe (si choisi)
        phase2_problems = []
        if verification_depth == 'full' and ok_files:
            phase2_problems = checker.phase2_scan(ok_files)
        
        # 6. Regroupement de tous les problèmes
        all_problems = phase1_problems + phase2_problems
        checker.all_problems = all_problems
        
        # 7. Traitement selon le mode
        if mode == 'real' and all_problems:
            if checker.confirm_deletion(all_problems):
                deleted_files = checker.delete_files(all_problems)
                checker.deleted_files = deleted_files
                checker.save_deletion_log(deleted_files)
            else:
                print("❌ Suppression annulée")
                mode = 'dry-run'  # Traiter comme un dry-run
        
        # 8. Sauvegarde des rapports
        checker.save_full_report(all_problems, mode)
        
        # 9. Scan des serveurs média
        checker.trigger_media_scans()
        
        # 10. Résumé final
        elapsed = time.time() - start_time
        checker.print_final_summary(mode)
        print(f"\n⏱️ Temps total: {elapsed//60:.0f}m{elapsed%60:.0f}s")
        
    except KeyboardInterrupt:
        print("\n❌ Opération interrompue par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        print(f"❌ Erreur fatale: {e}")

if __name__ == "__main__":
    main()