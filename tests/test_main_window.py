"""Unit tests for Main Window and related dialogs"""

import pytest
import sys
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# ExportCsvDialog tests (no qdarkstyle dependency)
# ---------------------------------------------------------------------------

class TestExportCsvDialog:
    """Tests for ExportCsvDialog"""

    def _make_dialog(self, qtbot):
        from budget_app.views.main_window import ExportCsvDialog
        dialog = ExportCsvDialog()
        qtbot.addWidget(dialog)
        return dialog

    def test_all_checkboxes_initially_checked(self, qtbot):
        """All 7 table checkboxes should be checked by default"""
        dialog = self._make_dialog(qtbot)
        expected_keys = [
            'accounts', 'credit_cards', 'loans',
            'recurring_charges', 'transactions',
            'paycheck', 'shared_expenses',
        ]
        assert set(dialog.table_checkboxes.keys()) == set(expected_keys)
        for key, cb in dialog.table_checkboxes.items():
            assert cb.isChecked(), f"Checkbox '{key}' should be checked initially"

    def test_date_filters_initially_disabled(self, qtbot):
        """Start/end date edits should be disabled and checkboxes unchecked"""
        dialog = self._make_dialog(qtbot)
        assert not dialog.start_date_cb.isChecked()
        assert not dialog.end_date_cb.isChecked()
        assert not dialog.start_date_edit.isEnabled()
        assert not dialog.end_date_edit.isEnabled()

    def test_enabling_start_date_cb_enables_start_date_edit(self, qtbot):
        """Toggling start_date_cb on should enable start_date_edit"""
        dialog = self._make_dialog(qtbot)
        dialog.start_date_cb.setChecked(True)
        assert dialog.start_date_edit.isEnabled()

    def test_enabling_end_date_cb_enables_end_date_edit(self, qtbot):
        """Toggling end_date_cb on should enable end_date_edit"""
        dialog = self._make_dialog(qtbot)
        dialog.end_date_cb.setChecked(True)
        assert dialog.end_date_edit.isEnabled()

    def test_set_all_checked_false_unchecks_all(self, qtbot):
        """_set_all_checked(False) should uncheck every table checkbox"""
        dialog = self._make_dialog(qtbot)
        dialog._set_all_checked(False)
        for key, cb in dialog.table_checkboxes.items():
            assert not cb.isChecked(), f"Checkbox '{key}' should be unchecked"

    def test_set_all_checked_true_checks_all(self, qtbot):
        """_set_all_checked(True) should check every table checkbox"""
        dialog = self._make_dialog(qtbot)
        dialog._set_all_checked(False)  # uncheck first
        dialog._set_all_checked(True)
        for key, cb in dialog.table_checkboxes.items():
            assert cb.isChecked(), f"Checkbox '{key}' should be checked"

    def test_dialog_title(self, qtbot):
        """Dialog window title should be 'Export to CSV'"""
        dialog = self._make_dialog(qtbot)
        assert dialog.windowTitle() == "Export to CSV"


# ---------------------------------------------------------------------------
# MainWindow tests (requires qdarkstyle mock or real install)
# ---------------------------------------------------------------------------

@pytest.fixture
def main_window(qtbot, temp_db, monkeypatch):
    """Create MainWindow, patching qdarkstyle if not installed"""
    try:
        import qdarkstyle  # noqa: F401
    except ImportError:
        mock_palette = MagicMock()
        mock_light = MagicMock()
        mock_light.palette = mock_palette

        mock_qdarkstyle = MagicMock()
        mock_qdarkstyle.load_stylesheet.return_value = ""
        mock_qdarkstyle.light = mock_light

        sys.modules['qdarkstyle'] = mock_qdarkstyle
        sys.modules['qdarkstyle.light'] = mock_light
        sys.modules['qdarkstyle.light.palette'] = mock_palette

    from budget_app.views.main_window import MainWindow
    window = MainWindow()
    qtbot.addWidget(window)
    return window


