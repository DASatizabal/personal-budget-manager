"""Credit Cards management view"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QFormLayout, QLineEdit,
    QComboBox, QHeaderView, QMessageBox, QLabel
)
from .widgets import NoScrollDoubleSpinBox, NoScrollSpinBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ..models.credit_card import CreditCard


class CreditCardsView(QWidget):
    """View for managing credit cards"""

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        """Set up the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Toolbar
        toolbar = QHBoxLayout()

        add_btn = QPushButton("Add Card")
        add_btn.clicked.connect(self._add_card)
        toolbar.addWidget(add_btn)

        edit_btn = QPushButton("Edit Selected")
        edit_btn.clicked.connect(self._edit_card)
        toolbar.addWidget(edit_btn)

        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self._delete_card)
        toolbar.addWidget(delete_btn)

        toolbar.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Code", "Name", "Balance", "Limit", "Available",
            "Utilization", "Min Payment", "Interest Rate", "Due Day"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_card)
        layout.addWidget(self.table)

        # Summary
        summary_layout = QHBoxLayout()
        self.total_balance_label = QLabel()
        self.total_limit_label = QLabel()
        self.total_util_label = QLabel()
        summary_layout.addWidget(self.total_balance_label)
        summary_layout.addWidget(self.total_limit_label)
        summary_layout.addWidget(self.total_util_label)
        summary_layout.addStretch()
        layout.addLayout(summary_layout)

    def refresh(self):
        """Refresh the table data"""
        cards = CreditCard.get_all()
        self.table.setRowCount(len(cards))

        for row, card in enumerate(cards):
            self.table.setItem(row, 0, QTableWidgetItem(card.pay_type_code))
            self.table.setItem(row, 1, QTableWidgetItem(card.name))

            balance_item = QTableWidgetItem(f"${card.current_balance:,.2f}")
            if card.current_balance > card.credit_limit:
                balance_item.setForeground(QColor("#f44336"))
            self.table.setItem(row, 2, balance_item)

            self.table.setItem(row, 3, QTableWidgetItem(f"${card.credit_limit:,.2f}"))

            available_item = QTableWidgetItem(f"${card.available_credit:,.2f}")
            if card.available_credit < 0:
                available_item.setForeground(QColor("#f44336"))
            self.table.setItem(row, 4, available_item)

            util_pct = card.utilization * 100
            util_item = QTableWidgetItem(f"{util_pct:.1f}%")
            if util_pct > 80:
                util_item.setForeground(QColor("#f44336"))
            elif util_pct > 50:
                util_item.setForeground(QColor("#ff9800"))
            self.table.setItem(row, 5, util_item)

            self.table.setItem(row, 6, QTableWidgetItem(f"${card.min_payment:,.2f}"))
            self.table.setItem(row, 7, QTableWidgetItem(f"{card.interest_rate * 100:.2f}%"))
            self.table.setItem(row, 8, QTableWidgetItem(str(card.due_day or "-")))

            # Store the card id in the first column
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, card.id)

        # Update summary
        total_balance = CreditCard.get_total_balance()
        total_limit = CreditCard.get_total_credit_limit()
        total_util = CreditCard.get_total_utilization() * 100

        self.total_balance_label.setText(f"Total Balance: ${total_balance:,.2f}")
        self.total_limit_label.setText(f"Total Limit: ${total_limit:,.2f}")
        self.total_util_label.setText(f"Overall Utilization: {total_util:.1f}%")

    def _get_selected_card_id(self) -> int:
        """Get the ID of the selected card"""
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def _add_card(self):
        """Add a new credit card"""
        dialog = CreditCardDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            card = dialog.get_card()
            card.save()
            self.refresh()

    def _edit_card(self):
        """Edit the selected credit card"""
        card_id = self._get_selected_card_id()
        if not card_id:
            QMessageBox.warning(self, "Warning", "Please select a card to edit")
            return

        card = CreditCard.get_by_id(card_id)
        if card:
            dialog = CreditCardDialog(self, card)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                updated = dialog.get_card()
                updated.id = card.id
                updated.save()
                self.refresh()

    def _delete_card(self):
        """Delete the selected credit card with reassignment options"""
        card_id = self._get_selected_card_id()
        if not card_id:
            QMessageBox.warning(self, "Warning", "Please select a card to delete")
            return

        card = CreditCard.get_by_id(card_id)
        if not card:
            return

        # Check for linked data
        from ..models.database import Database
        db = Database()

        linked_charges = db.execute(
            "SELECT id, name FROM recurring_charges WHERE linked_card_id = ?",
            (card_id,)
        ).fetchall()

        transactions = db.execute(
            "SELECT id, date, description, amount FROM transactions WHERE payment_method = ?",
            (card.pay_type_code,)
        ).fetchall()

        # If no linked data, simple deletion
        if not linked_charges and not transactions:
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Are you sure you want to delete '{card.name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                card.delete()
                self.refresh()
            return

        # Show deletion dialog with reassignment options
        dialog = CardDeletionDialog(self, card, linked_charges, transactions)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            target_card_id = dialog.get_target_card_id()
            delete_transactions = dialog.get_delete_transactions()

            # Reassign or unlink recurring charges
            if target_card_id:
                db.execute(
                    "UPDATE recurring_charges SET linked_card_id = ? WHERE linked_card_id = ?",
                    (target_card_id, card_id)
                )
            else:
                db.execute(
                    "UPDATE recurring_charges SET linked_card_id = NULL WHERE linked_card_id = ?",
                    (card_id,)
                )

            # Handle transactions
            if delete_transactions:
                db.execute(
                    "DELETE FROM transactions WHERE payment_method = ?",
                    (card.pay_type_code,)
                )
            elif target_card_id:
                # Transfer to target card
                target_card = CreditCard.get_by_id(target_card_id)
                if target_card:
                    db.execute(
                        "UPDATE transactions SET payment_method = ? WHERE payment_method = ?",
                        (target_card.pay_type_code, card.pay_type_code)
                    )

            db.commit()
            card.delete()
            self.refresh()
            QMessageBox.information(self, "Deleted", f"'{card.name}' has been deleted.")


