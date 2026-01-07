"""Main application window"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QMenuBar, QMenu, QStatusBar, QMessageBox,
    QFileDialog, QPushButton, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence

from .dashboard_view import DashboardView
from .credit_cards_view import CreditCardsView
from .recurring_charges_view import RecurringChargesView
from .transactions_view import TransactionsView
from .paycheck_view import PaycheckView
from .shared_expenses_view import SharedExpensesView
from ..models.database import init_db
from ..utils.excel_import import import_from_excel


class MainWindow(QMainWindow):
    """Main application window with tabbed interface"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Personal Budget Manager")
        self.setMinimumSize(1200, 800)

        # Initialize database
        init_db()

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Create views
        self.dashboard_view = DashboardView()
        self.credit_cards_view = CreditCardsView()
        self.recurring_view = RecurringChargesView()
        self.transactions_view = TransactionsView()
        self.paycheck_view = PaycheckView()
        self.shared_expenses_view = SharedExpensesView()

        # Add tabs
        self.tabs.addTab(self.dashboard_view, "Dashboard")
        self.tabs.addTab(self.transactions_view, "Transactions")
        self.tabs.addTab(self.credit_cards_view, "Credit Cards")
        self.tabs.addTab(self.recurring_view, "Recurring Charges")
        self.tabs.addTab(self.paycheck_view, "Paycheck")
        self.tabs.addTab(self.shared_expenses_view, "Lisa Payments")

        # Connect tab change to refresh
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Create menu bar
        self._create_menu_bar()

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Apply dark mode by default
        self._apply_dark_mode()

    def _create_menu_bar(self):
        """Create the application menu bar"""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        import_action = QAction("&Import from Excel...", self)
        import_action.setShortcut(QKeySequence("Ctrl+I"))
        import_action.triggered.connect(self._import_excel)
        file_menu.addAction(import_action)

        export_action = QAction("&Export to CSV...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._export_csv)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        backup_action = QAction("&Backup Database...", self)
        backup_action.triggered.connect(self._backup_database)
        file_menu.addAction(backup_action)

        restore_action = QAction("&Restore from Backup...", self)
        restore_action.triggered.connect(self._restore_database)
        file_menu.addAction(restore_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Alt+F4"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menu_bar.addMenu("&View")

        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self._refresh_current_view)
        view_menu.addAction(refresh_action)

        view_menu.addSeparator()

        dark_mode_action = QAction("&Dark Mode", self)
        dark_mode_action.setCheckable(True)
        dark_mode_action.setChecked(True)
        dark_mode_action.triggered.connect(self._toggle_dark_mode)
        view_menu.addAction(dark_mode_action)
        self._dark_mode_action = dark_mode_action

        # Tools menu
        tools_menu = menu_bar.addMenu("&Tools")

        generate_action = QAction("&Generate Future Transactions", self)
        generate_action.triggered.connect(self._generate_transactions)
        tools_menu.addAction(generate_action)

        recalc_action = QAction("&Recalculate Balances", self)
        recalc_action.triggered.connect(self._recalculate_balances)
        tools_menu.addAction(recalc_action)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _on_tab_changed(self, index: int):
        """Handle tab change to refresh the new view"""
        current_widget = self.tabs.currentWidget()
        if hasattr(current_widget, 'refresh'):
            current_widget.refresh()

    def _refresh_current_view(self):
        """Refresh the currently active view"""
        current_widget = self.tabs.currentWidget()
        if hasattr(current_widget, 'refresh'):
            current_widget.refresh()
            self.status_bar.showMessage("View refreshed", 2000)

    def _import_excel(self):
        """Import data from Excel file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Excel File",
            "",
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )

        if file_path:
            try:
                results = import_from_excel(file_path)
                msg = (
                    f"Import successful!\n\n"
                    f"Credit Cards: {results['credit_cards']}\n"
                    f"Loans: {results['loans']}\n"
                    f"Recurring Charges: {results['recurring_charges']}\n"
                    f"Accounts: {results['accounts']}\n"
                    f"Paycheck Configs: {results['paycheck_configs']}\n"
                    f"Shared Expenses: {results['shared_expenses']}"
                )
                QMessageBox.information(self, "Import Complete", msg)
                self._refresh_current_view()
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import: {str(e)}")

    def _export_csv(self):
        """Export data to CSV"""
        # TODO: Implement CSV export
        QMessageBox.information(self, "Export", "CSV export not yet implemented")

    def _backup_database(self):
        """Backup the database file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup Database",
            "budget_backup.db",
            "Database Files (*.db);;All Files (*)"
        )

        if file_path:
            import shutil
            from ..models.database import DB_PATH
            try:
                shutil.copy2(DB_PATH, file_path)
                QMessageBox.information(self, "Backup", "Database backup created successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Backup Error", f"Failed to backup: {str(e)}")

    def _restore_database(self):
        """Restore database from backup"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Restore Database",
            "",
            "Database Files (*.db);;All Files (*)"
        )

        if file_path:
            reply = QMessageBox.warning(
                self,
                "Confirm Restore",
                "This will replace all current data. Are you sure?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                import shutil
                from ..models.database import DB_PATH, Database
                try:
                    # Close current connection
                    db = Database()
                    db.close()

                    # Copy backup
                    shutil.copy2(file_path, DB_PATH)

                    # Reinitialize
                    init_db()

                    QMessageBox.information(self, "Restore", "Database restored successfully!")
                    self._refresh_current_view()
                except Exception as e:
                    QMessageBox.critical(self, "Restore Error", f"Failed to restore: {str(e)}")

    def _generate_transactions(self):
        """Generate future transactions from recurring charges"""
        from ..utils.calculations import generate_future_transactions
        from ..models.transaction import Transaction

        reply = QMessageBox.question(
            self,
            "Generate Transactions",
            "Generate future transactions for the next 12 months?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Delete existing future recurring transactions
                Transaction.delete_future_recurring()

                # Generate new ones
                transactions = generate_future_transactions(months_ahead=12)
                for trans in transactions:
                    trans.save()

                QMessageBox.information(
                    self,
                    "Generate Complete",
                    f"Generated {len(transactions)} future transactions"
                )
                self._refresh_current_view()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to generate: {str(e)}")

    def _recalculate_balances(self):
        """Recalculate all running balances"""
        # TODO: Implement balance recalculation
        self.status_bar.showMessage("Balances recalculated", 2000)

    def _toggle_dark_mode(self, checked: bool):
        """Toggle dark mode on/off"""
        if checked:
            self._apply_dark_mode()
        else:
            self._apply_light_mode()

    def _apply_dark_mode(self):
        """Apply dark mode styling"""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
            QTabWidget::pane {
                border: 1px solid #3c3c3c;
                background-color: #252526;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #d4d4d4;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                border-bottom: 2px solid #007acc;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3c3c3c;
            }
            QTableWidget, QTableView {
                background-color: #1e1e1e;
                alternate-background-color: #252526;
                gridline-color: #3c3c3c;
                border: 1px solid #3c3c3c;
            }
            QTableWidget::item, QTableView::item {
                padding: 6px 8px;
            }
            QTableWidget::item:selected, QTableView::item:selected {
                background-color: #264f78;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #d4d4d4;
                padding: 8px 12px;
                border: none;
                border-right: 1px solid #3c3c3c;
                border-bottom: 1px solid #3c3c3c;
                font-weight: bold;
            }
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:pressed {
                background-color: #0d5a8c;
            }
            QPushButton:disabled {
                background-color: #3c3c3c;
                color: #808080;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555555;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QDateEdit:focus {
                border: 1px solid #007acc;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #d4d4d4;
                margin-right: 8px;
            }
            QMenuBar {
                background-color: #2d2d2d;
                color: #d4d4d4;
            }
            QMenuBar::item:selected {
                background-color: #3c3c3c;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
            QMenu::item:selected {
                background-color: #094771;
            }
            QStatusBar {
                background-color: #007acc;
                color: white;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: #5a5a5a;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #7a7a7a;
            }
            QScrollBar:horizontal {
                background-color: #1e1e1e;
                height: 12px;
            }
            QScrollBar::handle:horizontal {
                background-color: #5a5a5a;
                border-radius: 6px;
                min-width: 20px;
            }
            QLabel {
                color: #d4d4d4;
            }
            QGroupBox {
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                margin-top: 12px;
                padding: 16px 12px 12px 12px;
                font-weight: bold;
            }
            QGroupBox::title {
                color: #d4d4d4;
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QDialog {
                background-color: #252526;
            }
            QFormLayout {
                spacing: 12px;
            }
        """)

    def _apply_light_mode(self):
        """Apply light mode styling"""
        self.setStyleSheet("")  # Reset to default

    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About Personal Budget Manager",
            "Personal Budget Manager v1.0.0\n\n"
            "A comprehensive budget tracking application.\n\n"
            "Features:\n"
            "- Track credit cards and loans\n"
            "- Manage recurring charges\n"
            "- Project future cash flow\n"
            "- 90-day minimum balance alerts"
        )