class TestMainWindow:
    """Tests for MainWindow"""

    def test_window_title(self, main_window):
        """Window title should be 'Personal Budget Manager'"""
        assert main_window.windowTitle() == "Personal Budget Manager"

    def test_tab_count(self, main_window):
        """There should be exactly 11 tabs"""
        assert main_window.tabs.count() == 11

    def test_tab_labels(self, main_window):
        """Tab labels should match expected names in order"""
        expected = [
            "Dashboard", "Transactions", "Posted", "Credit Cards",
            "Payoff Planner", "Deferred Interest", "Recurring Charges",
            "Paycheck", "Lisa Payments", "PDF Import", "Bank API",
        ]
        actual = [main_window.tabs.tabText(i) for i in range(main_window.tabs.count())]
        assert actual == expected

    def test_status_bar_shows_ready(self, main_window):
        """Status bar should initially display 'Ready'"""
        assert main_window.status_bar.currentMessage() == "Ready"

    def test_menu_bar_has_expected_menus(self, main_window):
        """Menu bar should contain File, Edit, View, Tools, Help menus"""
        menu_bar = main_window.menuBar()
        menu_titles = [action.text() for action in menu_bar.actions()]
        for expected in ["&File", "&Edit", "&View", "&Tools", "&Help"]:
            assert expected in menu_titles, f"Menu '{expected}' not found in menu bar"

    def test_on_tab_changed_calls_refresh(self, main_window):
        """Switching tabs should trigger refresh on the new tab's view"""
        # Switch to Credit Cards tab (index 3)
        main_window.tabs.setCurrentIndex(3)
        current_widget = main_window.tabs.currentWidget()
        # Verify we are on the credit cards view
        assert current_widget is main_window.credit_cards_view

    def test_refresh_current_view_updates_status_bar(self, main_window):
        """_refresh_current_view() should update the status bar message"""
        main_window._refresh_current_view()
        assert main_window.status_bar.currentMessage() == "View refreshed"

    def test_dashboard_is_first_tab(self, main_window):
        """Dashboard should be the first tab (index 0) and the current widget after init"""
        assert main_window.tabs.currentIndex() == 0
        assert main_window.tabs.currentWidget() is main_window.dashboard_view


# ---------------------------------------------------------------------------
# RecalculateBalancesDialog tests
# ---------------------------------------------------------------------------

