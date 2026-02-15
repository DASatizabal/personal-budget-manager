"""PDF Import view for parsing bank and credit card statements"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QComboBox,
    QHeaderView, QFileDialog, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ..models.credit_card import CreditCard
from ..models.account import Account
from ..models.transaction import Transaction
from ..utils.statement_parser import (
    parse_statement, StatementData, match_account
)


class PDFImportView(QWidget):
    """View for importing transactions from PDF statements"""

    def __init__(self):
        super().__init__()
        self._statement = None  # Current parsed statement
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── Top toolbar ──
        toolbar = QHBoxLayout()

        select_btn = QPushButton("Select PDF...")
        select_btn.clicked.connect(self._select_pdf)
        toolbar.addWidget(select_btn)

        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #888;")
        toolbar.addWidget(self.file_label, 1)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear)
        toolbar.addWidget(clear_btn)

        layout.addLayout(toolbar)

        # ── Statement Summary ──
        summary_group = QGroupBox("Statement Summary")
        summary_layout = QVBoxLayout(summary_group)

        # Row 1: institution, type, last4, period
        row1 = QHBoxLayout()
        self.institution_label = QLabel("Institution: —")
        row1.addWidget(self.institution_label)
        self.type_label = QLabel("Type: —")
        row1.addWidget(self.type_label)
        self.last4_label = QLabel("Account: —")
        row1.addWidget(self.last4_label)
        self.period_label = QLabel("Period: —")
        row1.addWidget(self.period_label)
        summary_layout.addLayout(row1)

        # Row 2: balances, limit, interest, fees
        row2 = QHBoxLayout()
        self.prev_balance_label = QLabel("Prev Balance: —")
        row2.addWidget(self.prev_balance_label)
        self.new_balance_label = QLabel("New Balance: —")
        row2.addWidget(self.new_balance_label)
        self.limit_label = QLabel("Credit Limit: —")
        row2.addWidget(self.limit_label)
        self.interest_label = QLabel("Interest: —")
        row2.addWidget(self.interest_label)
        self.fees_label = QLabel("Fees: —")
        row2.addWidget(self.fees_label)
        summary_layout.addLayout(row2)

        # Row 3: min payment, due date, payslip info
        row3 = QHBoxLayout()
        self.min_payment_label = QLabel("Min Payment: —")
        row3.addWidget(self.min_payment_label)
        self.due_date_label = QLabel("Due Date: —")
        row3.addWidget(self.due_date_label)
        self.payslip_label = QLabel("")
        row3.addWidget(self.payslip_label)
        row3.addStretch()
        summary_layout.addLayout(row3)

        layout.addWidget(summary_group)

        # ── Account Mapping ──
        mapping_layout = QHBoxLayout()

        mapping_layout.addWidget(QLabel("Import to Account:"))
        self.account_combo = QComboBox()
        self.account_combo.setMinimumWidth(200)
        mapping_layout.addWidget(self.account_combo)

        self.auto_match_label = QLabel("")
        self.auto_match_label.setStyleSheet("color: #4caf50;")
        mapping_layout.addWidget(self.auto_match_label)

        mapping_layout.addStretch()

        self.update_balance_check = QCheckBox("Update account balance to statement balance")
        self.update_balance_check.setChecked(True)
        mapping_layout.addWidget(self.update_balance_check)

        layout.addLayout(mapping_layout)

        # ── Transactions Table ──
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Date", "Post Date", "Description", "Amount", "Category"
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        # ── Import Options + Button ──
        bottom_layout = QHBoxLayout()

        self.mark_posted_check = QCheckBox("Mark imported transactions as posted")
        self.mark_posted_check.setChecked(True)
        bottom_layout.addWidget(self.mark_posted_check)

        bottom_layout.addStretch()

        self.status_label = QLabel("")
        bottom_layout.addWidget(self.status_label)

        self.import_btn = QPushButton("Import Transactions")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self._import_transactions)
        self.import_btn.setStyleSheet(
            "QPushButton { background-color: #4caf50; color: white; "
            "padding: 8px 24px; font-weight: bold; }"
            "QPushButton:disabled { background-color: #ccc; color: #666; }"
        )
        bottom_layout.addWidget(self.import_btn)

        layout.addLayout(bottom_layout)

    def _load_accounts(self):
        """Load accounts and cards into the combo box"""
        self.account_combo.clear()
        self.account_combo.addItem("— Select Account —", None)

        for acct in Account.get_all():
            if acct.pay_type_code:
                self.account_combo.addItem(
                    f"{acct.name} ({acct.account_type})", acct.pay_type_code
                )

        for card in CreditCard.get_all():
            self.account_combo.addItem(
                f"{card.name} (CC)", card.pay_type_code
            )

    def _select_pdf(self):
        """Open file dialog and parse selected PDF"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF Statement", "",
            "PDF Files (*.pdf);;All Files (*)"
        )
        if not file_path:
            return

        try:
            self._statement = parse_statement(file_path)
        except Exception as e:
            QMessageBox.warning(
                self, "Parse Error",
                f"Could not parse statement:\n{e}"
            )
            return

        # Update file label
        import os
        self.file_label.setText(os.path.basename(file_path))
        self.file_label.setStyleSheet("color: inherit;")

        # Update summary
        self._update_summary()

        # Load accounts and auto-match
        self._load_accounts()
        self._auto_match_account()

        # Populate transactions table
        self._populate_table()

        # Enable import button
        self.import_btn.setEnabled(len(self._statement.transactions) > 0)

    def _update_summary(self):
        """Update the summary labels from parsed statement"""
        s = self._statement
        if not s:
            return

        self.institution_label.setText(f"Institution: {s.institution}")
        self.type_label.setText(f"Type: {s.statement_type}")
        self.last4_label.setText(
            f"Account: ***{s.account_last4}" if s.account_last4 else "Account: —"
        )

        if s.period_start and s.period_end:
            self.period_label.setText(f"Period: {s.period_start} to {s.period_end}")
        elif s.period_end:
            self.period_label.setText(f"Closing: {s.period_end}")
        else:
            self.period_label.setText("Period: —")

        self.prev_balance_label.setText(f"Prev Balance: ${s.previous_balance:,.2f}")
        self.new_balance_label.setText(f"New Balance: ${s.new_balance:,.2f}")
        self.limit_label.setText(
            f"Credit Limit: ${s.credit_limit:,.2f}" if s.credit_limit else "Credit Limit: —"
        )
        self.interest_label.setText(f"Interest: ${s.interest_total:,.2f}")
        self.fees_label.setText(f"Fees: ${s.fees_total:,.2f}")
        self.min_payment_label.setText(
            f"Min Payment: ${s.minimum_payment:,.2f}" if s.minimum_payment else "Min Payment: —"
        )
        self.due_date_label.setText(
            f"Due Date: {s.payment_due_date}" if s.payment_due_date else "Due Date: —"
        )

        if s.statement_type == 'payslip':
            self.payslip_label.setText(
                f"Gross: ${s.gross_pay:,.2f}  |  Net: ${s.net_pay:,.2f}"
            )
        else:
            self.payslip_label.setText("")

    def _auto_match_account(self):
        """Try to auto-match the statement to an account"""
        if not self._statement:
            return

        cards = CreditCard.get_all()
        accounts = Account.get_all()
        code = match_account(self._statement, cards, accounts)

        if code:
            # Find and select in combo
            for i in range(self.account_combo.count()):
                if self.account_combo.itemData(i) == code:
                    self.account_combo.setCurrentIndex(i)
                    self.auto_match_label.setText("(auto-matched)")
                    return

        self.auto_match_label.setText("(no match found)")

    def _populate_table(self):
        """Populate the transactions table"""
        if not self._statement:
            self.table.setRowCount(0)
            return

        txns = self._statement.transactions
        self.table.setRowCount(len(txns))

        for row, txn in enumerate(txns):
            # Date
            self.table.setItem(row, 0, QTableWidgetItem(txn.date))

            # Post Date
            self.table.setItem(
                row, 1, QTableWidgetItem(txn.post_date or "")
            )

            # Description
            self.table.setItem(row, 2, QTableWidgetItem(txn.description))

            # Amount
            amount_item = QTableWidgetItem(f"${txn.amount:,.2f}")
            if txn.amount < 0:
                amount_item.setForeground(QColor("#f44336"))
            else:
                amount_item.setForeground(QColor("#4caf50"))
            self.table.setItem(row, 3, amount_item)

            # Category
            self.table.setItem(row, 4, QTableWidgetItem(txn.category))

        self.status_label.setText(f"{len(txns)} transaction(s) found")

    def _import_transactions(self):
        """Import parsed transactions into the database"""
        if not self._statement or not self._statement.transactions:
            return

        pay_code = self.account_combo.currentData()
        if not pay_code:
            QMessageBox.warning(
                self, "No Account Selected",
                "Please select an account to import transactions to."
            )
            return

        # Confirm import
        count = len(self._statement.transactions)
        reply = QMessageBox.question(
            self, "Confirm Import",
            f"Import {count} transaction(s) to "
            f"{self.account_combo.currentText()}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        is_posted = self.mark_posted_check.isChecked()
        imported = 0

        for txn in self._statement.transactions:
            t = Transaction(
                id=None,
                date=txn.date,
                description=txn.description,
                amount=txn.amount,
                payment_method=pay_code,
                is_posted=is_posted,
                posted_date=txn.post_date or txn.date if is_posted else None,
                notes=f"Imported from {self._statement.institution} statement"
            )
            t.save()
            imported += 1

        # Update account/card balance if requested
        if self.update_balance_check.isChecked() and self._statement.new_balance > 0:
            self._update_account_balance(pay_code)

        QMessageBox.information(
            self, "Import Complete",
            f"Successfully imported {imported} transaction(s)."
        )

        self.status_label.setText(f"Imported {imported} transaction(s)")
        self.import_btn.setEnabled(False)

    def _update_account_balance(self, pay_code: str):
        """Update account or card balance from statement"""
        s = self._statement

        # Try credit card first
        card = CreditCard.get_by_code(pay_code)
        if card:
            card.current_balance = s.new_balance
            card.save()
            return

        # Try account
        acct = Account.get_by_code(pay_code)
        if acct:
            acct.current_balance = s.new_balance
            acct.save()

    def _clear(self):
        """Clear the current import"""
        self._statement = None
        self.file_label.setText("No file selected")
        self.file_label.setStyleSheet("color: #888;")
        self.institution_label.setText("Institution: —")
        self.type_label.setText("Type: —")
        self.last4_label.setText("Account: —")
        self.period_label.setText("Period: —")
        self.prev_balance_label.setText("Prev Balance: —")
        self.new_balance_label.setText("New Balance: —")
        self.limit_label.setText("Credit Limit: —")
        self.interest_label.setText("Interest: —")
        self.fees_label.setText("Fees: —")
        self.min_payment_label.setText("Min Payment: —")
        self.due_date_label.setText("Due Date: —")
        self.payslip_label.setText("")
        self.auto_match_label.setText("")
        self.account_combo.clear()
        self.table.setRowCount(0)
        self.import_btn.setEnabled(False)
        self.status_label.setText("")

    def refresh(self):
        """Refresh - no-op, import is user-driven"""
        pass
