"""Unit tests for backup utilities"""

import pytest
import tempfile
import shutil
import os
import time
from pathlib import Path
from unittest.mock import patch
from datetime import datetime


@pytest.fixture
def backup_env(temp_db):
    """Set up backup environment with patched paths"""
    import budget_app.utils.backup as backup_mod

    # Create a temp backup dir
    backup_dir = Path(tempfile.mkdtemp())
    original_backup_dir = backup_mod.BACKUP_DIR
    original_max = backup_mod.MAX_BACKUPS
    backup_mod.BACKUP_DIR = backup_dir

    yield {
        'db_path': temp_db,
        'backup_dir': backup_dir,
        'backup_mod': backup_mod,
    }

    # Cleanup
    backup_mod.BACKUP_DIR = original_backup_dir
    backup_mod.MAX_BACKUPS = original_max
    shutil.rmtree(backup_dir, ignore_errors=True)


class TestCreateAutoBackup:
    """Tests for create_auto_backup"""

    def test_creates_backup_file(self, backup_env):
        """Should create a backup file in the backup directory"""
        mod = backup_env['backup_mod']
        result = mod.create_auto_backup("test_operation")
        assert result is not None
        assert result.exists()
        assert 'test_operation' in result.name

    def test_backup_filename_format(self, backup_env):
        """Backup filename should follow auto_YYYYMMDD_HHMMSS_name.db pattern"""
        mod = backup_env['backup_mod']
        result = mod.create_auto_backup("my_op")
        assert result.name.startswith('auto_')
        assert result.name.endswith('.db')
        assert 'my_op' in result.name

    def test_special_characters_sanitized(self, backup_env):
        """Special characters in operation name should be sanitized"""
        mod = backup_env['backup_mod']
        result = mod.create_auto_backup("delete all!!! @#$")
        assert result is not None
        # Special chars replaced with underscores
        assert '!' not in result.name
        assert '@' not in result.name

    def test_returns_none_when_no_db(self, backup_env):
        """Should return None when database file doesn't exist"""
        mod = backup_env['backup_mod']
        import budget_app.utils.backup as backup_module
        original_db_path = backup_module.DB_PATH
        fake_path = Path(backup_env['backup_dir']) / 'nonexistent' / 'fake.db'
        backup_module.DB_PATH = fake_path
        try:
            result = mod.create_auto_backup("test")
            assert result is None
        finally:
            backup_module.DB_PATH = original_db_path


class TestCleanupOldBackups:
    """Tests for _cleanup_old_backups"""

    def test_keeps_only_max_backups(self, backup_env):
        """Should remove oldest backups beyond MAX_BACKUPS"""
        mod = backup_env['backup_mod']
        mod.MAX_BACKUPS = 3

        # Create 5 backups
        for i in range(5):
            mod.create_auto_backup(f"op_{i}")
            time.sleep(0.05)  # Ensure different timestamps

        backups = list(backup_env['backup_dir'].glob('auto_*.db'))
        assert len(backups) == 3


class TestGetAutoBackups:
    """Tests for get_auto_backups"""

    def test_returns_backup_tuples(self, backup_env):
        """Should return list of (path, datetime, operation_name) tuples"""
        mod = backup_env['backup_mod']
        mod.create_auto_backup("import_excel")

        backups = mod.get_auto_backups()
        assert len(backups) >= 1
        path, dt, op = backups[0]
        assert isinstance(path, Path)
        assert isinstance(dt, datetime)
        assert 'import excel' in op or 'import_excel' in op

    def test_sorted_newest_first(self, backup_env):
        """Backups should be sorted newest first"""
        mod = backup_env['backup_mod']
        mod.create_auto_backup("first")
        time.sleep(0.05)
        mod.create_auto_backup("second")

        backups = mod.get_auto_backups()
        assert len(backups) >= 2
        # First entry should be newer
        assert backups[0][1] >= backups[1][1]

    def test_empty_when_no_backups(self, backup_env):
        """Should return empty list when no backups exist"""
        mod = backup_env['backup_mod']
        backups = mod.get_auto_backups()
        assert backups == []


class TestRestoreFromBackup:
    """Tests for restore_from_backup"""

    def test_restore_copies_file(self, backup_env):
        """Restore should copy backup over database file"""
        mod = backup_env['backup_mod']
        backup_path = mod.create_auto_backup("before_restore")

        result = mod.restore_from_backup(backup_path)
        assert result is True

    def test_restore_creates_safety_backup(self, backup_env):
        """Restore should create a pre_restore safety backup"""
        mod = backup_env['backup_mod']
        backup_path = mod.create_auto_backup("initial")
        mod.restore_from_backup(backup_path)

        safety_backups = list(backup_env['backup_dir'].glob('pre_restore_*.db'))
        assert len(safety_backups) >= 1

    def test_restore_nonexistent_returns_false(self, backup_env):
        """Restore should return False for nonexistent backup"""
        mod = backup_env['backup_mod']
        result = mod.restore_from_backup(Path('/nonexistent/backup.db'))
        assert result is False


class TestGetMostRecentBackup:
    """Tests for get_most_recent_backup"""

    def test_returns_most_recent(self, backup_env):
        """Should return the newest backup"""
        mod = backup_env['backup_mod']
        mod.create_auto_backup("old")
        time.sleep(0.05)
        mod.create_auto_backup("latest")

        most_recent = mod.get_most_recent_backup()
        assert most_recent is not None
        _, _, op = most_recent
        assert 'latest' in op

    def test_returns_none_when_empty(self, backup_env):
        """Should return None when no backups exist"""
        mod = backup_env['backup_mod']
        assert mod.get_most_recent_backup() is None


class TestErrorHandlers:
    """Tests for exception handling branches"""

    def test_create_backup_copy_failure(self, backup_env):
        """create_auto_backup should return None when copy fails"""
        mod = backup_env['backup_mod']
        with patch('budget_app.utils.backup.shutil.copy2', side_effect=OSError("disk full")):
            result = mod.create_auto_backup("failing_op")
            assert result is None

    def test_cleanup_unlink_failure_ignored(self, backup_env):
        """_cleanup_old_backups should silently ignore unlink failures"""
        mod = backup_env['backup_mod']
        mod.MAX_BACKUPS = 2

        # Create 4 backups
        for i in range(4):
            mod.create_auto_backup(f"op_{i}")
            time.sleep(0.05)

        # Patch unlink to fail — cleanup should not raise
        with patch.object(Path, 'unlink', side_effect=PermissionError("locked")):
            # This should not raise even though unlink fails
            mod._cleanup_old_backups()

    def test_get_auto_backups_skips_malformed_filenames(self, backup_env):
        """get_auto_backups should skip files with unparseable filenames"""
        mod = backup_env['backup_mod']
        backup_dir = backup_env['backup_dir']

        # Create a properly named backup
        mod.create_auto_backup("good")

        # Create a malformed backup file (wrong name format)
        malformed = backup_dir / 'auto_bad.db'
        malformed.write_bytes(b'fake')

        backups = mod.get_auto_backups()
        # Should have the good backup but skip the malformed one
        # (malformed has only 2 parts after split, needs >= 4)
        ops = [op for _, _, op in backups]
        assert 'good' in ops
        assert len(backups) == 1

    def test_restore_copy_failure_returns_false(self, backup_env):
        """restore_from_backup should return False when copy fails"""
        mod = backup_env['backup_mod']
        backup_path = mod.create_auto_backup("before")

        with patch('budget_app.utils.backup.shutil.copy2', side_effect=OSError("fail")):
            result = mod.restore_from_backup(backup_path)
            assert result is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