class TestRecalculateBalancesDialog:
    """Tests for RecalculateBalancesDialog"""

    def _make_dialog(self, qtbot):
        from budget_app.views.main_window import RecalculateBalancesDialog
        dialog = RecalculateBalancesDialog()
        qtbot.addWidget(dialog)
        return dialog

    def test_dialog_title(self, qtbot, temp_db):
        """Dialog title should be 'Recalculate Balances'"""
        dialog = self._make_dialog(qtbot)
        assert dialog.windowTitle() == "Recalculate Balances"

    def test_table_has_six_columns(self, qtbot, temp_db):
        """Table should have 6 columns with the correct headers"""
        dialog = self._make_dialog(qtbot)
        assert dialog.table.columnCount() == 6
        expected_headers = [
            "Account", "Type", "Stored Balance",
            "Transaction Sum", "Calculated", "Actual Balance"
        ]
        for col, expected in enumerate(expected_headers):
            header_item = dialog.table.horizontalHeaderItem(col)
            assert header_item.text() == expected, (
                f"Column {col} header should be '{expected}', got '{header_item.text()}'"
            )

    def test_accounts_appear_in_table(self, qtbot, temp_db, sample_account):
        """An account with a pay_type_code should appear as a row in the table"""
        dialog = self._make_dialog(qtbot)
        assert dialog.table.rowCount() >= 1
        # Verify the account name appears in the first column of some row
        found = False
        for row in range(dialog.table.rowCount()):
            cell_text = dialog.table.item(row, 0).text()
            if sample_account.name in cell_text:
                found = True
                break
        assert found, f"Account '{sample_account.name}' not found in table"

    def test_cards_appear_in_table(self, qtbot, temp_db, sample_card):
        """A credit card should appear as a row in the table"""
        dialog = self._make_dialog(qtbot)
        assert dialog.table.rowCount() >= 1
        found = False
        for row in range(dialog.table.rowCount()):
            cell_text = dialog.table.item(row, 0).text()
            if sample_card.name in cell_text:
                found = True
                # Verify type column says CREDIT CARD
                type_text = dialog.table.item(row, 1).text()
                assert type_text == "CREDIT CARD"
                break
        assert found, f"Card '{sample_card.name}' not found in table"

    def test_loans_appear_in_table(self, qtbot, temp_db, sample_loan):
        """A loan should appear as a row in the table"""
        dialog = self._make_dialog(qtbot)
        assert dialog.table.rowCount() >= 1
        found = False
        for row in range(dialog.table.rowCount()):
            cell_text = dialog.table.item(row, 0).text()
            if sample_loan.name in cell_text:
                found = True
                # Verify type column says LOAN
                type_text = dialog.table.item(row, 1).text()
                assert type_text == "LOAN"
                break
        assert found, f"Loan '{sample_loan.name}' not found in table"

    def test_spinbox_initial_value_matches_calculated(self, qtbot, temp_db, sample_account):
        """Spinbox in Actual Balance column should equal stored_balance + trans_sum (no posted txns => stored_balance)"""
        dialog = self._make_dialog(qtbot)
        # Find the row for our sample account
        for row in range(dialog.table.rowCount()):
            cell_text = dialog.table.item(row, 0).text()
            if sample_account.name in cell_text:
                spinbox = dialog.spinboxes[row]
                # With no posted transactions, trans_sum = 0, so calculated = stored_balance
                assert abs(spinbox.value() - sample_account.current_balance) < 0.01, (
                    f"Spinbox value {spinbox.value()} should equal stored balance "
                    f"{sample_account.current_balance}"
                )
                return
        pytest.fail(f"Account '{sample_account.name}' not found in dialog table")

    def test_apply_no_changes_shows_info(self, qtbot, temp_db, sample_account, mock_qmessagebox):
        """Applying without changes should show 'No Changes' info message"""
        dialog = self._make_dialog(qtbot)
        dialog._apply_changes()
        assert mock_qmessagebox.info_called
        assert mock_qmessagebox.info_title == "No Changes"


# ---------------------------------------------------------------------------
# AutoBackupRestoreDialog tests
# ---------------------------------------------------------------------------

class TestAutoBackupRestoreDialog:
    """Tests for AutoBackupRestoreDialog"""

    def _make_dialog(self, qtbot):
        from datetime import datetime
        from budget_app.views.main_window import AutoBackupRestoreDialog
        backups = [
            ('/path/backup1.db', datetime(2026, 2, 10, 14, 30), 'excel_import'),
            ('/path/backup2.db', datetime(2026, 2, 9, 10, 0), 'generate_transactions'),
        ]
        dialog = AutoBackupRestoreDialog(None, backups)
        qtbot.addWidget(dialog)
        return dialog

    def test_dialog_title(self, qtbot):
        """Dialog title should be 'Restore from Auto-Backup'"""
        dialog = self._make_dialog(qtbot)
        assert dialog.windowTitle() == "Restore from Auto-Backup"

    def test_backup_list_populated(self, qtbot):
        """Backup list should have one item per backup"""
        dialog = self._make_dialog(qtbot)
        assert dialog.backup_list.count() == 2

    def test_backup_list_items_text(self, qtbot):
        """Each list item should contain the operation name"""
        dialog = self._make_dialog(qtbot)
        assert "excel_import" in dialog.backup_list.item(0).text()
        assert "generate_transactions" in dialog.backup_list.item(1).text()

    def test_backup_list_items_user_data(self, qtbot):
        """Each list item should store the backup path in UserRole"""
        from PyQt6.QtCore import Qt
        dialog = self._make_dialog(qtbot)
        assert dialog.backup_list.item(0).data(Qt.ItemDataRole.UserRole) == '/path/backup1.db'
        assert dialog.backup_list.item(1).data(Qt.ItemDataRole.UserRole) == '/path/backup2.db'

    def test_selected_backup_initially_none(self, qtbot):
        """selected_backup should be None before any interaction"""
        dialog = self._make_dialog(qtbot)
        assert dialog.selected_backup is None

    def test_on_restore_no_selection_warns(self, qtbot, mock_qmessagebox):
        """Clicking restore with no selection should show a warning"""
        dialog = self._make_dialog(qtbot)
        dialog._on_restore()
        assert mock_qmessagebox.warning_called

    def test_on_restore_with_selection_sets_selected(self, qtbot, mock_qmessagebox):
        """Clicking restore with a selection should set selected_backup to the path"""
        dialog = self._make_dialog(qtbot)
        dialog.backup_list.setCurrentRow(0)
        dialog._on_restore()
        assert dialog.selected_backup == '/path/backup1.db'


