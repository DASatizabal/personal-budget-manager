"""Recurring Charges management view"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QSpinBox, QComboBox, QHeaderView, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ..models.recurring_charge import RecurringCharge
from ..models.credit_card import CreditCard


class RecurringChargesView(QWidget):
    """View for managing recurring charges"""

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

        add_btn = QPushButton("Add Charge")
        add_btn.clicked.connect(self._add_charge)
        toolbar.addWidget(add_btn)

        edit_btn = QPushButton("Edit Selected")
        edit_btn.clicked.connect(self._edit_charge)
        toolbar.addWidget(edit_btn)

        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self._delete_charge)
        toolbar.addWidget(delete_btn)

        toolbar.addStretch()

        self.show_inactive = QCheckBox("Show Inactive")
        self.show_inactive.stateChanged.connect(self.refresh)
        toolbar.addWidget(self.show_inactive)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Name", "Amount", "Day", "Payment Method", "Frequency", "Type", "Active"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_charge)
        layout.addWidget(self.table)

    def refresh(self):
        """Refresh the table data"""
        active_only = not self.show_inactive.isChecked()
        charges = RecurringCharge.get_all(active_only=active_only)
        self.table.setRowCount(len(charges))

        # Get payment method names
        cards = {c.pay_type_code: c.name for c in CreditCard.get_all()}
        cards['C'] = 'Chase (Bank)'

        for row, charge in enumerate(charges):
            name_item = QTableWidgetItem(charge.name)
            name_item.setData(Qt.ItemDataRole.UserRole, charge.id)
            self.table.setItem(row, 0, name_item)

            amount_item = QTableWidgetItem(f"${charge.amount:,.2f}")
            if charge.amount < 0:
                amount_item.setForeground(QColor("#f44336"))
            else:
                amount_item.setForeground(QColor("#4caf50"))
            self.table.setItem(row, 1, amount_item)

            # Day display
            day = charge.day_of_month
            if day >= 991:
                day_text = f"Special ({day})"
            else:
                day_text = str(day)
            self.table.setItem(row, 2, QTableWidgetItem(day_text))

            method_name = cards.get(charge.payment_method, charge.payment_method)
            self.table.setItem(row, 3, QTableWidgetItem(method_name))

            self.table.setItem(row, 4, QTableWidgetItem(charge.frequency))
            self.table.setItem(row, 5, QTableWidgetItem(charge.amount_type))

            active_item = QTableWidgetItem("Yes" if charge.is_active else "No")
            if not charge.is_active:
                active_item.setForeground(QColor("#808080"))
            self.table.setItem(row, 6, active_item)

    def _get_selected_charge_id(self) -> int:
        """Get the ID of the selected charge"""
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def _add_charge(self):
        """Add a new recurring charge"""
        dialog = RecurringChargeDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            charge = dialog.get_charge()
            charge.save()
            self.refresh()

    def _edit_charge(self):
        """Edit the selected recurring charge"""
        charge_id = self._get_selected_charge_id()
        if not charge_id:
            QMessageBox.warning(self, "Warning", "Please select a charge to edit")
            return

        charge = RecurringCharge.get_by_id(charge_id)
        if charge:
            dialog = RecurringChargeDialog(self, charge)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                updated = dialog.get_charge()
                updated.id = charge.id
                updated.save()
                self.refresh()

    def _delete_charge(self):
        """Delete the selected recurring charge"""
        charge_id = self._get_selected_charge_id()
        if not charge_id:
            QMessageBox.warning(self, "Warning", "Please select a charge to delete")
            return

        charge = RecurringCharge.get_by_id(charge_id)
        if charge:
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Are you sure you want to delete '{charge.name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                charge.delete()
                self.refresh()


class RecurringChargeDialog(QDialog):
    """Dialog for adding/editing a recurring charge"""

    def __init__(self, parent=None, charge: RecurringCharge = None):
        super().__init__(parent)
        self.charge = charge
        self.setWindowTitle("Edit Recurring Charge" if charge else "Add Recurring Charge")
        self.setMinimumWidth(400)
        self._setup_ui()
        if charge:
            self._populate_fields()

    def _setup_ui(self):
        """Set up the dialog UI"""
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        layout.addRow("Name:", self.name_edit)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(-1000000, 1000000)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setPrefix("$")
        layout.addRow("Amount (negative = expense):", self.amount_spin)

        self.day_spin = QSpinBox()
        self.day_spin.setRange(1, 999)
        self.day_spin.setSpecialValueText("1")
        layout.addRow("Day of Month (991-999 = special):", self.day_spin)

        self.method_combo = QComboBox()
        self._load_payment_methods()
        layout.addRow("Payment Method:", self.method_combo)

        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems(["MONTHLY", "BIWEEKLY", "WEEKLY", "YEARLY", "SPECIAL"])
        layout.addRow("Frequency:", self.frequency_combo)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["FIXED", "CREDIT_CARD_BALANCE", "CALCULATED"])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        layout.addRow("Amount Type:", self.type_combo)

        self.linked_card_combo = QComboBox()
        self._load_linked_cards()
        self.linked_card_combo.setEnabled(False)
        layout.addRow("Linked Card:", self.linked_card_combo)

        self.active_check = QCheckBox()
        self.active_check.setChecked(True)
        layout.addRow("Active:", self.active_check)

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

    def _load_linked_cards(self):
        """Load cards for linking"""
        self.linked_card_combo.addItem("None", None)
        for card in CreditCard.get_all():
            self.linked_card_combo.addItem(card.name, card.id)

    def _on_type_changed(self, index: int):
        """Handle amount type change"""
        self.linked_card_combo.setEnabled(index == 1)  # CREDIT_CARD_BALANCE

    def _populate_fields(self):
        """Populate fields with existing charge data"""
        self.name_edit.setText(self.charge.name)
        self.amount_spin.setValue(self.charge.amount)
        self.day_spin.setValue(self.charge.day_of_month)

        # Find and select payment method
        for i in range(self.method_combo.count()):
            if self.method_combo.itemData(i) == self.charge.payment_method:
                self.method_combo.setCurrentIndex(i)
                break

        # Find and select frequency
        freq_index = self.frequency_combo.findText(self.charge.frequency)
        if freq_index >= 0:
            self.frequency_combo.setCurrentIndex(freq_index)

        # Find and select amount type
        type_index = self.type_combo.findText(self.charge.amount_type)
        if type_index >= 0:
            self.type_combo.setCurrentIndex(type_index)

        # Find and select linked card
        if self.charge.linked_card_id:
            for i in range(self.linked_card_combo.count()):
                if self.linked_card_combo.itemData(i) == self.charge.linked_card_id:
                    self.linked_card_combo.setCurrentIndex(i)
                    break

        self.active_check.setChecked(self.charge.is_active)

    def get_charge(self) -> RecurringCharge:
        """Get the charge from the form values"""
        return RecurringCharge(
            id=None,
            name=self.name_edit.text().strip(),
            amount=self.amount_spin.value(),
            day_of_month=self.day_spin.value(),
            payment_method=self.method_combo.currentData(),
            frequency=self.frequency_combo.currentText(),
            amount_type=self.type_combo.currentText(),
            linked_card_id=self.linked_card_combo.currentData(),
            is_active=self.active_check.isChecked()
        )
