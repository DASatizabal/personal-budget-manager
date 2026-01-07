"""Credit Cards management view"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QSpinBox, QComboBox, QHeaderView, QMessageBox, QLabel
)
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
        """Delete the selected credit card"""
        card_id = self._get_selected_card_id()
        if not card_id:
            QMessageBox.warning(self, "Warning", "Please select a card to delete")
            return

        card = CreditCard.get_by_id(card_id)
        if card:
            # Check for linked recurring charges
            from ..models.database import Database
            db = Database()
            linked_count = db.execute(
                "SELECT COUNT(*) FROM recurring_charges WHERE linked_card_id = ?",
                (card_id,)
            ).fetchone()[0]

            if linked_count > 0:
                msg = (f"Are you sure you want to delete '{card.name}'?\n\n"
                       f"Warning: {linked_count} recurring charge(s) are linked to this card "
                       f"and will be unlinked.")
            else:
                msg = f"Are you sure you want to delete '{card.name}'?"

            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                card.delete()
                self.refresh()


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

        self.limit_spin = QDoubleSpinBox()
        self.limit_spin.setRange(0, 1000000)
        self.limit_spin.setDecimals(2)
        self.limit_spin.setPrefix("$")
        layout.addRow("Credit Limit:", self.limit_spin)

        self.balance_spin = QDoubleSpinBox()
        self.balance_spin.setRange(0, 1000000)
        self.balance_spin.setDecimals(2)
        self.balance_spin.setPrefix("$")
        layout.addRow("Current Balance:", self.balance_spin)

        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(0, 100)
        self.rate_spin.setDecimals(2)
        self.rate_spin.setSuffix("%")
        layout.addRow("Interest Rate:", self.rate_spin)

        self.due_day_spin = QSpinBox()
        self.due_day_spin.setRange(1, 31)
        layout.addRow("Due Day:", self.due_day_spin)

        self.min_type_combo = QComboBox()
        self.min_type_combo.addItems(["Calculated", "Fixed Amount", "Full Balance"])
        self.min_type_combo.currentIndexChanged.connect(self._on_min_type_changed)
        layout.addRow("Min Payment Type:", self.min_type_combo)

        self.min_amount_spin = QDoubleSpinBox()
        self.min_amount_spin.setRange(0, 100000)
        self.min_amount_spin.setDecimals(2)
        self.min_amount_spin.setPrefix("$")
        self.min_amount_spin.setEnabled(False)
        layout.addRow("Min Payment Amount:", self.min_amount_spin)

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
