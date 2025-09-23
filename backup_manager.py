import os
import sqlite3
from datetime import datetime, timedelta
import threading
import zipfile

RETENTION_DAYS = 30
BACKUP_ROOT_NAME = "backups"

CONFIG_FILES = [
    # Arquivos de configuração por ambiente
    "data/app_settings_prod.json",
    "data/app_settings_dev.json",
    # Conexões OAuth legadas e por ambiente (inclui legada para migração)
    "data/oauth_connections.json",
    "data/oauth_connections_prod.json",
    "data/oauth_connections_dev.json",
    # Arquivo de ambiente
    "data/app_environment.json"
]

_lock = threading.Lock()


def _now_ts():
    return datetime.now().strftime('%Y-%m-%d_%H-%M-%S')


def _now_human():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _env_dir(env_name: str) -> str:
    return os.path.join(os.path.dirname(__file__), BACKUP_ROOT_NAME, env_name)


def _list_backups(env_name: str):
    directory = _env_dir(env_name)
    if not os.path.isdir(directory):
        return []
    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.db')]
    return sorted(files, key=lambda p: os.path.getmtime(p), reverse=True)


def _needs_backup(env_name: str, max_hours: int = 24) -> bool:
    backups = _list_backups(env_name)
    if not backups:
        return True
    last_mtime = datetime.fromtimestamp(os.path.getmtime(backups[0]))
    return (datetime.now() - last_mtime) >= timedelta(hours=max_hours)


def _integrity_check(db_file: str) -> bool:
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.execute('PRAGMA integrity_check;')
        res = cur.fetchone()[0]
        return res == 'ok'
    finally:
        conn.close()


def _prune_old(env_name: str):
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    for f in _list_backups(env_name)[::-1]:
        try:
            if datetime.fromtimestamp(os.path.getmtime(f)) < cutoff:
                os.remove(f)
        except OSError:
            pass


def _snapshot_configs(timestamp: str):
    cfg_dir = os.path.join(os.path.dirname(__file__), BACKUP_ROOT_NAME, 'configs')
    os.makedirs(cfg_dir, exist_ok=True)
    zip_path = os.path.join(cfg_dir, f'data_snapshot_{timestamp}.zip')
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path in CONFIG_FILES:
            if os.path.isfile(path):
                try:
                    zf.write(path, os.path.basename(path))
                except Exception:
                    continue
    return zip_path


def perform_backup(db_path: str, env_name: str, force: bool = False, max_hours: int = 24):
    with _lock:
        try:
            os.makedirs(_env_dir(env_name), exist_ok=True)
            if not force and not _needs_backup(env_name, max_hours=max_hours):
                return False, 'Backup recente existe (<{h}h)'.format(h=max_hours)
            if not os.path.isfile(db_path):
                return False, f'Banco não encontrado: {db_path}'
            timestamp = _now_ts()
            base = os.path.basename(db_path)
            dest = os.path.join(_env_dir(env_name), base.replace('.db', f'_{timestamp}.db'))
            src_conn = sqlite3.connect(db_path)
            dest_conn = sqlite3.connect(dest)
            try:
                with dest_conn:
                    src_conn.backup(dest_conn)
            finally:
                dest_conn.close()
                src_conn.close()
            if not _integrity_check(dest):
                try:
                    os.remove(dest)
                except OSError:
                    pass
                return False, 'Integrity check falhou'
            _prune_old(env_name)
            _snapshot_configs(timestamp)
            return True, dest
        except Exception as e:
            return False, f'Erro backup: {e}'


def start_periodic_backups(db_path: str, env_name: str, interval_hours: int = 6):
    def loop():
        while True:
            try:
                perform_backup(db_path, env_name, force=False, max_hours=24)
            except Exception:
                pass
            import time
            time.sleep(interval_hours * 3600)
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t


if __name__ == '__main__':
    try:
        from config import Config
        from environment_manager import environment_manager
        dbp = Config.get_database_path()
        env = environment_manager.get_current_environment()
        created, info = perform_backup(dbp, env, force=True)
        print(f'[{_now_human()}] created={created} detail={info}')
    except Exception as e:
        print(f'[{_now_human()}] erro: {e}')
