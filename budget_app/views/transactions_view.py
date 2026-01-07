"""Transactions ledger view with running balances"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QComboBox, QHeaderView, QMessageBox, QDateEdit, QLabel,
    QCheckBox, QSpinBox, QGroupBox, QProgressBar, QApplication
)
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QCursor
from datetime import datetime, timedelta, date
import calendar

from ..models.transaction import Transaction
from ..models.credit_card import CreditCard
from ..models.account import Account
from ..models.recurring_charge import RecurringCharge
from ..models.paycheck import PaycheckConfig
from ..utils.calculations import calculate_running_balances, get_starting_balances


class TransactionsView(QWidget):
    """View for the transaction ledger with running balances"""

    def __init__(self):
        super().__init__()
        self._first_load = True
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

    def _setup_table_columns(self):
        """Set up table columns dynamically based on available cards"""
        # Base columns
        columns = ["Date", "Pay Type", "Description", "Amount", "Chase Balance"]

        # Add columns for each credit card
        cards = CreditCard.get_all()
        for card in cards:
            columns.append(f"{card.name} Avail")

        columns.append("CC Utilization")

        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_transaction)

    def refresh(self):
        """Refresh the table with transactions and running balances"""
        # On first load, auto-generate recurring transactions if none exist
        if self._first_load:
            self._first_load = False
            self._auto_generate_if_needed()

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
            transactions = Transaction.get_by_date_range(from_date, to_date)
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

                # Credit card available credit columns
                for i, code in enumerate(card_codes):
                    avail = card_limits.get(code, 0) - running.get(code, 0)
                    avail_item = QTableWidgetItem(f"${avail:,.2f}")
                    if avail < 0:
                        avail_item.setForeground(QColor("#f44336"))
                    elif avail < 100:
                        avail_item.setForeground(QColor("#ff9800"))
                    self.table.setItem(row, 5 + i, avail_item)

                # Utilization
                util_item = QTableWidgetItem(f"{utilization * 100:.1f}%")
                if utilization > 0.8:
                    util_item.setForeground(QColor("#f44336"))
                elif utilization > 0.5:
                    util_item.setForeground(QColor("#ff9800"))
                self.table.setItem(row, 5 + len(card_codes), util_item)

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

        # Get paycheck config
        paycheck = PaycheckConfig.get_current()

        generated_count = 0
        end_date = today + timedelta(days=months * 30)

        # Generate regular monthly charges
        current_date = today
        while current_date <= end_date:
            day = current_date.day

            for charge in charges:
                # Skip special frequency and zero-amount charges
                if charge.frequency == 'SPECIAL':
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

        # Generate special charges
        generated_count += self._generate_special_charges(today, end_date, charges)

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

        self.refresh()

    def _generate_special_charges(self, start_date: date, end_date: date,
                                   charges: list) -> int:
        """Generate transactions for special frequency charges"""
        count = 0
        special_charges = [c for c in charges if c.frequency == 'SPECIAL']

        for charge in special_charges:
            # Skip Lisa payment codes (996-999) - handled separately based on paycheck count
            if charge.day_of_month >= 996:
                continue

            if charge.day_of_month == 991:
                # Mortgage - bi-weekly, aligned with payday
                current = start_date
                days_until_friday = (4 - current.weekday()) % 7
                if days_until_friday == 0:
                    days_until_friday = 7
                current += timedelta(days=days_until_friday)

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

        # Find first Friday
        current = start_date
        days_until_friday = (4 - current.weekday()) % 7
        if days_until_friday == 0:
            days_until_friday = 7
        current += timedelta(days=days_until_friday)

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

        self.months_spin = QSpinBox()
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

        self.amount_spin = QDoubleSpinBox()
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
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

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
