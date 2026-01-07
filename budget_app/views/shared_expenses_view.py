"""Shared Expenses (Lisa Payment Splitting) view"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QComboBox, QHeaderView, QMessageBox, QGroupBox, QLabel,
    QGridLayout, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..models.shared_expense import SharedExpense
from ..models.recurring_charge import RecurringCharge


class SharedExpensesView(QWidget):
    """View for managing shared expenses (Lisa payment splitting)"""

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        """Set up the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Summary section
        summary_group = QGroupBox("Payment Summary")
        summary_layout = QGridLayout(summary_group)

        # 2-Paycheck month calculation
        summary_layout.addWidget(QLabel("2-Paycheck Month:"), 0, 0)
        self.two_paycheck_label = QLabel()
        self.two_paycheck_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        summary_layout.addWidget(self.two_paycheck_label, 0, 1)

        summary_layout.addWidget(QLabel("Per Paycheck:"), 0, 2)
        self.two_per_paycheck_label = QLabel()
        self.two_per_paycheck_label.setFont(QFont("Segoe UI", 14))
        summary_layout.addWidget(self.two_per_paycheck_label, 0, 3)

        # 3-Paycheck month calculation
        summary_layout.addWidget(QLabel("3-Paycheck Month:"), 1, 0)
        self.three_paycheck_label = QLabel()
        self.three_paycheck_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        summary_layout.addWidget(self.three_paycheck_label, 1, 1)

        summary_layout.addWidget(QLabel("Per Paycheck:"), 1, 2)
        self.three_per_paycheck_label = QLabel()
        self.three_per_paycheck_label.setFont(QFont("Segoe UI", 14))
        summary_layout.addWidget(self.three_per_paycheck_label, 1, 3)

        # Total monthly
        summary_layout.addWidget(QLabel("Total Monthly:"), 2, 0)
        self.total_monthly_label = QLabel()
        self.total_monthly_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.total_monthly_label.setStyleSheet("color: #4caf50;")
        summary_layout.addWidget(self.total_monthly_label, 2, 1)

        layout.addWidget(summary_group)

        # Toolbar
        toolbar = QHBoxLayout()

        add_btn = QPushButton("Add Shared Expense")
        add_btn.clicked.connect(self._add_expense)
        toolbar.addWidget(add_btn)

        edit_btn = QPushButton("Edit Selected")
        edit_btn.clicked.connect(self._edit_expense)
        toolbar.addWidget(edit_btn)

        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self._delete_expense)
        toolbar.addWidget(delete_btn)

        toolbar.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        # Expenses table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Expense", "Monthly Amount", "Split Type", "2-Paycheck Split", "3-Paycheck Split"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_expense)
        layout.addWidget(self.table)

    def refresh(self):
        """Refresh the view"""
        expenses = SharedExpense.get_all()

        # Update summary
        total_monthly = SharedExpense.get_total_monthly()
        two_paycheck_total = sum(e.get_split_amount(2) * 2 for e in expenses)
        three_paycheck_total = sum(e.get_split_amount(3) * 3 for e in expenses)

        self.total_monthly_label.setText(f"${total_monthly:,.2f}")
        self.two_paycheck_label.setText(f"${two_paycheck_total:,.2f}")
        self.two_per_paycheck_label.setText(f"${two_paycheck_total / 2:,.2f}" if two_paycheck_total > 0 else "$0.00")
        self.three_paycheck_label.setText(f"${three_paycheck_total:,.2f}")
        self.three_per_paycheck_label.setText(f"${three_paycheck_total / 3:,.2f}" if three_paycheck_total > 0 else "$0.00")

        # Update table
        self.table.setRowCount(len(expenses))

        for row, expense in enumerate(expenses):
            name_item = QTableWidgetItem(expense.name)
            name_item.setData(Qt.ItemDataRole.UserRole, expense.id)
            self.table.setItem(row, 0, name_item)

            self.table.setItem(row, 1, QTableWidgetItem(f"${expense.monthly_amount:,.2f}"))
            self.table.setItem(row, 2, QTableWidgetItem(expense.split_type))
            self.table.setItem(row, 3, QTableWidgetItem(f"${expense.get_split_amount(2):,.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"${expense.get_split_amount(3):,.2f}"))

    def _get_selected_expense_id(self) -> int:
        """Get the ID of the selected expense"""
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def _add_expense(self):
        """Add a new shared expense"""
        dialog = SharedExpenseDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            expense = dialog.get_expense()
            expense.save()
            self.refresh()

    def _edit_expense(self):
        """Edit the selected shared expense"""
        expense_id = self._get_selected_expense_id()
        if not expense_id:
            QMessageBox.warning(self, "Warning", "Please select an expense to edit")
            return

        expense = SharedExpense.get_by_id(expense_id)
        if expense:
            dialog = SharedExpenseDialog(self, expense)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                updated = dialog.get_expense()
                updated.id = expense.id
                updated.save()
                self.refresh()

    def _delete_expense(self):
        """Delete the selected shared expense"""
        expense_id = self._get_selected_expense_id()
        if not expense_id:
            QMessageBox.warning(self, "Warning", "Please select an expense to delete")
            return

        expense = SharedExpense.get_by_id(expense_id)
        if expense:
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Are you sure you want to delete '{expense.name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                expense.delete()
                self.refresh()


class SharedExpenseDialog(QDialog):
    """Dialog for adding/editing a shared expense"""

    def __init__(self, parent=None, expense: SharedExpense = None):
        super().__init__(parent)
        self.expense = expense
        self.setWindowTitle("Edit Shared Expense" if expense else "Add Shared Expense")
        self.setMinimumWidth(400)
        self._setup_ui()
        if expense:
            self._populate_fields()

    def _setup_ui(self):
        """Set up the dialog UI"""
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        layout.addRow("Name:", self.name_edit)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 100000)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setPrefix("$")
        self.amount_spin.valueChanged.connect(self._update_preview)
        layout.addRow("Monthly Amount:", self.amount_spin)

        # Split type radio buttons
        self.split_group = QButtonGroup(self)
        split_layout = QHBoxLayout()

        self.half_radio = QRadioButton("Half (50%)")
        self.half_radio.setChecked(True)
        self.half_radio.toggled.connect(self._update_preview)
        self.split_group.addButton(self.half_radio)
        split_layout.addWidget(self.half_radio)

        self.third_radio = QRadioButton("Third (33%)")
        self.third_radio.toggled.connect(self._update_preview)
        self.split_group.addButton(self.third_radio)
        split_layout.addWidget(self.third_radio)

        self.custom_radio = QRadioButton("Custom")
        self.custom_radio.toggled.connect(self._on_custom_toggled)
        self.split_group.addButton(self.custom_radio)
        split_layout.addWidget(self.custom_radio)

        layout.addRow("Split Type:", split_layout)

        self.custom_spin = QDoubleSpinBox()
        self.custom_spin.setRange(0, 100)
        self.custom_spin.setDecimals(1)
        self.custom_spin.setSuffix("%")
        self.custom_spin.setValue(50)
        self.custom_spin.setEnabled(False)
        self.custom_spin.valueChanged.connect(self._update_preview)
        layout.addRow("Custom Ratio:", self.custom_spin)

        # Link to recurring charge
        self.linked_combo = QComboBox()
        self._load_recurring_charges()
        layout.addRow("Link to Recurring:", self.linked_combo)

        # Preview
        preview_group = QGroupBox("Payment Preview")
        preview_layout = QGridLayout(preview_group)

        preview_layout.addWidget(QLabel("2-Paycheck:"), 0, 0)
        self.preview_2_label = QLabel("$0.00")
        preview_layout.addWidget(self.preview_2_label, 0, 1)

        preview_layout.addWidget(QLabel("3-Paycheck:"), 1, 0)
        self.preview_3_label = QLabel("$0.00")
        preview_layout.addWidget(self.preview_3_label, 1, 1)

        layout.addRow(preview_group)

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

    def _load_recurring_charges(self):
        """Load recurring charges for linking"""
        self.linked_combo.addItem("None", None)
        for charge in RecurringCharge.get_all():
            self.linked_combo.addItem(charge.name, charge.id)

    def _on_custom_toggled(self, checked: bool):
        """Handle custom radio toggle"""
        self.custom_spin.setEnabled(checked)
        self._update_preview()

    def _update_preview(self):
        """Update the payment preview"""
        amount = self.amount_spin.value()

        if self.half_radio.isChecked():
            split_2 = amount / 2
            split_3 = amount / 3
        elif self.third_radio.isChecked():
            split_2 = amount / 3
            split_3 = amount / 3
        else:  # Custom
            ratio = self.custom_spin.value() / 100
            split_2 = amount * ratio / 2
            split_3 = amount * ratio / 3

        self.preview_2_label.setText(f"${split_2:,.2f}")
        self.preview_3_label.setText(f"${split_3:,.2f}")

    def _populate_fields(self):
        """Populate fields with existing expense data"""
        self.name_edit.setText(self.expense.name)
        self.amount_spin.setValue(self.expense.monthly_amount)

        if self.expense.split_type == 'THIRD':
            self.third_radio.setChecked(True)
        elif self.expense.split_type == 'CUSTOM':
            self.custom_radio.setChecked(True)
            if self.expense.custom_split_ratio:
                self.custom_spin.setValue(self.expense.custom_split_ratio * 100)
        else:
            self.half_radio.setChecked(True)

        if self.expense.linked_recurring_id:
            for i in range(self.linked_combo.count()):
                if self.linked_combo.itemData(i) == self.expense.linked_recurring_id:
                    self.linked_combo.setCurrentIndex(i)
                    break

        self._update_preview()

    def get_expense(self) -> SharedExpense:
        """Get the expense from the form values"""
        if self.half_radio.isChecked():
            split_type = 'HALF'
            custom_ratio = None
        elif self.third_radio.isChecked():
            split_type = 'THIRD'
            custom_ratio = None
        else:
            split_type = 'CUSTOM'
            custom_ratio = self.custom_spin.value() / 100

        return SharedExpense(
            id=None,
            name=self.name_edit.text().strip(),
            monthly_amount=self.amount_spin.value(),
            split_type=split_type,
            custom_split_ratio=custom_ratio,
            linked_recurring_id=self.linked_combo.currentData()
        )