class CreditCardDialog(QDialog):
    """Dialog for adding/editing a credit card"""

    def __init__(self, parent=None, card: CreditCard = None):
        super().__init__(parent)
        self.card = card
        self.setWindowTitle("Edit Credit Card" if card else "Add Credit Card")
        self.setMinimumWidth(400)
        self._setup_ui()
        if card:
            self._populate_fields()

    def _setup_ui(self):
        """Set up the dialog UI"""
        layout = QFormLayout(self)

        self.code_edit = QLineEdit()
        self.code_edit.setMaxLength(3)
        layout.addRow("Pay Type Code:", self.code_edit)

        self.name_edit = QLineEdit()
        layout.addRow("Card Name:", self.name_edit)

        self.limit_spin = NoScrollDoubleSpinBox()
        self.limit_spin.setRange(0, 1000000)
        self.limit_spin.setDecimals(2)
        self.limit_spin.setPrefix("$")
        layout.addRow("Credit Limit:", self.limit_spin)

        self.balance_spin = NoScrollDoubleSpinBox()
        self.balance_spin.setRange(0, 1000000)
        self.balance_spin.setDecimals(2)
        self.balance_spin.setPrefix("$")
        layout.addRow("Current Balance:", self.balance_spin)

        self.rate_spin = NoScrollDoubleSpinBox()
        self.rate_spin.setRange(0, 100)
        self.rate_spin.setDecimals(2)
        self.rate_spin.setSuffix("%")
        layout.addRow("Interest Rate:", self.rate_spin)

        self.due_day_spin = NoScrollSpinBox()
        self.due_day_spin.setRange(1, 31)
        layout.addRow("Due Day:", self.due_day_spin)

        self.min_type_combo = QComboBox()
        self.min_type_combo.addItems(["Calculated", "Fixed Amount", "Full Balance"])
        self.min_type_combo.currentIndexChanged.connect(self._on_min_type_changed)
        layout.addRow("Min Payment Type:", self.min_type_combo)

        self.min_amount_spin = NoScrollDoubleSpinBox()
        self.min_amount_spin.setRange(0, 100000)
        self.min_amount_spin.setDecimals(2)
        self.min_amount_spin.setPrefix("$")
        self.min_amount_spin.setEnabled(False)
        layout.addRow("Min Payment Amount:", self.min_amount_spin)

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

        code = self.code_edit.text().strip()
        if not code:
            errors.append("Pay Type Code is required.")
        elif len(code) > 3:
            errors.append("Pay Type Code must be 3 characters or less.")

        name = self.name_edit.text().strip()
        if not name:
            errors.append("Card Name is required.")

        if self.limit_spin.value() <= 0:
            errors.append("Credit Limit must be greater than 0.")

        # Check for duplicate pay type code (only for new cards or changed codes)
        if code:
            existing = CreditCard.get_by_code(code)
            if existing and (not self.card or existing.id != self.card.id):
                errors.append(f"Pay Type Code '{code}' is already in use.")

        if errors:
            QMessageBox.warning(self, "Validation Error", "\n".join(errors))
            return

        self.accept()

    def _on_min_type_changed(self, index: int):
        """Handle min payment type change"""
        self.min_amount_spin.setEnabled(index == 1)  # Fixed Amount

    def _populate_fields(self):
        """Populate fields with existing card data"""
        self.code_edit.setText(self.card.pay_type_code)
        self.name_edit.setText(self.card.name)
        self.limit_spin.setValue(self.card.credit_limit)
        self.balance_spin.setValue(self.card.current_balance)
        self.rate_spin.setValue(self.card.interest_rate * 100)
        self.due_day_spin.setValue(self.card.due_day or 1)

        type_map = {'CALCULATED': 0, 'FIXED': 1, 'FULL_BALANCE': 2}
        self.min_type_combo.setCurrentIndex(type_map.get(self.card.min_payment_type, 0))

        if self.card.min_payment_amount:
            self.min_amount_spin.setValue(self.card.min_payment_amount)

    def get_card(self) -> CreditCard:
        """Get the card from the form values"""
        type_map = {0: 'CALCULATED', 1: 'FIXED', 2: 'FULL_BALANCE'}
        min_type = type_map[self.min_type_combo.currentIndex()]

        return CreditCard(
            id=None,
            pay_type_code=self.code_edit.text().strip().upper(),
            name=self.name_edit.text().strip(),
            credit_limit=self.limit_spin.value(),
            current_balance=self.balance_spin.value(),
            interest_rate=self.rate_spin.value() / 100,
            due_day=self.due_day_spin.value(),
            min_payment_type=min_type,
            min_payment_amount=self.min_amount_spin.value() if min_type == 'FIXED' else None
        )


