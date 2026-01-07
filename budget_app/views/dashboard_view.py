"""Dashboard view showing summary of finances"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QProgressBar, QPushButton,
    QDialog, QFormLayout, QMessageBox, QLineEdit
)
from .widgets import NoScrollDoubleSpinBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from datetime import datetime, timedelta

from ..models.account import Account
from ..models.credit_card import CreditCard
from ..models.loan import Loan
from ..models.transaction import Transaction
from ..utils.calculations import calculate_90_day_minimum, get_starting_balances


class DashboardView(QWidget):
    """Dashboard with financial summary"""

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        """Set up the dashboard UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Toolbar
        toolbar = QHBoxLayout()

        update_balances_btn = QPushButton("Update Balances")
        update_balances_btn.setToolTip("Manually update account and credit card balances")
        update_balances_btn.clicked.connect(self._show_update_balances_dialog)
        toolbar.addWidget(update_balances_btn)

        toolbar.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        # Top section: Account balances and alerts
        top_layout = QHBoxLayout()

        # Account balances card
        self.accounts_group = QGroupBox("Account Balances (Click to Edit)")
        accounts_layout = QVBoxLayout(self.accounts_group)
        self.accounts_layout = accounts_layout
        top_layout.addWidget(self.accounts_group, 1)

        # 90-day alert card
        self.alert_group = QGroupBox("90-Day Minimum Balance Alert")
        alert_layout = QVBoxLayout(self.alert_group)
        self.min_balance_label = QLabel()
        self.min_balance_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.min_date_label = QLabel()
        self.min_date_label.setFont(QFont("Segoe UI", 12))
        alert_layout.addWidget(self.min_balance_label)
        alert_layout.addWidget(self.min_date_label)
        alert_layout.addStretch()
        top_layout.addWidget(self.alert_group, 1)

        layout.addLayout(top_layout)

        # Credit utilization section
        util_group = QGroupBox("Credit Utilization")
        util_layout = QVBoxLayout(util_group)

        self.total_util_bar = QProgressBar()
        self.total_util_bar.setTextVisible(True)
        self.total_util_bar.setMinimum(0)
        self.total_util_bar.setMaximum(100)
        self.total_util_label = QLabel()
        util_layout.addWidget(QLabel("Overall Credit Utilization:"))
        util_layout.addWidget(self.total_util_bar)
        util_layout.addWidget(self.total_util_label)

        layout.addWidget(util_group)

        # Credit cards table
        cards_group = QGroupBox("Credit Cards Summary (Double-click to Edit Balance)")
        cards_layout = QVBoxLayout(cards_group)

        self.cards_table = QTableWidget()
        self.cards_table.setColumnCount(8)
        self.cards_table.setHorizontalHeaderLabels([
            "Card", "Balance", "Limit", "Available", "Utilization",
            "Min Payment", "Interest Rate", "Due Day"
        ])
        self.cards_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.cards_table.setAlternatingRowColors(True)
        self.cards_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cards_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.cards_table.doubleClicked.connect(self._edit_card_balance)
        cards_layout.addWidget(self.cards_table)

        layout.addWidget(cards_group, 1)

        # Loans section
        loans_group = QGroupBox("Loans (Double-click to Edit Balance)")
        loans_layout = QVBoxLayout(loans_group)

        self.loans_table = QTableWidget()
        self.loans_table.setColumnCount(5)
        self.loans_table.setHorizontalHeaderLabels([
            "Loan", "Balance", "Original Amount", "Payment", "Interest Rate"
        ])
        self.loans_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.loans_table.setAlternatingRowColors(True)
        self.loans_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.loans_table.doubleClicked.connect(self._edit_loan_balance)
        loans_layout.addWidget(self.loans_table)

        layout.addWidget(loans_group)

    def refresh(self):
        """Refresh all dashboard data"""
        self._update_accounts()
        self._update_90_day_alert()
        self._update_credit_cards()
        self._update_loans()
        self._update_utilization()

    def _update_accounts(self):
        """Update account balances display"""
        # Clear existing widgets
        while self.accounts_layout.count():
            item = self.accounts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        accounts = Account.get_all()

        for account in accounts:
            row = QHBoxLayout()
            name_label = QLabel(f"{account.name}:")
            name_label.setFont(QFont("Segoe UI", 12))

            balance_btn = QPushButton(f"${account.current_balance:,.2f}")
            balance_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            balance_btn.setFlat(True)
            balance_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            balance_btn.setToolTip("Click to edit balance")
            balance_btn.clicked.connect(lambda checked, a=account: self._edit_account_balance(a))

            if account.current_balance < 0:
                balance_btn.setStyleSheet("color: #f44336; text-align: right;")
            elif account.current_balance > 1000:
                balance_btn.setStyleSheet("color: #4caf50; text-align: right;")
            else:
                balance_btn.setStyleSheet("text-align: right;")

            row.addWidget(name_label)
            row.addStretch()
            row.addWidget(balance_btn)

            container = QWidget()
            container.setLayout(row)
            self.accounts_layout.addWidget(container)

        self.accounts_layout.addStretch()

    def _edit_account_balance(self, account: Account):
        """Edit an account balance"""
        dialog = EditBalanceDialog(self, account.name, account.current_balance)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            account.current_balance = dialog.get_balance()
            account.save()
            self.refresh()

    def _edit_card_balance(self):
        """Edit credit card balance from table double-click"""
        selected = self.cards_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        card_id = self.cards_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        card = CreditCard.get_by_id(card_id)

        if card:
            dialog = EditBalanceDialog(self, card.name, card.current_balance, is_credit_card=True)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                card.current_balance = dialog.get_balance()
                card.save()
                self.refresh()

    def _edit_loan_balance(self):
        """Edit loan balance from table double-click"""
        selected = self.loans_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        loan_id = self.loans_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        loan = Loan.get_by_id(loan_id)

        if loan:
            dialog = EditBalanceDialog(self, loan.name, loan.current_balance)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                loan.current_balance = dialog.get_balance()
                loan.save()
                self.refresh()

    def _show_update_balances_dialog(self):
        """Show dialog to update all balances at once"""
        dialog = UpdateAllBalancesDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _update_90_day_alert(self):
        """Update 90-day minimum balance alert"""
        checking = Account.get_checking_account()
        if not checking:
            self.min_balance_label.setText("N/A")
            self.min_date_label.setText("No checking account found")
            return

        transactions = Transaction.get_future_transactions()
        min_balance, min_date = calculate_90_day_minimum(
            checking.current_balance,
            transactions,
            payment_method='C'
        )

        self.min_balance_label.setText(f"${min_balance:,.2f}")

        # Format date as MM/DD/YYYY for display
        date_str = min_date.strftime("%m/%d/%Y") if min_date else None

        if min_balance < 0:
            self.min_balance_label.setStyleSheet("color: #f44336;")
            self.min_date_label.setText(f"WARNING: Negative balance on {date_str}")
            self.min_date_label.setStyleSheet("color: #f44336;")
        elif min_balance < 500:
            self.min_balance_label.setStyleSheet("color: #ff9800;")
            self.min_date_label.setText(f"Low balance expected on {date_str}")
            self.min_date_label.setStyleSheet("color: #ff9800;")
        else:
            self.min_balance_label.setStyleSheet("color: #4caf50;")
            if date_str:
                self.min_date_label.setText(f"Minimum occurs on {date_str}")
            else:
                self.min_date_label.setText("Balance stays stable")
            self.min_date_label.setStyleSheet("color: #d4d4d4;")

    def _update_credit_cards(self):
        """Update credit cards table"""
        cards = CreditCard.get_all()
        self.cards_table.setRowCount(len(cards))

        for row, card in enumerate(cards):
            name_item = QTableWidgetItem(card.name)
            name_item.setData(Qt.ItemDataRole.UserRole, card.id)
            self.cards_table.setItem(row, 0, name_item)

            self.cards_table.setItem(row, 1, QTableWidgetItem(f"${card.current_balance:,.2f}"))
            self.cards_table.setItem(row, 2, QTableWidgetItem(f"${card.credit_limit:,.2f}"))
            self.cards_table.setItem(row, 3, QTableWidgetItem(f"${card.available_credit:,.2f}"))

            util_pct = card.utilization * 100
            util_item = QTableWidgetItem(f"{util_pct:.1f}%")
            if util_pct > 80:
                util_item.setForeground(QColor("#f44336"))
            elif util_pct > 50:
                util_item.setForeground(QColor("#ff9800"))
            elif util_pct > 30:
                util_item.setForeground(QColor("#ffeb3b"))
            else:
                util_item.setForeground(QColor("#4caf50"))
            self.cards_table.setItem(row, 4, util_item)

            self.cards_table.setItem(row, 5, QTableWidgetItem(f"${card.min_payment:,.2f}"))
            self.cards_table.setItem(row, 6, QTableWidgetItem(f"{card.interest_rate * 100:.2f}%"))
            self.cards_table.setItem(row, 7, QTableWidgetItem(str(card.due_day or "-")))

    def _update_loans(self):
        """Update loans table"""
        loans = Loan.get_all()
        self.loans_table.setRowCount(len(loans))

        for row, loan in enumerate(loans):
            name_item = QTableWidgetItem(loan.name)
            name_item.setData(Qt.ItemDataRole.UserRole, loan.id)
            self.loans_table.setItem(row, 0, name_item)

            self.loans_table.setItem(row, 1, QTableWidgetItem(f"${loan.current_balance:,.2f}"))
            self.loans_table.setItem(row, 2, QTableWidgetItem(f"${loan.original_amount:,.2f}"))
            self.loans_table.setItem(row, 3, QTableWidgetItem(f"${loan.payment_amount:,.2f}"))
            self.loans_table.setItem(row, 4, QTableWidgetItem(f"{loan.interest_rate * 100:.2f}%"))

    def _update_utilization(self):
        """Update credit utilization display"""
        total_balance = CreditCard.get_total_balance()
        total_limit = CreditCard.get_total_credit_limit()

        if total_limit > 0:
            utilization = (total_balance / total_limit) * 100
        else:
            utilization = 0

        self.total_util_bar.setValue(int(utilization))
        self.total_util_label.setText(
            f"${total_balance:,.2f} of ${total_limit:,.2f} used ({utilization:.1f}%)"
        )

        # Color the progress bar based on utilization
        if utilization > 80:
            color = "#f44336"
        elif utilization > 50:
            color = "#ff9800"
        elif utilization > 30:
            color = "#ffeb3b"
        else:
            color = "#4caf50"

        self.total_util_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                text-align: center;
                background-color: #2d2d2d;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)


