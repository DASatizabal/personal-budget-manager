"""Transactions ledger view with running balances"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QFormLayout, QLineEdit,
    QComboBox, QHeaderView, QMessageBox, QDateEdit, QLabel,
    QCheckBox, QGroupBox, QProgressBar, QApplication, QMenu, QWidgetAction
)
from .widgets import NoScrollDoubleSpinBox, NoScrollSpinBox
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import QColor, QBrush, QCursor, QAction
from datetime import datetime, timedelta, date
import calendar

from ..models.transaction import Transaction
from ..models.credit_card import CreditCard
from ..models.account import Account
from ..models.recurring_charge import RecurringCharge
from ..models.paycheck import PaycheckConfig
from ..models.shared_expense import SharedExpense
from ..utils.calculations import calculate_running_balances, get_starting_balances


class TransactionsView(QWidget):
    """View for the transaction ledger with running balances"""

    def __init__(self):
        super().__init__()
        self._first_load = True
        self._data_dirty = True  # Track if data needs reload
        self._last_from_date = None
        self._last_to_date = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Toolbar
        toolbar = QHBoxLayout()

        add_btn = QPushButton("Add Transaction")
        add_btn.clicked.connect(self._add_transaction)
        toolbar.addWidget(add_btn)

        edit_btn = QPushButton("Edit Selected")
        edit_btn.clicked.connect(self._edit_transaction)
        toolbar.addWidget(edit_btn)

        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self._delete_transaction)
        toolbar.addWidget(delete_btn)

        delete_all_btn = QPushButton("Delete All")
        delete_all_btn.setToolTip("Delete all transactions from the database")
        delete_all_btn.clicked.connect(self._delete_all_transactions)
        toolbar.addWidget(delete_all_btn)

        toolbar.addWidget(QLabel("  |  "))

        generate_btn = QPushButton("Generate Recurring")
        generate_btn.setToolTip("Generate future transactions from recurring charges")
        generate_btn.clicked.connect(self._generate_recurring_transactions)
        toolbar.addWidget(generate_btn)

        clear_posted_btn = QPushButton("Clear Posted")
        clear_posted_btn.setToolTip("Remove all posted transactions (moves them to Posted tab)")
        clear_posted_btn.clicked.connect(self._clear_posted_transactions)
        toolbar.addWidget(clear_posted_btn)

        toolbar.addStretch()

        # Date filter
        toolbar.addWidget(QLabel("From:"))
        self.from_date = QDateEdit()
        self.from_date.setDate(QDate.currentDate().addDays(-7))
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("MM/dd/yyyy")
        toolbar.addWidget(self.from_date)

        toolbar.addWidget(QLabel("To:"))
        self.to_date = QDateEdit()
        self.to_date.setDate(QDate.currentDate().addMonths(3))
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("MM/dd/yyyy")
        toolbar.addWidget(self.to_date)

        filter_btn = QPushButton("Filter")
        filter_btn.clicked.connect(self.refresh)
        toolbar.addWidget(filter_btn)

        toolbar.addWidget(QLabel("  |  "))

        # Payment method filter button
        toolbar.addWidget(QLabel("Pay Types:"))
        self.pay_type_btn = QPushButton("All ▼")
        self.pay_type_menu = QMenu(self)
        self.pay_type_btn.setMenu(self.pay_type_menu)
        toolbar.addWidget(self.pay_type_btn)

        # Columns visibility button with dropdown menu
        self.columns_btn = QPushButton("Columns ▼")
        self.columns_menu = QMenu(self)
        self.columns_btn.setMenu(self.columns_menu)
        toolbar.addWidget(self.columns_btn)

        layout.addLayout(toolbar)

        # Filter row
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)

        filter_layout.addWidget(QLabel("Filters:"))

        # Description filter
        filter_layout.addWidget(QLabel("Description:"))
        self.desc_filter = QLineEdit()
        self.desc_filter.setPlaceholderText("Search...")
        self.desc_filter.setFixedWidth(150)
        self.desc_filter.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.desc_filter)

        # Amount min filter
        filter_layout.addWidget(QLabel("Amount Min:"))
        self.amount_min_filter = QLineEdit()
        self.amount_min_filter.setPlaceholderText("e.g. -500")
        self.amount_min_filter.setFixedWidth(80)
        self.amount_min_filter.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.amount_min_filter)

        # Amount max filter
        filter_layout.addWidget(QLabel("Max:"))
        self.amount_max_filter = QLineEdit()
        self.amount_max_filter.setPlaceholderText("e.g. 5000")
        self.amount_max_filter.setFixedWidth(80)
        self.amount_max_filter.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.amount_max_filter)

        # Show only positive/negative
        filter_layout.addWidget(QLabel("Show:"))
        self.amount_sign_filter = QComboBox()
        self.amount_sign_filter.addItems(["All", "Income (+)", "Expenses (-)"])
        self.amount_sign_filter.setFixedWidth(100)
        self.amount_sign_filter.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.amount_sign_filter)

        # Clear filters button
        clear_filters_btn = QPushButton("Clear Filters")
        clear_filters_btn.clicked.connect(self._clear_filters)
        filter_layout.addWidget(clear_filters_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Info label and progress bar
        info_layout = QHBoxLayout()
        self.info_label = QLabel()
        info_layout.addWidget(self.info_label)
        info_layout.addStretch()
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setVisible(False)
        info_layout.addWidget(self.progress_bar)
        layout.addLayout(info_layout)

        # Main table
        self.table = QTableWidget()
        self._setup_table_columns()
        layout.addWidget(self.table)

        # Summary section at bottom
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(24)

        self.chase_summary = QLabel("Chase: $0.00")
        self.chase_summary.setStyleSheet("font-weight: bold;")
        summary_layout.addWidget(self.chase_summary)

        self.total_avail_label = QLabel("Total CC Available: $0.00")
        self.total_avail_label.setStyleSheet("font-weight: bold;")
        summary_layout.addWidget(self.total_avail_label)

        self.total_util_label = QLabel("Utilization: 0%")
        self.total_util_label.setStyleSheet("font-weight: bold;")
        summary_layout.addWidget(self.total_util_label)

        summary_layout.addStretch()
        layout.addLayout(summary_layout)

    def _setup_table_columns(self):
        """Set up table columns dynamically based on available cards"""
        # Base columns - checkbox column first (checkmark symbol as header)
        self._base_columns = ["\u2713", "Date", "Pay Type", "Description", "Amount", "Chase Balance"]
        columns = self._base_columns.copy()

        # Add columns for each credit card (both Owed and Avail)
        self._cards = CreditCard.get_all()
        self._card_owed_columns = []
        self._card_avail_columns = []
        for card in self._cards:
            owed_col = f"{card.name} Owed"
            avail_col = f"{card.name} Avail"
            columns.append(owed_col)
            columns.append(avail_col)
            self._card_owed_columns.append(owed_col)
            self._card_avail_columns.append(avail_col)

        columns.append("CC Utilization")
        self._all_columns = columns

        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)

        # Make columns user-resizable
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)

        # Set default column widths
        default_widths = {
            "\u2713": 35,
            "Date": 90,
            "Pay Type": 70,
            "Description": 200,
            "Amount": 100,
            "Chase Balance": 110,
            "CC Utilization": 100
        }
        for i, col in enumerate(columns):
            if col in default_widths:
                self.table.setColumnWidth(i, default_widths[col])
            elif "Owed" in col or "Avail" in col:
                self.table.setColumnWidth(i, 95)

        # Restore saved column widths
        self._load_column_widths()

        # Connect to save column widths when resized
        header.sectionResized.connect(self._save_column_widths)

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_transaction)

        # Connect checkbox changes to handler
        self.table.itemChanged.connect(self._on_item_changed)

        # Set up the columns visibility menu
        self._setup_columns_menu()

        # Set up the payment type filter menu
        self._setup_pay_type_menu()

    def _save_column_widths(self):
        """Save column widths to settings"""
        settings = QSettings("BudgetApp", "PersonalBudgetManager")
        widths = []
        for i in range(self.table.columnCount()):
            widths.append(self.table.columnWidth(i))
        settings.setValue("transactions/column_widths", widths)

    def _load_column_widths(self):
        """Load column widths from settings"""
        settings = QSettings("BudgetApp", "PersonalBudgetManager")
        widths = settings.value("transactions/column_widths")
        if widths and len(widths) == self.table.columnCount():
            for i, width in enumerate(widths):
                if isinstance(width, int) and width > 0:
                    self.table.setColumnWidth(i, width)
                elif isinstance(width, str) and width.isdigit():
                    self.table.setColumnWidth(i, int(width))

    def _setup_columns_menu(self):
        """Set up the columns visibility menu"""
        self.columns_menu.clear()
        self._column_actions = {}

        # Make menu stay open for multi-select
        self.columns_menu.setToolTipsVisible(True)

        # Add "Show All" and "Hide CC Columns" quick actions
        show_all_action = QAction("Show All Columns", self)
        show_all_action.triggered.connect(self._show_all_columns)
        self.columns_menu.addAction(show_all_action)

        hide_cc_action = QAction("Hide All CC Columns", self)
        hide_cc_action.triggered.connect(self._hide_all_cc_columns)
        self.columns_menu.addAction(hide_cc_action)

        self.columns_menu.addSeparator()

        # CC column sorting options
        sort_high_low_action = QAction("Sort CC: High → Low Balance", self)
        sort_high_low_action.triggered.connect(lambda: self._sort_cc_columns(descending=True))
        self.columns_menu.addAction(sort_high_low_action)

        sort_low_high_action = QAction("Sort CC: Low → High Balance", self)
        sort_low_high_action.triggered.connect(lambda: self._sort_cc_columns(descending=False))
        self.columns_menu.addAction(sort_low_high_action)

        self.columns_menu.addSeparator()

        # Quick toggles for column groups
        show_owed_action = QAction("Show All 'Owed' Columns", self)
        show_owed_action.triggered.connect(lambda: self._toggle_column_group("Owed", True))
        self.columns_menu.addAction(show_owed_action)

        hide_owed_action = QAction("Hide All 'Owed' Columns", self)
        hide_owed_action.triggered.connect(lambda: self._toggle_column_group("Owed", False))
        self.columns_menu.addAction(hide_owed_action)

        show_avail_action = QAction("Show All 'Avail' Columns", self)
        show_avail_action.triggered.connect(lambda: self._toggle_column_group("Avail", True))
        self.columns_menu.addAction(show_avail_action)

        hide_avail_action = QAction("Hide All 'Avail' Columns", self)
        hide_avail_action.triggered.connect(lambda: self._toggle_column_group("Avail", False))
        self.columns_menu.addAction(hide_avail_action)

        self.columns_menu.addSeparator()

        # $0 Owed quick toggles
        show_zero_owed_action = QAction("Show all $0 Owed", self)
        show_zero_owed_action.triggered.connect(lambda: self._toggle_zero_owed_columns(True))
        self.columns_menu.addAction(show_zero_owed_action)

        hide_zero_owed_action = QAction("Hide all $0 Owed", self)
        hide_zero_owed_action.triggered.connect(lambda: self._toggle_zero_owed_columns(False))
        self.columns_menu.addAction(hide_zero_owed_action)

        self.columns_menu.addSeparator()

        # Load saved visibility settings
        settings = QSettings("BudgetApp", "PersonalBudgetManager")
        hidden_columns = settings.value("transactions/hidden_columns", [])
        if hidden_columns is None:
            hidden_columns = []

        # Add checkable action for each credit card column (both Owed and Avail)
        # Using QWidgetAction with QCheckBox so menu stays open for multi-select
        self._column_checkboxes = {}
        for i, col_name in enumerate(self._all_columns):
            if "Owed" in col_name or "Avail" in col_name:
                # Create checkbox widget
                checkbox = QCheckBox(col_name)
                checkbox.setChecked(col_name not in hidden_columns)
                checkbox.setStyleSheet("QCheckBox { padding: 4px 8px; }")
                checkbox.stateChanged.connect(lambda state, idx=i: self._toggle_column(idx, state == Qt.CheckState.Checked.value))

                # Wrap in QWidgetAction to keep menu open
                widget_action = QWidgetAction(self)
                widget_action.setDefaultWidget(checkbox)
                self.columns_menu.addAction(widget_action)

                self._column_actions[i] = widget_action
                self._column_checkboxes[i] = checkbox

                # Apply saved visibility - default: hide "Owed" columns initially
                if col_name in hidden_columns or ("Owed" in col_name and col_name not in hidden_columns and not settings.contains("transactions/hidden_columns")):
                    self.table.setColumnHidden(i, True)
                    checkbox.setChecked(False)

    def _toggle_column(self, column_index: int, visible: bool):
        """Toggle visibility of a column"""
        self.table.setColumnHidden(column_index, not visible)
        self._save_column_visibility()

    def _show_all_columns(self):
        """Show all columns"""
        for i in range(self.table.columnCount()):
            self.table.setColumnHidden(i, False)
            if i in self._column_checkboxes:
                self._column_checkboxes[i].setChecked(True)
        self._save_column_visibility()

    def _hide_all_cc_columns(self):
        """Hide all credit card columns"""
        for i, col_name in enumerate(self._all_columns):
            if "Owed" in col_name or "Avail" in col_name:
                self.table.setColumnHidden(i, True)
                if i in self._column_checkboxes:
                    self._column_checkboxes[i].setChecked(False)
        self._save_column_visibility()

    def _toggle_column_group(self, group_type: str, visible: bool):
        """Toggle visibility of a group of columns (Owed or Avail)"""
        for i, col_name in enumerate(self._all_columns):
            if group_type in col_name:
                self.table.setColumnHidden(i, not visible)
                if i in self._column_checkboxes:
                    self._column_checkboxes[i].setChecked(visible)
        self._save_column_visibility()

    def _toggle_zero_owed_columns(self, visible: bool):
        """Toggle visibility of Owed columns for credit cards with $0 balance"""
        # Get current card balances
        card_balances = {c.name: c.current_balance for c in self._cards}

        for i, col_name in enumerate(self._all_columns):
            if "Owed" in col_name:
                # Extract card name from column name (e.g., "Amex Owed" -> "Amex")
                card_name = col_name.replace(" Owed", "")
                # Check if this card has $0 balance
                if card_balances.get(card_name, -1) == 0:
                    self.table.setColumnHidden(i, not visible)
                    if i in self._column_checkboxes:
                        self._column_checkboxes[i].setChecked(visible)
        self._save_column_visibility()

    def _sort_cc_columns(self, descending: bool = True):
        """Sort credit card columns by current balance"""
        # Sort cards by balance
        sorted_cards = sorted(self._cards, key=lambda c: c.current_balance, reverse=descending)

        # Update the internal cards list
        self._cards = sorted_cards

        # Rebuild the table columns with new order
        self._rebuild_columns_with_sorted_cards()

        # Refresh data to populate with new column order
        self.mark_dirty()
        self.refresh()

    def _rebuild_columns_with_sorted_cards(self):
        """Rebuild column structure after sorting cards"""
        # Preserve current visibility settings
        settings = QSettings("BudgetApp", "PersonalBudgetManager")
        hidden_columns = settings.value("transactions/hidden_columns", [])
        if hidden_columns is None:
            hidden_columns = []

        # Rebuild columns list
        columns = self._base_columns.copy()
        self._card_owed_columns = []
        self._card_avail_columns = []

        for card in self._cards:
            owed_col = f"{card.name} Owed"
            avail_col = f"{card.name} Avail"
            columns.append(owed_col)
            columns.append(avail_col)
            self._card_owed_columns.append(owed_col)
            self._card_avail_columns.append(avail_col)

        columns.append("CC Utilization")
        self._all_columns = columns

        # Update table headers
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)

        # Set default column widths
        default_widths = {
            "\u2713": 35,
            "Date": 90,
            "Pay Type": 70,
            "Description": 200,
            "Amount": 100,
            "Chase Balance": 110,
            "CC Utilization": 100
        }
        for i, col in enumerate(columns):
            if col in default_widths:
                self.table.setColumnWidth(i, default_widths[col])
            elif "Owed" in col or "Avail" in col:
                self.table.setColumnWidth(i, 95)

        # Rebuild the columns menu
        self._setup_columns_menu()

        # Restore visibility settings
        for i, col_name in enumerate(self._all_columns):
            if col_name in hidden_columns:
                self.table.setColumnHidden(i, True)
                if i in self._column_checkboxes:
                    self._column_checkboxes[i].setChecked(False)

    def _save_column_visibility(self):
        """Save column visibility to settings"""
        settings = QSettings("BudgetApp", "PersonalBudgetManager")
        hidden = []
        for i, col_name in enumerate(self._all_columns):
            if self.table.isColumnHidden(i):
                hidden.append(col_name)
        settings.setValue("transactions/hidden_columns", hidden)

    def _setup_pay_type_menu(self):
        """Set up the payment type filter menu"""
        self.pay_type_menu.clear()
        self._pay_type_actions = {}

        # Add "All" and "None" quick actions
        all_action = QAction("Select All", self)
        all_action.triggered.connect(self._select_all_pay_types)
        self.pay_type_menu.addAction(all_action)

        none_action = QAction("Select None", self)
        none_action.triggered.connect(self._select_no_pay_types)
        self.pay_type_menu.addAction(none_action)

        self.pay_type_menu.addSeparator()

        # Add Chase (Bank account)
        chase_action = QAction("Chase (Bank)", self)
        chase_action.setCheckable(True)
        chase_action.setChecked(True)
        chase_action.setData("C")
        chase_action.triggered.connect(self._update_pay_type_filter)
        self.pay_type_menu.addAction(chase_action)
        self._pay_type_actions["C"] = chase_action

        # Add each credit card
        for card in self._cards:
            action = QAction(card.name, self)
            action.setCheckable(True)
            action.setChecked(True)
            action.setData(card.pay_type_code)
            action.triggered.connect(self._update_pay_type_filter)
            self.pay_type_menu.addAction(action)
            self._pay_type_actions[card.pay_type_code] = action

    def _select_all_pay_types(self):
        """Select all payment types"""
        for action in self._pay_type_actions.values():
            action.setChecked(True)
        self._update_pay_type_filter()

    def _select_no_pay_types(self):
        """Deselect all payment types"""
        for action in self._pay_type_actions.values():
            action.setChecked(False)
        self._update_pay_type_filter()

    def _update_pay_type_filter(self):
        """Update the filter button text and refresh if needed"""
        selected = [code for code, action in self._pay_type_actions.items() if action.isChecked()]
        total = len(self._pay_type_actions)

        if len(selected) == total:
            self.pay_type_btn.setText("All ▼")
        elif len(selected) == 0:
            self.pay_type_btn.setText("None ▼")
        else:
            self.pay_type_btn.setText(f"{len(selected)}/{total} ▼")

        self.mark_dirty()
        self.refresh()

    def _get_selected_pay_types(self) -> list:
        """Get list of selected payment type codes"""
        if not hasattr(self, '_pay_type_actions'):
            return None  # No filter applied
        return [code for code, action in self._pay_type_actions.items() if action.isChecked()]

    def mark_dirty(self):
        """Mark data as dirty so next refresh reloads from database"""
        self._data_dirty = True

    def _apply_filters(self):
        """Apply column filters to hide/show rows"""
        desc_filter = self.desc_filter.text().lower().strip()
        amount_min_text = self.amount_min_filter.text().strip()
        amount_max_text = self.amount_max_filter.text().strip()
        sign_filter = self.amount_sign_filter.currentIndex()  # 0=All, 1=Income, 2=Expenses

        # Parse amount filters
        amount_min = None
        amount_max = None
        try:
            if amount_min_text:
                amount_min = float(amount_min_text)
        except ValueError:
            pass
        try:
            if amount_max_text:
                amount_max = float(amount_max_text)
        except ValueError:
            pass

        # Apply filters to each row
        for row in range(self.table.rowCount()):
            show_row = True

            # Description filter (column 3)
            if desc_filter:
                desc_item = self.table.item(row, 3)
                if desc_item and desc_filter not in desc_item.text().lower():
                    show_row = False

            # Amount filter (column 4)
            if show_row and (amount_min is not None or amount_max is not None or sign_filter != 0):
                amount_item = self.table.item(row, 4)
                if amount_item:
                    try:
                        amount_text = amount_item.text().replace('$', '').replace(',', '').strip()
                        amount = float(amount_text)

                        # Check min/max
                        if amount_min is not None and amount < amount_min:
                            show_row = False
                        if amount_max is not None and amount > amount_max:
                            show_row = False

                        # Check sign filter
                        if sign_filter == 1 and amount <= 0:  # Income only
                            show_row = False
                        elif sign_filter == 2 and amount >= 0:  # Expenses only
                            show_row = False
                    except ValueError:
                        pass

            self.table.setRowHidden(row, not show_row)

    def _clear_filters(self):
        """Clear all column filters"""
        self.desc_filter.setText("")
        self.amount_min_filter.setText("")
        self.amount_max_filter.setText("")
        self.amount_sign_filter.setCurrentIndex(0)
        # Show all rows
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, False)

    def refresh(self):
        """Refresh the table with transactions and running balances"""
        # On first load, auto-generate recurring transactions if none exist
        if self._first_load:
            self._first_load = False
            self._auto_generate_if_needed()
            self._data_dirty = True  # Force load on first view

        # Check if date range changed
        current_from = self.from_date.date().toString("yyyy-MM-dd")
        current_to = self.to_date.date().toString("yyyy-MM-dd")
        dates_changed = (current_from != self._last_from_date or
                        current_to != self._last_to_date)

        # Skip refresh if data hasn't changed and dates are the same
        if not self._data_dirty and not dates_changed:
            return

        self._last_from_date = current_from
        self._last_to_date = current_to
        self._data_dirty = False

        # Show loading state
        self.info_label.setText("Loading transactions...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        QApplication.processEvents()

        try:
            # Get date range
            from_date = self.from_date.date().toString("yyyy-MM-dd")
            to_date = self.to_date.date().toString("yyyy-MM-dd")

            # Get transactions (only non-posted for planning view)
            all_transactions = Transaction.get_by_date_range(from_date, to_date)
            # Filter out posted transactions - they appear in the Posted tab
            all_transactions = [t for t in all_transactions if not t.is_posted]

            # Filter by selected payment types
            selected_pay_types = self._get_selected_pay_types()
            if selected_pay_types is not None and len(selected_pay_types) < len(self._pay_type_actions):
                transactions = [t for t in all_transactions if t.payment_method in selected_pay_types]
            else:
                transactions = all_transactions

            self.progress_bar.setValue(20)
            QApplication.processEvents()

            # Get starting balances
            starting = get_starting_balances()

            # Use self._cards for column mapping (preserves sort order)
            cards = self._cards
            card_codes = [c.pay_type_code for c in cards]
            card_limits = {c.pay_type_code: c.credit_limit for c in cards}
            self.progress_bar.setValue(30)
            QApplication.processEvents()

            # Calculate running balances (optimized inline version)
            running = starting.copy()
            total_limit = sum(c.credit_limit for c in cards)

            # Build cache of recurring charges that are credit card payments
            # Maps recurring_charge_id -> pay_type_code of the linked card
            cc_payment_map = {}
            card_id_to_code = {c.id: c.pay_type_code for c in cards}
            for charge in RecurringCharge.get_all():
                if charge.linked_card_id and charge.linked_card_id in card_id_to_code:
                    cc_payment_map[charge.id] = card_id_to_code[charge.linked_card_id]

            # Block table signals during population for performance
            self.table.blockSignals(True)
            self.table.setUpdatesEnabled(False)
            self.table.setRowCount(len(transactions))

            total_count = len(transactions)
            recurring_count = 0

            for row, trans in enumerate(transactions):
                if trans.recurring_charge_id:
                    recurring_count += 1

                method = trans.payment_method

                # Update the relevant balance - only for non-posted transactions
                # Posted transactions are already reflected in the current balance
                if method in running and not trans.is_posted:
                    running[method] += trans.amount

                    # If this is a credit card payment, also update the card's balance
                    # The payment reduces the card's debt (amount is negative, so it reduces owed)
                    if trans.recurring_charge_id in cc_payment_map:
                        linked_card_code = cc_payment_map[trans.recurring_charge_id]
                        if linked_card_code in running:
                            # Payment amount is negative (from Chase), apply as positive reduction to card debt
                            running[linked_card_code] += trans.amount  # trans.amount is already negative

                # Calculate utilization
                total_balance = sum(running.get(c.pay_type_code, 0) for c in cards)
                utilization = total_balance / total_limit if total_limit > 0 else 0

                # Posted checkbox (column 0)
                checkbox_item = QTableWidgetItem()
                checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                checkbox_item.setCheckState(Qt.CheckState.Checked if trans.is_posted else Qt.CheckState.Unchecked)
                checkbox_item.setData(Qt.ItemDataRole.UserRole, trans.id)  # Store transaction ID
                self.table.setItem(row, 0, checkbox_item)

                # Date - convert from YYYY-MM-DD to MM/DD/YYYY for display
                iso_date = trans.date[:10]
                display_date = f"{iso_date[5:7]}/{iso_date[8:10]}/{iso_date[:4]}"
                date_item = QTableWidgetItem(display_date)
                self.table.setItem(row, 1, date_item)

                # Pay Type
                self.table.setItem(row, 2, QTableWidgetItem(trans.payment_method))

                # Description - highlight recurring transactions
                desc_item = QTableWidgetItem(trans.description)
                desc_item.setData(Qt.ItemDataRole.UserRole, trans.id)
                if trans.recurring_charge_id:
                    desc_item.setForeground(QColor("#64b5f6"))
                self.table.setItem(row, 3, desc_item)

                # Amount
                amount_item = QTableWidgetItem(f"${trans.amount:,.2f}")
                if trans.amount < 0:
                    amount_item.setForeground(QColor("#f44336"))
                else:
                    amount_item.setForeground(QColor("#4caf50"))
                self.table.setItem(row, 4, amount_item)

                # Chase Balance
                chase_balance = running.get('C', 0)
                chase_item = QTableWidgetItem(f"${chase_balance:,.2f}")
                if chase_balance < 0:
                    chase_item.setForeground(QColor("#f44336"))
                elif chase_balance < 500:
                    chase_item.setForeground(QColor("#ff9800"))
                self.table.setItem(row, 5, chase_item)

                # Credit card Owed and Available columns
                for i, code in enumerate(card_codes):
                    owed = running.get(code, 0)
                    avail = card_limits.get(code, 0) - owed

                    # Owed column
                    owed_item = QTableWidgetItem(f"${owed:,.2f}")
                    if owed > card_limits.get(code, 0):
                        owed_item.setForeground(QColor("#f44336"))
                    elif owed > card_limits.get(code, 0) * 0.8:
                        owed_item.setForeground(QColor("#ff9800"))
                    self.table.setItem(row, 6 + (i * 2), owed_item)

                    # Avail column
                    avail_item = QTableWidgetItem(f"${avail:,.2f}")
                    if avail < 0:
                        avail_item.setForeground(QColor("#f44336"))
                    elif avail < 100:
                        avail_item.setForeground(QColor("#ff9800"))
                    self.table.setItem(row, 6 + (i * 2) + 1, avail_item)

                # Utilization (after all card columns)
                util_col = 6 + (len(card_codes) * 2)
                util_item = QTableWidgetItem(f"{utilization * 100:.1f}%")
                if utilization > 0.8:
                    util_item.setForeground(QColor("#f44336"))
                elif utilization > 0.5:
                    util_item.setForeground(QColor("#ff9800"))
                self.table.setItem(row, util_col, util_item)

                # Update progress every 50 rows
                if row % 50 == 0:
                    progress = 30 + int((row / max(total_count, 1)) * 65)
                    self.progress_bar.setValue(progress)
                    QApplication.processEvents()

            # Re-enable table updates
            self.table.setUpdatesEnabled(True)
            self.table.blockSignals(False)

            # Update info label
            self.info_label.setText(
                f"Showing {total_count} transactions ({recurring_count} recurring, "
                f"{total_count - recurring_count} manual)"
            )
            self.progress_bar.setValue(100)

            # Update summary section with final balances
            final_chase = running.get('C', 0)
            final_total_balance = sum(running.get(c.pay_type_code, 0) for c in cards)
            final_total_avail = total_limit - final_total_balance
            final_util = final_total_balance / total_limit if total_limit > 0 else 0

            self.chase_summary.setText(f"Chase: ${final_chase:,.2f}")
            if final_chase < 0:
                self.chase_summary.setStyleSheet("font-weight: bold; color: #f44336;")
            elif final_chase < 500:
                self.chase_summary.setStyleSheet("font-weight: bold; color: #ff9800;")
            else:
                self.chase_summary.setStyleSheet("font-weight: bold; color: #4caf50;")

            self.total_avail_label.setText(f"Total CC Available: ${final_total_avail:,.2f}")
            if final_total_avail < 0:
                self.total_avail_label.setStyleSheet("font-weight: bold; color: #f44336;")
            else:
                self.total_avail_label.setStyleSheet("font-weight: bold; color: #4caf50;")

            self.total_util_label.setText(f"Utilization: {final_util * 100:.1f}%")
            if final_util > 0.8:
                self.total_util_label.setStyleSheet("font-weight: bold; color: #f44336;")
            elif final_util > 0.5:
                self.total_util_label.setStyleSheet("font-weight: bold; color: #ff9800;")
            else:
                self.total_util_label.setStyleSheet("font-weight: bold; color: #4caf50;")

        finally:
            QApplication.restoreOverrideCursor()
            self.progress_bar.setVisible(False)

    def _auto_generate_if_needed(self):
        """Auto-generate recurring transactions if none exist"""
        # Check if there are any future transactions
        today = datetime.now().strftime('%Y-%m-%d')
        future_trans = Transaction.get_future_transactions(today)

        if len(future_trans) == 0:
            # No future transactions - generate them automatically
            self._do_generate_recurring(show_message=False)

    def _generate_recurring_transactions(self):
        """Show dialog to generate recurring transactions"""
        dialog = GenerateRecurringDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            months = dialog.get_months()
            clear_existing = dialog.get_clear_existing()
            self._do_generate_recurring(months, clear_existing, show_message=True)

    def _do_generate_recurring(self, months: int = 3, clear_existing: bool = True,
                                show_message: bool = True):
        """Actually generate the recurring transactions"""
        from ..utils.calculations import generate_future_transactions

        today = datetime.now().date()

        if clear_existing:
            # Delete future recurring transactions
            Transaction.delete_future_recurring(today.strftime('%Y-%m-%d'))

        # Generate transactions using the centralized function (includes interest charges)
        transactions = generate_future_transactions(months_ahead=months)
        for trans in transactions:
            trans.save()

        if show_message:
            end_date = today + timedelta(days=months * 30)
            QMessageBox.information(
                self,
                "Generation Complete",
                f"Generated {len(transactions)} recurring transactions\n"
                f"From {today} to {end_date}"
            )

        self.mark_dirty()
        self.refresh()

    def _generate_special_charges(self, start_date: date, end_date: date,
                                   charges: list, paycheck: PaycheckConfig = None,
                                   lisa_linked_ids: set = None) -> int:
        """Generate transactions for special frequency charges"""
        count = 0
        special_charges = [c for c in charges if c.frequency == 'SPECIAL']

        # Get payday from config (default to Friday=4)
        pay_day = paycheck.pay_day_of_week if paycheck else 4

        # Default to empty set if not provided
        if lisa_linked_ids is None:
            lisa_linked_ids = set()

        for charge in special_charges:
            # Skip Lisa payment codes (996-999) - handled separately based on paycheck count
            if charge.day_of_month >= 996:
                continue

            # Skip charges linked to Lisa Payments (handled in payday generation)
            if charge.id in lisa_linked_ids:
                continue

            if charge.day_of_month == 991:
                # Mortgage - bi-weekly, aligned with payday
                current = start_date
                days_until_payday = (pay_day - current.weekday()) % 7
                if days_until_payday == 0:
                    days_until_payday = 7
                current += timedelta(days=days_until_payday)

                while current <= end_date:
                    trans = Transaction(
                        id=None,
                        date=current.strftime('%Y-%m-%d'),
                        description=charge.name,
                        amount=charge.amount,
                        payment_method='C',
                        recurring_charge_id=charge.id,
                        is_posted=False
                    )
                    trans.save()
                    count += 1
                    current += timedelta(days=14)

            elif charge.day_of_month in [992, 993, 994, 995]:
                # Monthly special charges - on the 15th
                current = date(start_date.year, start_date.month, 15)
                if current < start_date:
                    if current.month == 12:
                        current = date(current.year + 1, 1, 15)
                    else:
                        current = date(current.year, current.month + 1, 15)

                while current <= end_date:
                    if charge.amount != 0:  # Skip zero amounts
                        trans = Transaction(
                            id=None,
                            date=current.strftime('%Y-%m-%d'),
                            description=charge.name,
                            amount=charge.amount,
                            payment_method='C',
                            recurring_charge_id=charge.id,
                            is_posted=False
                        )
                        trans.save()
                        count += 1

                    if current.month == 12:
                        current = date(current.year + 1, 1, 15)
                    else:
                        current = date(current.year, current.month + 1, 15)

        return count

    def _generate_payday_transactions(self, start_date: date, end_date: date,
                                       paycheck: PaycheckConfig) -> int:
        """Generate payday and Lisa payment transactions"""
        count = 0

        if paycheck.pay_frequency != 'BIWEEKLY':
            return count

        # Use effective_date as the anchor for bi-weekly pay schedule
        # Parse effective_date to get the reference payday
        anchor_date = datetime.strptime(paycheck.effective_date, '%Y-%m-%d').date()

        # Calculate the first payday on or after start_date
        # Find how many days between anchor and start_date
        days_diff = (start_date - anchor_date).days

        # Find how many 14-day periods fit in that difference
        periods = days_diff // 14
        if days_diff % 14 != 0 and days_diff > 0:
            periods += 1  # Round up to next payday

        # First payday is anchor + (periods * 14 days)
        current = anchor_date + timedelta(days=periods * 14)

        # If current is before start_date (can happen with negative periods), move forward
        while current < start_date:
            current += timedelta(days=14)

        # Get Lisa payment charges
        lisa_2_charge = RecurringCharge.get_by_name('Lisa')
        lisa_3_charge = RecurringCharge.get_by_name('Lisa3')

        while current <= end_date:
            # Add payday
            trans = Transaction(
                id=None,
                date=current.strftime('%Y-%m-%d'),
                description='Payday',
                amount=paycheck.net_pay,
                payment_method='C',
                recurring_charge_id=None,
                is_posted=False
            )
            trans.save()
            count += 1

            # Add LDBPD marker (day before payday)
            ldbpd_date = current - timedelta(days=1)
            if ldbpd_date >= start_date:
                ldbpd = Transaction(
                    id=None,
                    date=ldbpd_date.strftime('%Y-%m-%d'),
                    description='LDBPD',
                    amount=0,
                    payment_method='C',
                    recurring_charge_id=None,
                    is_posted=False,
                    notes='Pay period boundary marker'
                )
                ldbpd.save()
                count += 1

            # Determine if this is a 2 or 3 paycheck month and add Lisa payment
            paycheck_count = self._count_paydays_in_month(current.year, current.month)

            if paycheck_count == 3 and lisa_3_charge:
                lisa_amount = lisa_3_charge.amount
                lisa_charge_id = lisa_3_charge.id
            elif lisa_2_charge:
                lisa_amount = lisa_2_charge.amount
                lisa_charge_id = lisa_2_charge.id
            else:
                lisa_amount = 0
                lisa_charge_id = None

            if lisa_amount != 0:
                lisa_trans = Transaction(
                    id=None,
                    date=current.strftime('%Y-%m-%d'),
                    description='Lisa',
                    amount=lisa_amount,
                    payment_method='C',
                    recurring_charge_id=lisa_charge_id,
                    is_posted=False
                )
                lisa_trans.save()
                count += 1

            current += timedelta(days=14)

        return count

    def _count_paydays_in_month(self, year: int, month: int) -> int:
        """Count how many Fridays fall in a given month (assuming bi-weekly Friday paydays)"""
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        # Find first Friday
        days_until_friday = (4 - first_day.weekday()) % 7
        first_friday = first_day + timedelta(days=days_until_friday)

        count = 0
        current = first_friday
        while current <= last_day:
            count += 1
            current += timedelta(days=7)

        # For bi-weekly, typically 2 paychecks per month, sometimes 3
        # If 5 Fridays, likely 3 paydays; if 4, likely 2
        return 3 if count >= 5 else 2

    def _on_item_changed(self, item: QTableWidgetItem):
        """Handle item changes - specifically checkbox state changes"""
        # Only process checkbox column (column 0)
        if item.column() != 0:
            return

        # Get transaction ID from the item's user data
        trans_id = item.data(Qt.ItemDataRole.UserRole)
        if not trans_id:
            return

        # Determine new posted state from checkbox
        is_posted = item.checkState() == Qt.CheckState.Checked

        # Update transaction in database
        trans = Transaction.get_by_id(trans_id)
        if trans and trans.is_posted != is_posted:
            # Set posted_date when marking as posted
            if is_posted:
                trans.posted_date = datetime.now().strftime('%Y-%m-%d')
                # Update account/card balances
                self._update_balances_for_posted_transaction(trans)
            else:
                trans.posted_date = None
                # Reverse the balance updates
                self._reverse_balances_for_unposted_transaction(trans)

            trans.is_posted = is_posted
            trans.save()

            # Notify parent window to refresh dashboard
            self._notify_balance_change()

    def _update_balances_for_posted_transaction(self, trans: Transaction):
        """Update account/card balances when a transaction is marked as posted"""
        from ..models.account import Account
        from ..models.credit_card import CreditCard

        # Update the primary account/card (payment_method)
        if trans.payment_method == 'C':
            # Chase (checking account)
            account = Account.get_by_code('C')
            if account:
                account.current_balance += trans.amount
                account.save()
        else:
            # Credit card - the transaction is a charge TO the card
            card = CreditCard.get_by_code(trans.payment_method)
            if card:
                card.current_balance += trans.amount
                card.save()

        # If this is a CC payment from Chase, also update the linked card
        if trans.recurring_charge_id and trans.payment_method == 'C':
            charge = RecurringCharge.get_by_id(trans.recurring_charge_id)
            if charge and charge.linked_card_id:
                linked_card = CreditCard.get_by_id(charge.linked_card_id)
                if linked_card:
                    # Payment reduces the CC balance (trans.amount is negative, so this reduces debt)
                    linked_card.current_balance += trans.amount
                    linked_card.save()

    def _reverse_balances_for_unposted_transaction(self, trans: Transaction):
        """Reverse balance updates when a transaction is unmarked as posted"""
        from ..models.account import Account
        from ..models.credit_card import CreditCard

        # Reverse the primary account/card update
        if trans.payment_method == 'C':
            account = Account.get_by_code('C')
            if account:
                account.current_balance -= trans.amount
                account.save()
        else:
            card = CreditCard.get_by_code(trans.payment_method)
            if card:
                card.current_balance -= trans.amount
                card.save()

        # Reverse linked CC update if applicable
        if trans.recurring_charge_id and trans.payment_method == 'C':
            charge = RecurringCharge.get_by_id(trans.recurring_charge_id)
            if charge and charge.linked_card_id:
                linked_card = CreditCard.get_by_id(charge.linked_card_id)
                if linked_card:
                    linked_card.current_balance -= trans.amount
                    linked_card.save()

    def _notify_balance_change(self):
        """Notify parent window that balances have changed"""
        # Find main window and refresh dashboard and posted views
        parent = self.parent()
        while parent:
            if hasattr(parent, 'dashboard_view'):
                parent.dashboard_view.mark_dirty()
            if hasattr(parent, 'posted_transactions_view'):
                parent.posted_transactions_view.mark_dirty()
                break
            parent = parent.parent()

    def _get_selected_transaction_id(self) -> int:
        """Get the ID of the selected transaction"""
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        # Transaction ID is stored in column 3 (Description) or column 0 (Checkbox)
        return self.table.item(row, 3).data(Qt.ItemDataRole.UserRole)

    def _add_transaction(self):
        """Add a new transaction"""
        dialog = TransactionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            trans = dialog.get_transaction()
            trans.save()
            self.mark_dirty()
            self.refresh()

    def _edit_transaction(self):
        """Edit the selected transaction"""
        trans_id = self._get_selected_transaction_id()
        if not trans_id:
            QMessageBox.warning(self, "Warning", "Please select a transaction to edit")
            return

        trans = Transaction.get_by_id(trans_id)
        if trans:
            dialog = TransactionDialog(self, trans)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                updated = dialog.get_transaction()
                updated.id = trans.id
                updated.save()
                self.mark_dirty()
                self.refresh()

    def _delete_transaction(self):
        """Delete the selected transaction"""
        trans_id = self._get_selected_transaction_id()
        if not trans_id:
            QMessageBox.warning(self, "Warning", "Please select a transaction to delete")
            return

        trans = Transaction.get_by_id(trans_id)
        if trans:
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Are you sure you want to delete '{trans.description}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                trans.delete()
                self.mark_dirty()
                self.refresh()

    def _delete_all_transactions(self):
        """Delete all transactions from the database"""
        # Get count for confirmation message
        from ..models.database import Database
        db = Database()
        count = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]

        if count == 0:
            QMessageBox.information(self, "Info", "There are no transactions to delete.")
            return

        reply = QMessageBox.warning(
            self,
            "Confirm Delete All",
            f"This will permanently delete ALL {count} transactions.\n\n"
            "This action cannot be undone.\n\n"
            "Are you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Double confirmation for safety
            reply2 = QMessageBox.warning(
                self,
                "Final Confirmation",
                "Are you absolutely sure?\n\nAll transaction data will be lost.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply2 == QMessageBox.StandardButton.Yes:
                db.execute("DELETE FROM transactions")
                db.commit()
                QMessageBox.information(self, "Deleted", f"Deleted {count} transactions.")
                self.mark_dirty()
                self.refresh()

    def _clear_posted_transactions(self):
        """Clear all posted transactions from the Transactions view"""
        # Get count of posted transactions
        posted = Transaction.get_posted()
        count = len(posted)

        if count == 0:
            QMessageBox.information(
                self,
                "No Posted Transactions",
                "There are no posted transactions to clear.\n\n"
                "Use the checkbox column to mark transactions as posted."
            )
            return

        reply = QMessageBox.question(
            self,
            "Clear Posted Transactions",
            f"This will remove {count} posted transaction(s) from this view.\n\n"
            "They will still be available in the 'Posted' tab.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Posted transactions are already marked - just refresh to hide them
            # The Posted tab shows is_posted=True, Transactions tab shows is_posted=False
            self.mark_dirty()
            self.refresh()
            # Notify Posted tab to refresh
            self._notify_balance_change()
            QMessageBox.information(
                self,
                "Cleared",
                f"Cleared {count} posted transaction(s).\n\n"
                "View them in the 'Posted' tab."
            )


class GenerateRecurringDialog(QDialog):
    """Dialog for generating recurring transactions"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generate Recurring Transactions")
        self.setMinimumWidth(350)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI"""
        layout = QVBoxLayout(self)

        # Info
        info_label = QLabel(
            "This will generate future transactions based on your recurring charges, "
            "paydays, and Lisa payments."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Options
        form_layout = QFormLayout()

        self.months_spin = NoScrollSpinBox()
        self.months_spin.setRange(1, 24)
        self.months_spin.setValue(3)
        self.months_spin.setSuffix(" months")
        form_layout.addRow("Generate for:", self.months_spin)

        self.clear_check = QCheckBox("Clear existing future recurring transactions")
        self.clear_check.setChecked(True)
        form_layout.addRow("", self.clear_check)

        layout.addLayout(form_layout)

        # Summary of what will be generated
        charges = RecurringCharge.get_all(active_only=True)
        regular_count = sum(1 for c in charges if c.frequency != 'SPECIAL')
        special_count = sum(1 for c in charges if c.frequency == 'SPECIAL')

        summary = QGroupBox("Will Generate")
        summary_layout = QVBoxLayout(summary)
        summary_layout.addWidget(QLabel(f"- {regular_count} regular monthly charges"))
        summary_layout.addWidget(QLabel(f"- {special_count} special charges (mortgage, etc.)"))
        summary_layout.addWidget(QLabel("- Bi-weekly paydays"))
        summary_layout.addWidget(QLabel("- Lisa payments (based on paycheck count)"))
        summary_layout.addWidget(QLabel("- Credit card interest charges"))
        layout.addWidget(summary)

        # Buttons
        btn_layout = QHBoxLayout()
        generate_btn = QPushButton("Generate")
        generate_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(generate_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def get_months(self) -> int:
        return self.months_spin.value()

    def get_clear_existing(self) -> bool:
        return self.clear_check.isChecked()


class TransactionDialog(QDialog):
    """Dialog for adding/editing a transaction"""

    def __init__(self, parent=None, transaction: Transaction = None):
        super().__init__(parent)
        self.transaction = transaction
        self.setWindowTitle("Edit Transaction" if transaction else "Add Transaction")
        self.setMinimumWidth(400)
        self._setup_ui()
        if transaction:
            self._populate_fields()

    def _setup_ui(self):
        """Set up the dialog UI"""
        layout = QFormLayout(self)

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("MM/dd/yyyy")
        layout.addRow("Date:", self.date_edit)

        self.desc_edit = QLineEdit()
        layout.addRow("Description:", self.desc_edit)

        self.amount_spin = NoScrollDoubleSpinBox()
        self.amount_spin.setRange(-1000000, 1000000)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setPrefix("$")
        layout.addRow("Amount (negative = expense):", self.amount_spin)

        self.method_combo = QComboBox()
        self._load_payment_methods()
        layout.addRow("Payment Method:", self.method_combo)

        self.posted_check = QCheckBox()
        layout.addRow("Posted:", self.posted_check)

        self.notes_edit = QLineEdit()
        layout.addRow("Notes:", self.notes_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._validate_and_accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def _validate_and_accept(self):
        """Validate form inputs before accepting"""
        errors = []

        description = self.desc_edit.text().strip()
        if not description:
            errors.append("Description is required.")

        if errors:
            QMessageBox.warning(self, "Validation Error", "\n".join(errors))
            return

        self.accept()

    def _load_payment_methods(self):
        """Load available payment methods"""
        self.method_combo.addItem("Chase (Bank)", "C")
        for card in CreditCard.get_all():
            self.method_combo.addItem(card.name, card.pay_type_code)

    def _populate_fields(self):
        """Populate fields with existing transaction data"""
        date_str = self.transaction.date[:10]  # Handle datetime strings
        date = QDate.fromString(date_str, "yyyy-MM-dd")
        self.date_edit.setDate(date)
        self.desc_edit.setText(self.transaction.description)
        self.amount_spin.setValue(self.transaction.amount)

        # Find and select payment method
        for i in range(self.method_combo.count()):
            if self.method_combo.itemData(i) == self.transaction.payment_method:
                self.method_combo.setCurrentIndex(i)
                break

        self.posted_check.setChecked(self.transaction.is_posted)
        self.notes_edit.setText(self.transaction.notes or "")

    def get_transaction(self) -> Transaction:
        """Get the transaction from the form values"""
        return Transaction(
            id=None,
            date=self.date_edit.date().toString("yyyy-MM-dd"),
            description=self.desc_edit.text().strip(),
            amount=self.amount_spin.value(),
            payment_method=self.method_combo.currentData(),
            recurring_charge_id=None,
            is_posted=self.posted_check.isChecked(),
            notes=self.notes_edit.text().strip() or None
        )
