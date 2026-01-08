"""Transactions ledger view with running balances"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QFormLayout, QLineEdit,
    QComboBox, QHeaderView, QMessageBox, QDateEdit, QLabel,
    QCheckBox, QGroupBox, QProgressBar, QApplication, QMenu
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
        # Base columns
        self._base_columns = ["Date", "Pay Type", "Description", "Amount", "Chase Balance"]
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

        # Add "Show All" and "Hide CC Columns" quick actions
        show_all_action = QAction("Show All Columns", self)
        show_all_action.triggered.connect(self._show_all_columns)
        self.columns_menu.addAction(show_all_action)

        hide_cc_action = QAction("Hide All CC Columns", self)
        hide_cc_action.triggered.connect(self._hide_all_cc_columns)
        self.columns_menu.addAction(hide_cc_action)

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

        # Load saved visibility settings
        settings = QSettings("BudgetApp", "PersonalBudgetManager")
        hidden_columns = settings.value("transactions/hidden_columns", [])
        if hidden_columns is None:
            hidden_columns = []

        # Add checkable action for each credit card column (both Owed and Avail)
        for i, col_name in enumerate(self._all_columns):
            if "Owed" in col_name or "Avail" in col_name:
                action = QAction(col_name, self)
                action.setCheckable(True)
                action.setChecked(col_name not in hidden_columns)
                action.setData(i)  # Store column index
                action.triggered.connect(lambda checked, idx=i: self._toggle_column(idx, checked))
                self.columns_menu.addAction(action)
                self._column_actions[i] = action

                # Apply saved visibility - default: hide "Owed" columns initially
                if col_name in hidden_columns or ("Owed" in col_name and col_name not in hidden_columns and not settings.contains("transactions/hidden_columns")):
                    self.table.setColumnHidden(i, True)
                    action.setChecked(False)

    def _toggle_column(self, column_index: int, visible: bool):
        """Toggle visibility of a column"""
        self.table.setColumnHidden(column_index, not visible)
        self._save_column_visibility()

    def _show_all_columns(self):
        """Show all columns"""
        for i in range(self.table.columnCount()):
            self.table.setColumnHidden(i, False)
            if i in self._column_actions:
                self._column_actions[i].setChecked(True)
        self._save_column_visibility()

    def _hide_all_cc_columns(self):
        """Hide all credit card columns"""
        for i, col_name in enumerate(self._all_columns):
            if "Owed" in col_name or "Avail" in col_name:
                self.table.setColumnHidden(i, True)
                if i in self._column_actions:
                    self._column_actions[i].setChecked(False)
        self._save_column_visibility()

    def _toggle_column_group(self, group_type: str, visible: bool):
        """Toggle visibility of a group of columns (Owed or Avail)"""
        for i, col_name in enumerate(self._all_columns):
            if group_type in col_name:
                self.table.setColumnHidden(i, not visible)
                if i in self._column_actions:
                    self._column_actions[i].setChecked(visible)
        self._save_column_visibility()

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

            # Get transactions
            all_transactions = Transaction.get_by_date_range(from_date, to_date)

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

            # Get cards once for column mapping (avoid redundant queries)
            cards = CreditCard.get_all()
            card_codes = [c.pay_type_code for c in cards]
            card_limits = {c.pay_type_code: c.credit_limit for c in cards}
            self.progress_bar.setValue(30)
            QApplication.processEvents()

            # Calculate running balances (optimized inline version)
            running = starting.copy()
            total_limit = sum(c.credit_limit for c in cards)

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

                # Update the relevant balance
                if method in running:
                    running[method] += trans.amount

                # Calculate utilization
                total_balance = sum(running.get(c.pay_type_code, 0) for c in cards)
                utilization = total_balance / total_limit if total_limit > 0 else 0

                # Date - convert from YYYY-MM-DD to MM/DD/YYYY for display
                iso_date = trans.date[:10]
                display_date = f"{iso_date[5:7]}/{iso_date[8:10]}/{iso_date[:4]}"
                date_item = QTableWidgetItem(display_date)
                self.table.setItem(row, 0, date_item)

                # Pay Type
                self.table.setItem(row, 1, QTableWidgetItem(trans.payment_method))

                # Description - highlight recurring transactions
                desc_item = QTableWidgetItem(trans.description)
                desc_item.setData(Qt.ItemDataRole.UserRole, trans.id)
                if trans.recurring_charge_id:
                    desc_item.setForeground(QColor("#64b5f6"))
                self.table.setItem(row, 2, desc_item)

                # Amount
                amount_item = QTableWidgetItem(f"${trans.amount:,.2f}")
                if trans.amount < 0:
                    amount_item.setForeground(QColor("#f44336"))
                else:
                    amount_item.setForeground(QColor("#4caf50"))
                self.table.setItem(row, 3, amount_item)

                # Chase Balance
                chase_balance = running.get('C', 0)
                chase_item = QTableWidgetItem(f"${chase_balance:,.2f}")
                if chase_balance < 0:
                    chase_item.setForeground(QColor("#f44336"))
                elif chase_balance < 500:
                    chase_item.setForeground(QColor("#ff9800"))
                self.table.setItem(row, 4, chase_item)

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
                    self.table.setItem(row, 5 + (i * 2), owed_item)

                    # Avail column
                    avail_item = QTableWidgetItem(f"${avail:,.2f}")
                    if avail < 0:
                        avail_item.setForeground(QColor("#f44336"))
                    elif avail < 100:
                        avail_item.setForeground(QColor("#ff9800"))
                    self.table.setItem(row, 5 + (i * 2) + 1, avail_item)

                # Utilization (after all card columns)
                util_col = 5 + (len(card_codes) * 2)
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
        today = datetime.now().date()

        if clear_existing:
            # Delete future recurring transactions
            Transaction.delete_future_recurring(today.strftime('%Y-%m-%d'))

        # Get all active recurring charges
        charges = RecurringCharge.get_all(active_only=True)

        # Get IDs of charges linked to shared expenses (Lisa Payments)
        # These are handled separately in payday generation
        lisa_linked_ids = SharedExpense.get_linked_recurring_ids()

        # Get paycheck config
        paycheck = PaycheckConfig.get_current()

        generated_count = 0
        end_date = today + timedelta(days=months * 30)

        # Generate regular monthly charges
        current_date = today
        while current_date <= end_date:
            day = current_date.day

            for charge in charges:
                # Skip special frequency charges (handled separately)
                if charge.frequency == 'SPECIAL':
                    continue

                # Skip charges with special day codes (991-999)
                if charge.day_of_month >= 991:
                    continue

                # Skip charges linked to Lisa Payments (handled in payday generation)
                if charge.id in lisa_linked_ids:
                    continue

                # Handle day 32 as last day of month
                charge_day = charge.day_of_month
                if charge_day == 32:
                    # Last day of month
                    last_day = calendar.monthrange(current_date.year, current_date.month)[1]
                    charge_day = last_day

                if charge_day == day:
                    amount = charge.get_actual_amount()
                    # Skip if amount is 0 and it's not a credit card payment marker
                    if amount == 0 and charge.amount_type != 'CREDIT_CARD_BALANCE':
                        continue

                    trans = Transaction(
                        id=None,
                        date=current_date.strftime('%Y-%m-%d'),
                        description=charge.name,
                        amount=amount,
                        payment_method=charge.payment_method,
                        recurring_charge_id=charge.id,
                        is_posted=False
                    )
                    trans.save()
                    generated_count += 1

            current_date += timedelta(days=1)

        # Generate special charges (pass lisa_linked_ids to exclude linked charges)
        generated_count += self._generate_special_charges(today, end_date, charges, paycheck, lisa_linked_ids)

        # Generate payday transactions
        if paycheck:
            generated_count += self._generate_payday_transactions(today, end_date, paycheck)

        if show_message:
            QMessageBox.information(
                self,
                "Generation Complete",
                f"Generated {generated_count} recurring transactions\n"
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

    def _get_selected_transaction_id(self) -> int:
        """Get the ID of the selected transaction"""
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        return self.table.item(row, 2).data(Qt.ItemDataRole.UserRole)

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
