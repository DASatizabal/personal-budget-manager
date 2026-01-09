"""Main application window"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QMenuBar, QMenu, QStatusBar, QMessageBox,
    QFileDialog, QPushButton, QLabel, QDialog, QCheckBox,
    QGroupBox, QDialogButtonBox, QDateEdit
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QAction, QKeySequence

from .dashboard_view import DashboardView
from .credit_cards_view import CreditCardsView
from .recurring_charges_view import RecurringChargesView
from .transactions_view import TransactionsView
from .posted_transactions_view import PostedTransactionsView
from .paycheck_view import PaycheckView
from .shared_expenses_view import SharedExpensesView
from ..models.database import init_db
from ..utils.excel_import import import_from_excel
from ..utils.backup import (
    create_auto_backup, get_auto_backups, restore_from_backup,
    get_most_recent_backup
)


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
        self.posted_transactions_view = PostedTransactionsView()
        self.paycheck_view = PaycheckView()
        self.shared_expenses_view = SharedExpensesView()

        # Add tabs
        self.tabs.addTab(self.dashboard_view, "Dashboard")
        self.tabs.addTab(self.transactions_view, "Transactions")
        self.tabs.addTab(self.posted_transactions_view, "Posted")
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

        # Edit menu
        edit_menu = menu_bar.addMenu("&Edit")

        undo_action = QAction("&Undo Last Operation", self)
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        undo_action.triggered.connect(self._undo_last_operation)
        edit_menu.addAction(undo_action)

        restore_auto_action = QAction("&Restore from Auto-Backup...", self)
        restore_auto_action.triggered.connect(self._restore_from_auto_backup)
        edit_menu.addAction(restore_auto_action)

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
            # Confirm before importing (will overwrite existing data)
            reply = QMessageBox.warning(
                self,
                "Confirm Import",
                "This will replace all existing data with data from the Excel file.\n\n"
                "Are you sure you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            # Create auto-backup before destructive operation
            backup_path = create_auto_backup("excel_import")
            if backup_path:
                self.status_bar.showMessage("Auto-backup created", 2000)

            try:
                results = import_from_excel(file_path)

                # Build success message
                msg_parts = [
                    "Import successful!\n",
                    f"Credit Cards: {results['credit_cards']}",
                    f"Loans: {results['loans']}",
                    f"Recurring Charges: {results['recurring_charges']}",
                    f"Accounts: {results['accounts']}",
                    f"Paycheck Configs: {results['paycheck_configs']}",
                    f"Shared Expenses: {results['shared_expenses']}"
                ]

                # Add warnings if any
                warnings = results.get('warnings', [])
                if warnings:
                    msg_parts.append(f"\n--- Warnings ({len(warnings)}) ---")
                    # Show first 10 warnings max
                    for warn in warnings[:10]:
                        msg_parts.append(f"• {warn}")
                    if len(warnings) > 10:
                        msg_parts.append(f"... and {len(warnings) - 10} more warnings")

                msg = "\n".join(msg_parts)
                QMessageBox.information(self, "Import Complete", msg)
                self._refresh_current_view()

            except FileNotFoundError as e:
                QMessageBox.critical(
                    self,
                    "File Not Found",
                    f"Could not find the Excel file:\n{str(e)}"
                )
            except Exception as e:
                # Show detailed error message
                error_msg = str(e)
                QMessageBox.critical(
                    self,
                    "Import Error",
                    f"Failed to import data from Excel file.\n\n{error_msg}\n\n"
                    "Please ensure the Excel file has the required sheets:\n"
                    "• Credit Card Info\n"
                    "• Summary\n"
                    "• Reoccuring Charges"
                )

    def _export_csv(self):
        """Export data to CSV"""
        dialog = ExportCsvDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            folder = dialog.selected_folder
            tables = dialog.selected_tables
            start_date = dialog.start_date
            end_date = dialog.end_date

            if not folder:
                return

            if not tables:
                QMessageBox.warning(self, "Export", "No tables selected for export.")
                return

            try:
                from pathlib import Path
                from ..utils.csv_export import export_all

                results = export_all(
                    Path(folder),
                    tables,
                    start_date,
                    end_date
                )

                summary = "\n".join([f"  {table}: {count} rows" for table, count in results.items()])
                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"CSV files exported to:\n{folder}\n\n{summary}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")

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

                # Create auto-backup before restore
                create_auto_backup("before_restore")

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
        from .transactions_view import GenerateRecurringDialog
        from ..utils.calculations import generate_future_transactions
        from ..models.transaction import Transaction

        dialog = GenerateRecurringDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            months = dialog.get_months()
            clear_existing = dialog.get_clear_existing()

            # Create auto-backup before deleting transactions
            create_auto_backup("generate_transactions")

            try:
                if clear_existing:
                    # Delete existing future recurring transactions
                    Transaction.delete_future_recurring()

                # Generate new ones
                transactions = generate_future_transactions(months_ahead=months)
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
        dialog = RecalculateBalancesDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._refresh_current_view()
            self.status_bar.showMessage("Balances updated", 2000)

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

    def _undo_last_operation(self):
        """Undo the last operation by restoring from the most recent auto-backup"""
        backup = get_most_recent_backup()

        if not backup:
            QMessageBox.information(
                self,
                "No Backup Available",
                "No auto-backup is available to restore from.\n\n"
                "Auto-backups are created before major operations like:\n"
                "- Excel import\n"
                "- Database restore\n"
                "- Generate transactions"
            )
            return

        backup_path, backup_time, operation = backup
        time_str = backup_time.strftime("%m/%d/%Y %I:%M %p")

        reply = QMessageBox.question(
            self,
            "Confirm Undo",
            f"Restore to the state before '{operation}'?\n\n"
            f"Backup created: {time_str}\n\n"
            "This will replace all current data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if restore_from_backup(backup_path):
                init_db()  # Reinitialize database
                QMessageBox.information(self, "Undo Complete", "Data restored successfully!")
                self._refresh_current_view()
            else:
                QMessageBox.critical(self, "Error", "Failed to restore from backup.")

    def _restore_from_auto_backup(self):
        """Show dialog to select an auto-backup to restore from"""
        backups = get_auto_backups()

        if not backups:
            QMessageBox.information(
                self,
                "No Backups",
                "No auto-backups are available.\n\n"
                "Auto-backups are created automatically before major operations."
            )
            return

        dialog = AutoBackupRestoreDialog(self, backups)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_backup:
            backup_path = dialog.selected_backup

            if restore_from_backup(backup_path):
                init_db()  # Reinitialize database
                QMessageBox.information(self, "Restore Complete", "Data restored successfully!")
                self._refresh_current_view()
            else:
                QMessageBox.critical(self, "Error", "Failed to restore from backup.")


class AutoBackupRestoreDialog(QDialog):
    """Dialog for selecting an auto-backup to restore from"""

    def __init__(self, parent, backups):
        super().__init__(parent)
        self.setWindowTitle("Restore from Auto-Backup")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        self.selected_backup = None
        self.backups = backups
        self._setup_ui()

    def _setup_ui(self):
        from PyQt6.QtWidgets import QListWidget, QListWidgetItem

        layout = QVBoxLayout(self)

        # Instructions
        info = QLabel(
            "Select a backup to restore from. The most recent backup is at the top.\n"
            "Warning: This will replace all current data."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Backup list
        self.backup_list = QListWidget()
        for backup_path, backup_time, operation in self.backups:
            time_str = backup_time.strftime("%m/%d/%Y %I:%M %p")
            item = QListWidgetItem(f"{time_str} - {operation}")
            item.setData(Qt.ItemDataRole.UserRole, backup_path)
            self.backup_list.addItem(item)
        layout.addWidget(self.backup_list)

        # Buttons
        btn_layout = QHBoxLayout()
        restore_btn = QPushButton("Restore Selected")
        restore_btn.clicked.connect(self._on_restore)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(restore_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _on_restore(self):
        current_item = self.backup_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a backup to restore.")
            return

        self.selected_backup = current_item.data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.question(
            self,
            "Confirm Restore",
            "This will replace all current data with the selected backup.\n\n"
            "Are you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.accept()


class ExportCsvDialog(QDialog):
    """Dialog for selecting CSV export options"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export to CSV")
        self.setMinimumWidth(400)

        self.selected_folder = None
        self.selected_tables = []
        self.start_date = None
        self.end_date = None

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Folder selection
        folder_group = QGroupBox("Export Location")
        folder_layout = QHBoxLayout(folder_group)
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setStyleSheet("color: #888;")
        folder_btn = QPushButton("Browse...")
        folder_btn.clicked.connect(self._browse_folder)
        folder_layout.addWidget(self.folder_label, 1)
        folder_layout.addWidget(folder_btn)
        layout.addWidget(folder_group)

        # Table selection
        tables_group = QGroupBox("Data to Export")
        tables_layout = QVBoxLayout(tables_group)

        self.table_checkboxes = {}
        table_options = [
            ('accounts', 'Accounts'),
            ('credit_cards', 'Credit Cards'),
            ('loans', 'Loans'),
            ('recurring_charges', 'Recurring Charges'),
            ('transactions', 'Transactions'),
            ('paycheck', 'Paycheck Configuration'),
            ('shared_expenses', 'Shared Expenses (Lisa Payments)'),
        ]

        for key, label in table_options:
            cb = QCheckBox(label)
            cb.setChecked(True)
            self.table_checkboxes[key] = cb
            tables_layout.addWidget(cb)

        # Select all / none buttons
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(lambda: self._set_all_checked(False))
        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(select_none_btn)
        btn_layout.addStretch()
        tables_layout.addLayout(btn_layout)

        layout.addWidget(tables_group)

        # Transaction date filter
        date_group = QGroupBox("Transaction Date Range (Optional)")
        date_layout = QHBoxLayout(date_group)

        date_layout.addWidget(QLabel("From:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-12))
        self.start_date_edit.setDisplayFormat("MM/dd/yyyy")
        self.start_date_edit.setSpecialValueText(" ")
        self.start_date_cb = QCheckBox()
        self.start_date_cb.setChecked(False)
        self.start_date_edit.setEnabled(False)
        self.start_date_cb.toggled.connect(self.start_date_edit.setEnabled)
        date_layout.addWidget(self.start_date_cb)
        date_layout.addWidget(self.start_date_edit)

        date_layout.addSpacing(20)

        date_layout.addWidget(QLabel("To:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setDisplayFormat("MM/dd/yyyy")
        self.end_date_edit.setSpecialValueText(" ")
        self.end_date_cb = QCheckBox()
        self.end_date_cb.setChecked(False)
        self.end_date_edit.setEnabled(False)
        self.end_date_cb.toggled.connect(self.end_date_edit.setEnabled)
        date_layout.addWidget(self.end_date_cb)
        date_layout.addWidget(self.end_date_edit)

        date_layout.addStretch()
        layout.addWidget(date_group)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _browse_folder(self):
        """Open folder selection dialog"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Export Folder",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.selected_folder = folder
            # Show truncated path if too long
            display_path = folder if len(folder) < 40 else "..." + folder[-37:]
            self.folder_label.setText(display_path)
            self.folder_label.setStyleSheet("")
            self.folder_label.setToolTip(folder)

    def _set_all_checked(self, checked: bool):
        """Set all table checkboxes to checked/unchecked"""
        for cb in self.table_checkboxes.values():
            cb.setChecked(checked)

    def _on_accept(self):
        """Handle dialog acceptance"""
        if not self.selected_folder:
            QMessageBox.warning(self, "Export", "Please select an export folder.")
            return

        self.selected_tables = [
            key for key, cb in self.table_checkboxes.items() if cb.isChecked()
        ]

        if self.start_date_cb.isChecked():
            self.start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        if self.end_date_cb.isChecked():
            self.end_date = self.end_date_edit.date().toString("yyyy-MM-dd")

        self.accept()


class RecalculateBalancesDialog(QDialog):
    """Dialog for viewing and adjusting account balances"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recalculate Balances")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)

        from ..models.account import Account
        from ..models.credit_card import CreditCard
        from ..models.loan import Loan
        from ..models.database import Database

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Instructions
        instructions = QLabel(
            "Compare stored balances with calculated balances based on posted transactions.\n"
            "Enter your actual balance from bank statements in the 'Actual Balance' column, then click Apply."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Create table
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Account", "Type", "Stored Balance", "Transaction Sum", "Calculated", "Actual Balance"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 6):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        # Load data
        self.balance_data = []
        self._load_balances(Account, CreditCard, Loan, Database)

        # Buttons
        button_layout = QHBoxLayout()
        apply_btn = QPushButton("Apply Changes")
        apply_btn.clicked.connect(self._apply_changes)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(apply_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

    def _load_balances(self, Account, CreditCard, Loan, Database):
        """Load all account balances and calculate transaction sums"""
        from PyQt6.QtWidgets import QTableWidgetItem
        from .widgets import NoScrollDoubleSpinBox

        db = Database()

        # Accounts
        for account in Account.get_all():
            if account.pay_type_code:
                trans_sum = self._get_transaction_sum(db, account.pay_type_code)
                self.balance_data.append({
                    'type': 'account',
                    'id': account.id,
                    'name': account.name,
                    'account_type': account.account_type,
                    'pay_type_code': account.pay_type_code,
                    'stored_balance': account.current_balance,
                    'trans_sum': trans_sum
                })

        # Credit Cards
        for card in CreditCard.get_all():
            trans_sum = self._get_transaction_sum(db, card.pay_type_code)
            self.balance_data.append({
                'type': 'credit_card',
                'id': card.id,
                'name': card.name,
                'account_type': 'CREDIT CARD',
                'pay_type_code': card.pay_type_code,
                'stored_balance': card.current_balance,
                'trans_sum': trans_sum
            })

        # Loans
        for loan in Loan.get_all():
            trans_sum = self._get_transaction_sum(db, loan.pay_type_code)
            self.balance_data.append({
                'type': 'loan',
                'id': loan.id,
                'name': loan.name,
                'account_type': 'LOAN',
                'pay_type_code': loan.pay_type_code,
                'stored_balance': loan.current_balance,
                'trans_sum': trans_sum
            })

        # Populate table
        self.table.setRowCount(len(self.balance_data))
        self.spinboxes = []

        for row, data in enumerate(self.balance_data):
            calculated = data['stored_balance'] + data['trans_sum']

            # Account name
            self.table.setItem(row, 0, QTableWidgetItem(f"{data['name']} ({data['pay_type_code']})"))

            # Account type
            self.table.setItem(row, 1, QTableWidgetItem(data['account_type']))

            # Stored balance
            stored_item = QTableWidgetItem(f"${data['stored_balance']:,.2f}")
            stored_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 2, stored_item)

            # Transaction sum
            trans_item = QTableWidgetItem(f"${data['trans_sum']:+,.2f}")
            trans_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, trans_item)

            # Calculated balance
            calc_item = QTableWidgetItem(f"${calculated:,.2f}")
            calc_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 4, calc_item)

            # Actual balance spinbox
            spinbox = NoScrollDoubleSpinBox()
            spinbox.setRange(-999999.99, 999999.99)
            spinbox.setDecimals(2)
            spinbox.setPrefix("$ ")
            spinbox.setValue(calculated)
            self.spinboxes.append(spinbox)
            self.table.setCellWidget(row, 5, spinbox)

    def _get_transaction_sum(self, db, pay_type_code: str) -> float:
        """Get sum of posted transactions for a payment method"""
        result = db.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM transactions
            WHERE payment_method = ? AND is_posted = 1
        """, (pay_type_code,)).fetchone()
        return result[0] or 0.0

    def _apply_changes(self):
        """Apply the actual balance changes to the database"""
        from ..models.account import Account
        from ..models.credit_card import CreditCard
        from ..models.loan import Loan

        changes_made = 0

        for row, data in enumerate(self.balance_data):
            new_balance = self.spinboxes[row].value()
            calculated = data['stored_balance'] + data['trans_sum']

            # Only update if different from calculated
            if abs(new_balance - calculated) > 0.001:
                # Need to adjust the stored balance
                # new_balance = stored_balance + trans_sum
                # So: stored_balance = new_balance - trans_sum
                adjusted_stored = new_balance - data['trans_sum']

                if data['type'] == 'account':
                    account = Account.get_by_id(data['id'])
                    if account:
                        account.current_balance = adjusted_stored
                        account.save()
                        changes_made += 1
                elif data['type'] == 'credit_card':
                    card = CreditCard.get_by_id(data['id'])
                    if card:
                        card.current_balance = adjusted_stored
                        card.save()
                        changes_made += 1
                elif data['type'] == 'loan':
                    loan = Loan.get_by_id(data['id'])
                    if loan:
                        loan.current_balance = adjusted_stored
                        loan.save()
                        changes_made += 1

        if changes_made > 0:
            QMessageBox.information(
                self,
                "Balances Updated",
                f"Updated {changes_made} balance(s)."
            )
            self.accept()
        else:
            QMessageBox.information(
                self,
                "No Changes",
                "No balance adjustments were made."
            )
