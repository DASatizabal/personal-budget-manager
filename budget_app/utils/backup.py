"""Auto-backup utilities for undo functionality"""

import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple

from ..models.database import DB_PATH


# Directory for auto-backups
BACKUP_DIR = Path(DB_PATH).parent / 'auto_backups'
MAX_BACKUPS = 5  # Keep the last N auto-backups


def ensure_backup_dir():
    """Ensure the backup directory exists"""
    BACKUP_DIR.mkdir(exist_ok=True)


def create_auto_backup(operation_name: str = "operation") -> Optional[Path]:
    """
    Create an auto-backup before a destructive operation.
    Returns the path to the backup file or None if backup failed.
    """
    ensure_backup_dir()

    db_path = Path(DB_PATH)
    if not db_path.exists():
        return None

    # Create timestamp-based backup filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # Sanitize operation name for filename
    safe_name = "".join(c if c.isalnum() or c in '-_' else '_' for c in operation_name)
    backup_name = f"auto_{timestamp}_{safe_name}.db"
    backup_path = BACKUP_DIR / backup_name

    try:
        shutil.copy2(db_path, backup_path)
        _cleanup_old_backups()
        return backup_path
    except Exception:
        return None


def _cleanup_old_backups():
    """Remove old auto-backups, keeping only the most recent MAX_BACKUPS"""
    ensure_backup_dir()

    backups = list(BACKUP_DIR.glob('auto_*.db'))
    backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    # Remove older backups beyond MAX_BACKUPS
    for old_backup in backups[MAX_BACKUPS:]:
        try:
            old_backup.unlink()
        except Exception:
            pass


def get_auto_backups() -> List[Tuple[Path, datetime, str]]:
    """
    Get list of available auto-backups.
    Returns list of (path, datetime, operation_name) tuples, newest first.
    """
    ensure_backup_dir()

    backups = []
    for backup_path in BACKUP_DIR.glob('auto_*.db'):
        try:
            # Parse filename: auto_YYYYMMDD_HHMMSS_operation.db
            name = backup_path.stem  # Remove .db
            parts = name.split('_', 3)  # ['auto', 'YYYYMMDD', 'HHMMSS', 'operation']
            if len(parts) >= 4:
                date_str = parts[1]
                time_str = parts[2]
                operation = parts[3].replace('_', ' ')

                backup_time = datetime.strptime(f"{date_str}_{time_str}", '%Y%m%d_%H%M%S')
                backups.append((backup_path, backup_time, operation))
        except Exception:
            continue

    # Sort by datetime, newest first
    backups.sort(key=lambda x: x[1], reverse=True)
    return backups


def restore_from_backup(backup_path: Path) -> bool:
    """
    Restore database from a backup file.
    Returns True if successful, False otherwise.
    """
    if not backup_path.exists():
        return False

    db_path = Path(DB_PATH)

    try:
        # Create a safety backup of current state before restoring
        if db_path.exists():
            safety_backup = BACKUP_DIR / f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(db_path, safety_backup)

        # Close any existing database connection
        from ..models.database import Database
        db = Database()
        db.close()

        # Restore the backup
        shutil.copy2(backup_path, db_path)

        return True
    except Exception:
        return False


def get_most_recent_backup() -> Optional[Tuple[Path, datetime, str]]:
    """Get the most recent auto-backup if available"""
    backups = get_auto_backups()
    return backups[0] if backups else None