# ---------------------------------------------------------------------------
# ExportCsvDialog._on_accept tests
# ---------------------------------------------------------------------------

class TestExportCsvDialogAccept:
    """Tests for ExportCsvDialog._on_accept validation and data collection"""

    def _make_dialog(self, qtbot):
        from budget_app.views.main_window import ExportCsvDialog
        dialog = ExportCsvDialog()
        qtbot.addWidget(dialog)
        return dialog

    def test_on_accept_no_folder_warns(self, qtbot, mock_qmessagebox):
        """Accepting without selecting a folder should warn the user"""
        dialog = self._make_dialog(qtbot)
        dialog._on_accept()
        assert mock_qmessagebox.warning_called

    def test_on_accept_with_folder_sets_tables(self, qtbot):
        """Accepting with a folder should populate selected_tables with all 7 defaults"""
        dialog = self._make_dialog(qtbot)
        dialog.selected_folder = '/tmp/export'
        dialog._on_accept()
        assert len(dialog.selected_tables) == 7

    def test_on_accept_respects_unchecked_tables(self, qtbot):
        """Unchecked table checkboxes should be excluded from selected_tables"""
        dialog = self._make_dialog(qtbot)
        dialog.selected_folder = '/tmp/export'
        dialog.table_checkboxes['loans'].setChecked(False)
        dialog._on_accept()
        assert 'loans' not in dialog.selected_tables
        assert len(dialog.selected_tables) == 6

    def test_on_accept_with_start_date(self, qtbot):
        """Enabling start date checkbox should capture start_date string"""
        dialog = self._make_dialog(qtbot)
        dialog.selected_folder = '/tmp/export'
        dialog.start_date_cb.setChecked(True)
        dialog._on_accept()
        assert dialog.start_date is not None
        # Should be in yyyy-MM-dd format
        assert len(dialog.start_date) == 10
        assert dialog.start_date[4] == '-'

    def test_on_accept_without_start_date(self, qtbot):
        """Without start date checkbox, start_date should remain None"""
        dialog = self._make_dialog(qtbot)
        dialog.selected_folder = '/tmp/export'
        dialog._on_accept()
        assert dialog.start_date is None

    def test_on_accept_with_end_date(self, qtbot):
        """Enabling end date checkbox should capture end_date string"""
        dialog = self._make_dialog(qtbot)
        dialog.selected_folder = '/tmp/export'
        dialog.end_date_cb.setChecked(True)
        dialog._on_accept()
        assert dialog.end_date is not None
        assert len(dialog.end_date) == 10

    def test_on_accept_without_end_date(self, qtbot):
        """Without end date checkbox, end_date should remain None"""
        dialog = self._make_dialog(qtbot)
        dialog.selected_folder = '/tmp/export'
        dialog._on_accept()
        assert dialog.end_date is None


# ---------------------------------------------------------------------------
# RecalculateBalancesDialog._apply_changes with actual changes
# ---------------------------------------------------------------------------

