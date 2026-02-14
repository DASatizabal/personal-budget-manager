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