class CardDeletionDialog(QDialog):
    """Dialog for handling credit card deletion with data reassignment"""

    def __init__(self, parent, card: CreditCard, linked_charges: list, transactions: list):
        super().__init__(parent)
        self.card = card
        self.linked_charges = linked_charges
        self.transactions = transactions
        self.setWindowTitle(f"Delete {card.name}")
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self):
        from PyQt6.QtWidgets import QVBoxLayout, QGroupBox, QRadioButton, QButtonGroup

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Warning header
        warning = QLabel(f"<b>Deleting '{self.card.name}' ({self.card.pay_type_code})</b>")
        layout.addWidget(warning)

        # Linked charges section
        if self.linked_charges:
            charges_group = QGroupBox(f"Linked Recurring Charges ({len(self.linked_charges)})")
            charges_layout = QVBoxLayout(charges_group)

            charge_names = ", ".join([c['name'] for c in self.linked_charges[:5]])
            if len(self.linked_charges) > 5:
                charge_names += f" and {len(self.linked_charges) - 5} more..."
            charges_layout.addWidget(QLabel(charge_names))

            charges_layout.addWidget(QLabel("Reassign these charges to:"))
            self.charges_combo = QComboBox()
            self.charges_combo.addItem("(Unlink - no card)", None)
            for card in CreditCard.get_all():
                if card.id != self.card.id:
                    self.charges_combo.addItem(card.name, card.id)
            charges_layout.addWidget(self.charges_combo)

            layout.addWidget(charges_group)

        # Transactions section
        if self.transactions:
            trans_group = QGroupBox(f"Transactions ({len(self.transactions)})")
            trans_layout = QVBoxLayout(trans_group)

            trans_layout.addWidget(QLabel(f"Found {len(self.transactions)} transaction(s) using this card."))

            self.trans_button_group = QButtonGroup(self)
            self.trans_transfer_radio = QRadioButton("Transfer to another card")
            self.trans_delete_radio = QRadioButton("Delete all transactions")
            self.trans_keep_radio = QRadioButton("Keep transactions (payment method will be invalid)")

            self.trans_button_group.addButton(self.trans_transfer_radio, 0)
            self.trans_button_group.addButton(self.trans_delete_radio, 1)
            self.trans_button_group.addButton(self.trans_keep_radio, 2)
            self.trans_transfer_radio.setChecked(True)

            trans_layout.addWidget(self.trans_transfer_radio)

            self.trans_target_combo = QComboBox()
            for card in CreditCard.get_all():
                if card.id != self.card.id:
                    self.trans_target_combo.addItem(card.name, card.id)
            trans_layout.addWidget(self.trans_target_combo)

            trans_layout.addWidget(self.trans_delete_radio)
            trans_layout.addWidget(self.trans_keep_radio)

            # Connect radio buttons to enable/disable combo
            self.trans_transfer_radio.toggled.connect(
                lambda checked: self.trans_target_combo.setEnabled(checked)
            )

            layout.addWidget(trans_group)

        # Buttons
        btn_layout = QHBoxLayout()
        delete_btn = QPushButton("Delete Card")
        delete_btn.setStyleSheet("background-color: #f44336; color: white;")
        delete_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(delete_btn)
        layout.addLayout(btn_layout)

    def get_target_card_id(self) -> int:
        """Get the target card ID for charge reassignment"""
        if hasattr(self, 'charges_combo'):
            return self.charges_combo.currentData()
        return None

    def get_delete_transactions(self) -> bool:
        """Return True if transactions should be deleted"""
        if hasattr(self, 'trans_delete_radio'):
            return self.trans_delete_radio.isChecked()
        return False

    def get_transaction_target_id(self) -> int:
        """Get target card ID for transaction transfer"""
        if hasattr(self, 'trans_transfer_radio') and self.trans_transfer_radio.isChecked():
            return self.trans_target_combo.currentData()
        return None