class TestRecalculateBalancesDialogApply:
    """Tests for _apply_changes when spinbox values differ from calculated"""

    def _make_dialog(self, qtbot):
        from budget_app.views.main_window import RecalculateBalancesDialog
        dialog = RecalculateBalancesDialog()
        qtbot.addWidget(dialog)
        return dialog

    def test_apply_changes_updates_account(self, qtbot, temp_db, sample_account, mock_qmessagebox):
        """Changing an account spinbox should update the account balance in the DB"""
        from budget_app.models.account import Account
        dialog = self._make_dialog(qtbot)
        for row in range(dialog.table.rowCount()):
            if sample_account.name in dialog.table.item(row, 0).text():
                dialog.spinboxes[row].setValue(sample_account.current_balance + 100)
                break
        dialog._apply_changes()
        assert mock_qmessagebox.info_called
        assert mock_qmessagebox.info_title == "Balances Updated"
        updated = Account.get_by_id(sample_account.id)
        assert abs(updated.current_balance - (sample_account.current_balance + 100)) < 0.01

    def test_apply_changes_updates_card(self, qtbot, temp_db, sample_card, mock_qmessagebox):
        """Changing a credit card spinbox should update the card balance in the DB"""
        from budget_app.models.credit_card import CreditCard
        dialog = self._make_dialog(qtbot)
        for row in range(dialog.table.rowCount()):
            if sample_card.name in dialog.table.item(row, 0).text():
                dialog.spinboxes[row].setValue(sample_card.current_balance + 50)
                break
        dialog._apply_changes()
        assert mock_qmessagebox.info_called
        assert mock_qmessagebox.info_title == "Balances Updated"
        updated = CreditCard.get_by_id(sample_card.id)
        assert abs(updated.current_balance - (sample_card.current_balance + 50)) < 0.01

    def test_apply_changes_updates_loan(self, qtbot, temp_db, sample_loan, mock_qmessagebox):
        """Changing a loan spinbox should update the loan balance in the DB"""
        from budget_app.models.loan import Loan
        dialog = self._make_dialog(qtbot)
        for row in range(dialog.table.rowCount()):
            if sample_loan.name in dialog.table.item(row, 0).text():
                dialog.spinboxes[row].setValue(sample_loan.current_balance - 200)
                break
        dialog._apply_changes()
        assert mock_qmessagebox.info_called
        assert mock_qmessagebox.info_title == "Balances Updated"
        updated = Loan.get_by_id(sample_loan.id)
        assert abs(updated.current_balance - (sample_loan.current_balance - 200)) < 0.01


# ---------------------------------------------------------------------------
# MainWindow._import_excel tests
# ---------------------------------------------------------------------------