class EditBalanceDialog(QDialog):
    """Dialog for editing a single balance"""

    def __init__(self, parent=None, name: str = "", current_balance: float = 0,
                 is_credit_card: bool = False):
        super().__init__(parent)
        self.setWindowTitle(f"Edit {name} Balance")
        self.setMinimumWidth(300)
        self.is_credit_card = is_credit_card
        self._setup_ui(name, current_balance)

    def _setup_ui(self, name: str, current_balance: float):
        layout = QFormLayout(self)

        layout.addRow(QLabel(f"Editing: {name}"))

        self.balance_spin = NoScrollDoubleSpinBox()
        self.balance_spin.setRange(-1000000, 1000000)
        self.balance_spin.setDecimals(2)
        self.balance_spin.setPrefix("$")
        self.balance_spin.setValue(current_balance)

        if self.is_credit_card:
            layout.addRow("Current Balance (amount owed):", self.balance_spin)
        else:
            layout.addRow("Current Balance:", self.balance_spin)

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

    def get_balance(self) -> float:
        return self.balance_spin.value()


class UpdateAllBalancesDialog(QDialog):
    """Dialog for updating all balances at once"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update All Balances")
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Instructions
        info = QLabel(
            "Update your current balances below. These should match your actual "
            "bank/credit card statements."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Accounts section
        accounts_group = QGroupBox("Bank Accounts")
        accounts_layout = QFormLayout(accounts_group)

        self.account_spins = {}
        for account in Account.get_all():
            spin = NoScrollDoubleSpinBox()
            spin.setRange(-1000000, 1000000)
            spin.setDecimals(2)
            spin.setValue(account.current_balance)
            # Create row with $ label
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(QLabel("$"))
            row_layout.addWidget(spin)
            accounts_layout.addRow(f"{account.name}:", row_widget)
            self.account_spins[account.id] = spin

        layout.addWidget(accounts_group)

        # Credit Cards section
        cards_group = QGroupBox("Credit Cards (Enter amount OWED)")
        cards_layout = QFormLayout(cards_group)

        self.card_spins = {}
        for card in CreditCard.get_all():
            spin = NoScrollDoubleSpinBox()
            spin.setRange(0, 1000000)
            spin.setDecimals(2)
            spin.setValue(card.current_balance)
            # Create row with $ label
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(QLabel("$"))
            row_layout.addWidget(spin)
            cards_layout.addRow(f"{card.name}:", row_widget)
            self.card_spins[card.id] = spin

        layout.addWidget(cards_group)

        # Loans section
        loans = Loan.get_all()
        if loans:
            loans_group = QGroupBox("Loans (Enter remaining balance)")
            loans_layout = QFormLayout(loans_group)

            self.loan_spins = {}
            for loan in loans:
                spin = NoScrollDoubleSpinBox()
                spin.setRange(0, 1000000)
                spin.setDecimals(2)
                spin.setValue(loan.current_balance)
                # Create row with $ label
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.addWidget(QLabel("$"))
                row_layout.addWidget(spin)
                loans_layout.addRow(f"{loan.name}:", row_widget)
                self.loan_spins[loan.id] = spin

            layout.addWidget(loans_group)
        else:
            self.loan_spins = {}

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save All")
        save_btn.clicked.connect(self._save_all)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _save_all(self):
        """Save all balance updates"""
        # Update accounts
        for account_id, spin in self.account_spins.items():
            account = Account.get_by_id(account_id)
            if account:
                account.current_balance = spin.value()
                account.save()

        # Update credit cards
        for card_id, spin in self.card_spins.items():
            card = CreditCard.get_by_id(card_id)
            if card:
                card.current_balance = spin.value()
                card.save()

        # Update loans
        for loan_id, spin in self.loan_spins.items():
            loan = Loan.get_by_id(loan_id)
            if loan:
                loan.current_balance = spin.value()
                loan.save()

        QMessageBox.information(self, "Saved", "All balances have been updated!")
        self.accept()