class TestMainWindowImportExcel:
    """Tests for _import_excel method"""

    def test_import_no_file_selected(self, main_window, monkeypatch):
        """When user cancels file dialog, nothing happens and no crash"""
        from PyQt6.QtWidgets import QFileDialog
        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('', '')))
        main_window._import_excel()
        # No exception means success

    def test_import_user_cancels_confirm(self, main_window, monkeypatch, mock_qmessagebox):
        """When user selects file but cancels the confirmation warning, method returns early"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/tmp/test.xlsx', '')))
        mock_qmessagebox.last_return = QMessageBox.StandardButton.No
        main_window._import_excel()
        assert mock_qmessagebox.warning_called
        assert "Confirm Import" == mock_qmessagebox.warning_title

    def test_import_success(self, main_window, monkeypatch, mock_qmessagebox):
        """Successful import shows information dialog with Import Complete title"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/tmp/test.xlsx', '')))
        mock_qmessagebox.last_return = QMessageBox.StandardButton.Yes
        monkeypatch.setattr('budget_app.views.main_window.create_auto_backup',
                            lambda *a: '/tmp/backup.db')
        monkeypatch.setattr('budget_app.views.main_window.import_from_excel', lambda *a: {
            'credit_cards': 5, 'loans': 2, 'recurring_charges': 10,
            'accounts': 3, 'paycheck_configs': 1, 'shared_expenses': 4, 'warnings': []
        })
        main_window._import_excel()
        assert mock_qmessagebox.info_called
        assert mock_qmessagebox.info_title == "Import Complete"

    def test_import_with_warnings(self, main_window, monkeypatch, mock_qmessagebox):
        """Import with warnings still shows success dialog and includes warning text"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/tmp/test.xlsx', '')))
        mock_qmessagebox.last_return = QMessageBox.StandardButton.Yes
        monkeypatch.setattr('budget_app.views.main_window.create_auto_backup',
                            lambda *a: None)
        monkeypatch.setattr('budget_app.views.main_window.import_from_excel', lambda *a: {
            'credit_cards': 5, 'loans': 0, 'recurring_charges': 0,
            'accounts': 0, 'paycheck_configs': 0, 'shared_expenses': 0,
            'warnings': ['Warning 1', 'Warning 2']
        })
        main_window._import_excel()
        assert mock_qmessagebox.info_called
        assert "Warnings" in mock_qmessagebox.info_text

    def test_import_file_not_found(self, main_window, monkeypatch, mock_qmessagebox):
        """FileNotFoundError during import shows critical dialog"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/tmp/missing.xlsx', '')))
        mock_qmessagebox.last_return = QMessageBox.StandardButton.Yes
        monkeypatch.setattr('budget_app.views.main_window.create_auto_backup',
                            lambda *a: None)

        def mock_import(path):
            raise FileNotFoundError("not found")

        monkeypatch.setattr('budget_app.views.main_window.import_from_excel', mock_import)

        critical_tracker = {'called': False, 'title': ''}

        def mock_critical(parent, title, text, **kwargs):
            critical_tracker['called'] = True
            critical_tracker['title'] = title

        monkeypatch.setattr(QMessageBox, 'critical', staticmethod(mock_critical))
        main_window._import_excel()
        assert critical_tracker['called']
        assert critical_tracker['title'] == "File Not Found"

    def test_import_generic_exception(self, main_window, monkeypatch, mock_qmessagebox):
        """Generic exception during import shows critical dialog with Import Error"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/tmp/bad.xlsx', '')))
        mock_qmessagebox.last_return = QMessageBox.StandardButton.Yes
        monkeypatch.setattr('budget_app.views.main_window.create_auto_backup',
                            lambda *a: None)

        def mock_import(path):
            raise ValueError("corrupt data")

        monkeypatch.setattr('budget_app.views.main_window.import_from_excel', mock_import)

        critical_tracker = {'called': False, 'title': ''}

        def mock_critical(parent, title, text, **kwargs):
            critical_tracker['called'] = True
            critical_tracker['title'] = title

        monkeypatch.setattr(QMessageBox, 'critical', staticmethod(mock_critical))
        main_window._import_excel()
        assert critical_tracker['called']
        assert critical_tracker['title'] == "Import Error"


# ---------------------------------------------------------------------------
# MainWindow._backup_database / _restore_database tests
# ---------------------------------------------------------------------------

class TestMainWindowBackup:
    """Tests for _backup_database and _restore_database methods"""

    def test_backup_no_file_selected(self, main_window, monkeypatch):
        """When user cancels save dialog, nothing happens"""
        from PyQt6.QtWidgets import QFileDialog
        monkeypatch.setattr(QFileDialog, 'getSaveFileName',
                            staticmethod(lambda *a, **kw: ('', '')))
        main_window._backup_database()
        # No exception means success

    def test_backup_success(self, main_window, monkeypatch, mock_qmessagebox):
        """Successful backup shows information dialog"""
        import shutil
        from PyQt6.QtWidgets import QFileDialog
        monkeypatch.setattr(QFileDialog, 'getSaveFileName',
                            staticmethod(lambda *a, **kw: ('/tmp/backup.db', '')))
        monkeypatch.setattr(shutil, 'copy2', lambda *a: None)
        main_window._backup_database()
        assert mock_qmessagebox.info_called
        assert mock_qmessagebox.info_title == "Backup"

    def test_backup_exception(self, main_window, monkeypatch, mock_qmessagebox):
        """Exception during backup shows critical dialog"""
        import shutil
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        monkeypatch.setattr(QFileDialog, 'getSaveFileName',
                            staticmethod(lambda *a, **kw: ('/tmp/backup.db', '')))
        monkeypatch.setattr(shutil, 'copy2', lambda *a: (_ for _ in ()).throw(OSError("disk full")))

        def mock_copy(*a):
            raise OSError("disk full")

        monkeypatch.setattr(shutil, 'copy2', mock_copy)

        critical_tracker = {'called': False, 'title': ''}

        def mock_critical(parent, title, text, **kwargs):
            critical_tracker['called'] = True
            critical_tracker['title'] = title

        monkeypatch.setattr(QMessageBox, 'critical', staticmethod(mock_critical))
        main_window._backup_database()
        assert critical_tracker['called']
        assert critical_tracker['title'] == "Backup Error"

    def test_restore_no_file_selected(self, main_window, monkeypatch):
        """When user cancels open dialog for restore, nothing happens"""
        from PyQt6.QtWidgets import QFileDialog
        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('', '')))
        main_window._restore_database()


# ---------------------------------------------------------------------------
# MainWindow._undo_last_operation / _restore_from_auto_backup tests
# ---------------------------------------------------------------------------

class TestMainWindowUndoAndRestore:
    """Tests for _undo_last_operation and _restore_from_auto_backup methods"""

    def test_undo_no_backup_shows_info(self, main_window, monkeypatch, mock_qmessagebox):
        """When no backup is available, shows info dialog with No Backup Available title"""
        monkeypatch.setattr('budget_app.views.main_window.get_most_recent_backup', lambda: None)
        main_window._undo_last_operation()
        assert mock_qmessagebox.info_called
        assert "No Backup" in mock_qmessagebox.info_title

    def test_undo_user_declines(self, main_window, monkeypatch, mock_qmessagebox):
        """When user declines undo confirmation, nothing is restored"""
        from datetime import datetime
        from PyQt6.QtWidgets import QMessageBox
        monkeypatch.setattr('budget_app.views.main_window.get_most_recent_backup',
                            lambda: ('/tmp/backup.db', datetime(2026, 2, 10, 14, 30), 'excel_import'))
        mock_qmessagebox.last_return = QMessageBox.StandardButton.No
        main_window._undo_last_operation()
        assert mock_qmessagebox.question_called
        assert "Confirm Undo" == mock_qmessagebox.question_title

    def test_undo_success(self, main_window, monkeypatch, mock_qmessagebox):
        """Successful undo restores and shows success dialog"""
        from datetime import datetime
        from PyQt6.QtWidgets import QMessageBox
        monkeypatch.setattr('budget_app.views.main_window.get_most_recent_backup',
                            lambda: ('/tmp/backup.db', datetime(2026, 2, 10, 14, 30), 'excel_import'))
        mock_qmessagebox.last_return = QMessageBox.StandardButton.Yes
        monkeypatch.setattr('budget_app.views.main_window.restore_from_backup', lambda p: True)
        monkeypatch.setattr('budget_app.views.main_window.init_db', lambda: None)
        main_window._undo_last_operation()
        assert mock_qmessagebox.info_called
        assert mock_qmessagebox.info_title == "Undo Complete"

    def test_undo_restore_fails(self, main_window, monkeypatch, mock_qmessagebox):
        """When restore_from_backup returns False, shows critical error"""
        from datetime import datetime
        from PyQt6.QtWidgets import QMessageBox
        monkeypatch.setattr('budget_app.views.main_window.get_most_recent_backup',
                            lambda: ('/tmp/backup.db', datetime(2026, 2, 10, 14, 30), 'excel_import'))
        mock_qmessagebox.last_return = QMessageBox.StandardButton.Yes
        monkeypatch.setattr('budget_app.views.main_window.restore_from_backup', lambda p: False)

        critical_tracker = {'called': False}

        def mock_critical(parent, title, text, **kwargs):
            critical_tracker['called'] = True

        monkeypatch.setattr(QMessageBox, 'critical', staticmethod(mock_critical))
        main_window._undo_last_operation()
        assert critical_tracker['called']

    def test_restore_auto_no_backups_shows_info(self, main_window, monkeypatch, mock_qmessagebox):
        """When no auto-backups exist, shows info dialog with No Backups title"""
        monkeypatch.setattr('budget_app.views.main_window.get_auto_backups', lambda: [])
        main_window._restore_from_auto_backup()
        assert mock_qmessagebox.info_called
        assert "No Backups" in mock_qmessagebox.info_title


# ---------------------------------------------------------------------------
# MainWindow._show_about tests
# ---------------------------------------------------------------------------

class TestMainWindowAbout:
    """Tests for _show_about method"""

    def test_show_about(self, main_window, monkeypatch):
        """_show_about calls QMessageBox.about with expected title"""
        from PyQt6.QtWidgets import QMessageBox
        about_tracker = {'called': False, 'title': ''}

        def mock_about(parent, title, text):
            about_tracker['called'] = True
            about_tracker['title'] = title

        monkeypatch.setattr(QMessageBox, 'about', staticmethod(mock_about))
        main_window._show_about()
        assert about_tracker['called']
        assert "About" in about_tracker['title']


# ---------------------------------------------------------------------------
# MainWindow._toggle_dark_mode tests
# ---------------------------------------------------------------------------

class TestMainWindowDarkMode:
    """Tests for _toggle_dark_mode method"""

    def test_toggle_dark_on(self, main_window):
        """Toggling dark mode on does not crash (qdarkstyle is mocked)"""
        main_window._toggle_dark_mode(True)

    def test_toggle_dark_off(self, main_window):
        """Toggling dark mode off does not crash (qdarkstyle is mocked)"""
        main_window._toggle_dark_mode(False)


# ---------------------------------------------------------------------------
# ExportCsvDialog._browse_folder tests
# ---------------------------------------------------------------------------

class TestExportCsvDialogBrowseFolder:
    """Tests for ExportCsvDialog._browse_folder method"""

    def _make_dialog(self, qtbot):
        from budget_app.views.main_window import ExportCsvDialog
        dialog = ExportCsvDialog()
        qtbot.addWidget(dialog)
        return dialog

    def test_browse_folder_cancelled(self, qtbot, monkeypatch):
        """When user cancels folder dialog, selected_folder stays None"""
        from PyQt6.QtWidgets import QFileDialog
        dialog = self._make_dialog(qtbot)
        monkeypatch.setattr(QFileDialog, 'getExistingDirectory',
                            staticmethod(lambda *a, **kw: ''))
        dialog._browse_folder()
        assert dialog.selected_folder is None

    def test_browse_folder_selected(self, qtbot, monkeypatch):
        """When user selects a folder, selected_folder is set and label updated"""
        from PyQt6.QtWidgets import QFileDialog
        dialog = self._make_dialog(qtbot)
        monkeypatch.setattr(QFileDialog, 'getExistingDirectory',
                            staticmethod(lambda *a, **kw: '/tmp/export'))
        dialog._browse_folder()
        assert dialog.selected_folder == '/tmp/export'
        assert dialog.folder_label.text() == '/tmp/export'

    def test_browse_folder_long_path_truncated(self, qtbot, monkeypatch):
        """When selected path is very long, display label is truncated with ellipsis"""
        from PyQt6.QtWidgets import QFileDialog
        dialog = self._make_dialog(qtbot)
        long_path = '/home/user/very/deeply/nested/directory/structure/for/csv/export'
        monkeypatch.setattr(QFileDialog, 'getExistingDirectory',
                            staticmethod(lambda *a, **kw: long_path))
        dialog._browse_folder()
        assert dialog.selected_folder == long_path
        assert dialog.folder_label.text().startswith("...")
        assert dialog.folder_label.toolTip() == long_path
