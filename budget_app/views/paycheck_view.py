"""Paycheck configuration view"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QFormLayout, QLineEdit,
    QComboBox, QHeaderView, QMessageBox, QDateEdit, QLabel,
    QGroupBox, QGridLayout, QFileDialog, QCheckBox
)
from .widgets import MoneySpinBox, PercentSpinBox
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

from ..models.paycheck import PaycheckConfig, PaycheckDeduction
from ..utils.statement_parser import parse_statement


class PaycheckView(QWidget):
    """View for managing paycheck configuration"""

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        """Set up the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Paycheck summary section
        summary_group = QGroupBox("Current Paycheck Configuration")
        summary_layout = QGridLayout(summary_group)

        self.gross_label = QLabel()
        self.gross_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        summary_layout.addWidget(QLabel("Gross Pay:"), 0, 0)
        summary_layout.addWidget(self.gross_label, 0, 1)

        self.deductions_label = QLabel()
        self.deductions_label.setFont(QFont("Segoe UI", 14))
        summary_layout.addWidget(QLabel("Total Deductions:"), 0, 2)
        summary_layout.addWidget(self.deductions_label, 0, 3)

        self.net_label = QLabel()
        self.net_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.net_label.setStyleSheet("color: #4caf50;")
        summary_layout.addWidget(QLabel("Net Pay:"), 1, 0)
        summary_layout.addWidget(self.net_label, 1, 1)

        self.frequency_label = QLabel()
        summary_layout.addWidget(QLabel("Pay Frequency:"), 1, 2)
        summary_layout.addWidget(self.frequency_label, 1, 3)

        self.pay_day_label = QLabel()
        summary_layout.addWidget(QLabel("Pay Day:"), 1, 4)
        summary_layout.addWidget(self.pay_day_label, 1, 5)

        self.annual_gross_label = QLabel()
        summary_layout.addWidget(QLabel("Annual Gross:"), 2, 0)
        summary_layout.addWidget(self.annual_gross_label, 2, 1)

        self.annual_net_label = QLabel()
        summary_layout.addWidget(QLabel("Annual Net:"), 2, 2)
        summary_layout.addWidget(self.annual_net_label, 2, 3)

        layout.addWidget(summary_group)

        # Toolbar
        toolbar = QHBoxLayout()

        edit_config_btn = QPushButton("Edit Paycheck Config")
        edit_config_btn.clicked.connect(self._edit_config)
        toolbar.addWidget(edit_config_btn)

        import_paystub_btn = QPushButton("Import from Paystub")
        import_paystub_btn.clicked.connect(self._import_paystub)
        toolbar.addWidget(import_paystub_btn)

        add_deduction_btn = QPushButton("Add Deduction")
        add_deduction_btn.clicked.connect(self._add_deduction)
        toolbar.addWidget(add_deduction_btn)

        edit_deduction_btn = QPushButton("Edit Deduction")
        edit_deduction_btn.clicked.connect(self._edit_deduction)
        toolbar.addWidget(edit_deduction_btn)

        delete_deduction_btn = QPushButton("Delete Deduction")
        delete_deduction_btn.clicked.connect(self._delete_deduction)
        toolbar.addWidget(delete_deduction_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Deductions table
        deductions_group = QGroupBox("Deductions")
        deductions_layout = QVBoxLayout(deductions_group)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Name", "Type", "Amount/Rate", "Calculated Amount"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_deduction)
        deductions_layout.addWidget(self.table)

        layout.addWidget(deductions_group, 1)

    def refresh(self):
        """Refresh the view"""
        config = PaycheckConfig.get_current()

        if config:
            self.gross_label.setText(f"${config.gross_amount:,.2f}")
            self.deductions_label.setText(f"${config.total_deductions:,.2f}")
            self.net_label.setText(f"${config.net_pay:,.2f}")
            self.frequency_label.setText(config.pay_frequency)
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            self.pay_day_label.setText(day_names[config.pay_day_of_week] if config.pay_day_of_week < 7 else "Friday")
            self.annual_gross_label.setText(f"${config.annual_gross:,.2f}")
            self.annual_net_label.setText(f"${config.annual_net:,.2f}")

            # Populate deductions table
            self.table.setRowCount(len(config.deductions))
            for row, deduction in enumerate(config.deductions):
                name_item = QTableWidgetItem(deduction.name)
                name_item.setData(Qt.ItemDataRole.UserRole, deduction.id)
                self.table.setItem(row, 0, name_item)

                self.table.setItem(row, 1, QTableWidgetItem(deduction.amount_type))

                if deduction.amount_type == 'PERCENTAGE':
                    self.table.setItem(row, 2, QTableWidgetItem(f"{deduction.amount * 100:.4f}%"))
                else:
                    self.table.setItem(row, 2, QTableWidgetItem(f"${deduction.amount:,.2f}"))

                calc_amount = deduction.calculate_amount(config.gross_amount)
                self.table.setItem(row, 3, QTableWidgetItem(f"${calc_amount:,.2f}"))
        else:
            self.gross_label.setText("$0.00")
            self.deductions_label.setText("$0.00")
            self.net_label.setText("$0.00")
            self.frequency_label.setText("N/A")
            self.pay_day_label.setText("N/A")
            self.annual_gross_label.setText("$0.00")
            self.annual_net_label.setText("$0.00")
            self.table.setRowCount(0)

    def _edit_config(self):
        """Edit the paycheck configuration"""
        config = PaycheckConfig.get_current()
        dialog = PaycheckConfigDialog(self, config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated = dialog.get_config()
            if config:
                updated.id = config.id
            updated.save()
            self.refresh()

    def _get_selected_deduction_id(self) -> int:
        """Get the ID of the selected deduction"""
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def _add_deduction(self):
        """Add a new deduction"""
        config = PaycheckConfig.get_current()
        if not config:
            QMessageBox.warning(self, "Warning", "Please create a paycheck configuration first")
            return

        dialog = DeductionDialog(self, config.gross_amount)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            deduction = dialog.get_deduction()
            deduction.paycheck_config_id = config.id
            deduction.save()
            self.refresh()

    def _edit_deduction(self):
        """Edit the selected deduction"""
        config = PaycheckConfig.get_current()
        if not config:
            return

        deduction_id = self._get_selected_deduction_id()
        if not deduction_id:
            QMessageBox.warning(self, "Warning", "Please select a deduction to edit")
            return

        # Find the deduction
        deduction = None
        for d in config.deductions:
            if d.id == deduction_id:
                deduction = d
                break

        if deduction:
            dialog = DeductionDialog(self, config.gross_amount, deduction)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                updated = dialog.get_deduction()
                updated.id = deduction.id
                updated.paycheck_config_id = config.id
                updated.save()
                self.refresh()

    def _delete_deduction(self):
        """Delete the selected deduction"""
        deduction_id = self._get_selected_deduction_id()
        if not deduction_id:
            QMessageBox.warning(self, "Warning", "Please select a deduction to delete")
            return

        config = PaycheckConfig.get_current()
        if config:
            for d in config.deductions:
                if d.id == deduction_id:
                    reply = QMessageBox.question(
                        self,
                        "Confirm Delete",
                        f"Are you sure you want to delete '{d.name}'?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        d.delete()
                        self.refresh()
                    break

    def _import_paystub(self):
        """Import paycheck config from a paystub PDF"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Paystub PDF", "", "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        try:
            data = parse_statement(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Parse Error", f"Failed to parse PDF:\n{e}")
            return

        if data.statement_type != 'payslip':
            QMessageBox.warning(
                self, "Wrong Document Type",
                "This doesn't appear to be a paystub. "
                f"Detected type: {data.statement_type or 'unknown'}"
            )
            return

        config = PaycheckConfig.get_current()
        dialog = PaystubImportDialog(self, data, config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if not config:
                config = PaycheckConfig(id=None, gross_amount=0.0)
                config.save()

            if dialog.update_gross_cb.isChecked():
                config.gross_amount = data.gross_pay
                config.save()

            if dialog.replace_deductions_cb.isChecked():
                # Delete existing deductions
                for d in config.deductions:
                    d.delete()
                # Create new deductions from parsed data
                for name, amount in data.deductions.items():
                    deduction = PaycheckDeduction(
                        id=None,
                        paycheck_config_id=config.id,
                        name=name,
                        amount_type='FIXED',
                        amount=amount,
                    )
                    deduction.save()

            self.refresh()


class PaystubImportDialog(QDialog):
    """Dialog for reviewing and confirming paystub import"""

    def __init__(self, parent, data, config=None):
        super().__init__(parent)
        self.data = data
        self.config = config
        self.setWindowTitle("Import Paystub")
        self.setMinimumWidth(550)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Pay period info
        period_group = QGroupBox("Parsed Paystub Summary")
        period_layout = QGridLayout(period_group)

        period_layout.addWidget(QLabel("Gross Pay:"), 0, 0)
        gross_label = QLabel(f"${self.data.gross_pay:,.2f}")
        gross_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        period_layout.addWidget(gross_label, 0, 1)

        period_layout.addWidget(QLabel("Net Pay:"), 0, 2)
        net_label = QLabel(f"${self.data.net_pay:,.2f}")
        net_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        net_label.setStyleSheet("color: #4caf50;")
        period_layout.addWidget(net_label, 0, 3)

        if self.data.pay_period_start and self.data.pay_period_end:
            period_layout.addWidget(QLabel("Pay Period:"), 1, 0)
            period_layout.addWidget(
                QLabel(f"{self.data.pay_period_start} to {self.data.pay_period_end}"), 1, 1, 1, 3
            )

        layout.addWidget(period_group)

        # Comparison with current config
        if self.config:
            compare_group = QGroupBox("Comparison with Current Config")
            compare_layout = QGridLayout(compare_group)

            compare_layout.addWidget(QLabel(""), 0, 0)
            current_header = QLabel("Current")
            current_header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            compare_layout.addWidget(current_header, 0, 1)
            parsed_header = QLabel("Paystub")
            parsed_header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            compare_layout.addWidget(parsed_header, 0, 2)
            diff_header = QLabel("Difference")
            diff_header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            compare_layout.addWidget(diff_header, 0, 3)

            compare_layout.addWidget(QLabel("Gross:"), 1, 0)
            compare_layout.addWidget(QLabel(f"${self.config.gross_amount:,.2f}"), 1, 1)
            compare_layout.addWidget(QLabel(f"${self.data.gross_pay:,.2f}"), 1, 2)
            gross_diff = self.data.gross_pay - self.config.gross_amount
            diff_label = QLabel(f"{'+'if gross_diff >= 0 else ''}{gross_diff:,.2f}")
            if gross_diff != 0:
                diff_label.setStyleSheet("color: #f44336;" if gross_diff < 0 else "color: #4caf50;")
            compare_layout.addWidget(diff_label, 1, 3)

            compare_layout.addWidget(QLabel("Net:"), 2, 0)
            compare_layout.addWidget(QLabel(f"${self.config.net_pay:,.2f}"), 2, 1)
            compare_layout.addWidget(QLabel(f"${self.data.net_pay:,.2f}"), 2, 2)
            net_diff = self.data.net_pay - self.config.net_pay
            net_diff_label = QLabel(f"{'+'if net_diff >= 0 else ''}{net_diff:,.2f}")
            if net_diff != 0:
                net_diff_label.setStyleSheet("color: #f44336;" if net_diff < 0 else "color: #4caf50;")
            compare_layout.addWidget(net_diff_label, 2, 3)

            layout.addWidget(compare_group)

        # Deductions table
        deductions_group = QGroupBox(f"Deductions ({len(self.data.deductions)} items)")
        deductions_layout = QVBoxLayout(deductions_group)

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Name", "Amount"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        items = list(self.data.deductions.items())
        table.setRowCount(len(items))
        for row, (name, amount) in enumerate(items):
            table.setItem(row, 0, QTableWidgetItem(name))
            table.setItem(row, 1, QTableWidgetItem(f"${amount:,.2f}"))

        deductions_layout.addWidget(table)
        layout.addWidget(deductions_group, 1)

        # Options checkboxes
        options_group = QGroupBox("Import Options")
        options_layout = QVBoxLayout(options_group)

        self.update_gross_cb = QCheckBox("Update gross amount")
        self.update_gross_cb.setChecked(True)
        options_layout.addWidget(self.update_gross_cb)

        self.replace_deductions_cb = QCheckBox("Replace all deductions")
        self.replace_deductions_cb.setChecked(True)
        options_layout.addWidget(self.replace_deductions_cb)

        layout.addWidget(options_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("Import")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)


class PaycheckConfigDialog(QDialog):
    """Dialog for editing paycheck configuration"""

    def __init__(self, parent=None, config: PaycheckConfig = None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Edit Paycheck Configuration")
        self.setMinimumWidth(400)
        self._setup_ui()
        if config:
            self._populate_fields()

    def _setup_ui(self):
        """Set up the dialog UI"""
        layout = QFormLayout(self)

        self.gross_spin = MoneySpinBox()
        self.gross_spin.setMinimum(0)
        layout.addRow("Gross Pay:", self.gross_spin)

        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems(["BIWEEKLY", "WEEKLY", "SEMIMONTHLY", "MONTHLY"])
        layout.addRow("Pay Frequency:", self.frequency_combo)

        self.pay_day_combo = QComboBox()
        self.pay_day_combo.addItem("Monday", 0)
        self.pay_day_combo.addItem("Tuesday", 1)
        self.pay_day_combo.addItem("Wednesday", 2)
        self.pay_day_combo.addItem("Thursday", 3)
        self.pay_day_combo.addItem("Friday", 4)
        self.pay_day_combo.setCurrentIndex(4)  # Default to Friday
        layout.addRow("Pay Day:", self.pay_day_combo)

        self.effective_date = QDateEdit()
        self.effective_date.setDate(QDate.currentDate())
        self.effective_date.setCalendarPopup(True)
        self.effective_date.setDisplayFormat("MM/dd/yyyy")
        layout.addRow("Effective Date:", self.effective_date)

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

    def _populate_fields(self):
        """Populate fields with existing config data"""
        self.gross_spin.setValue(self.config.gross_amount)

        freq_index = self.frequency_combo.findText(self.config.pay_frequency)
        if freq_index >= 0:
            self.frequency_combo.setCurrentIndex(freq_index)

        # Set pay day of week
        pay_day_index = self.pay_day_combo.findData(self.config.pay_day_of_week)
        if pay_day_index >= 0:
            self.pay_day_combo.setCurrentIndex(pay_day_index)

        if self.config.effective_date:
            date = QDate.fromString(self.config.effective_date, "yyyy-MM-dd")
            self.effective_date.setDate(date)

    def get_config(self) -> PaycheckConfig:
        """Get the config from the form values"""
        return PaycheckConfig(
            id=None,
            gross_amount=self.gross_spin.value(),
            pay_frequency=self.frequency_combo.currentText(),
            effective_date=self.effective_date.date().toString("yyyy-MM-dd"),
            is_current=True,
            pay_day_of_week=self.pay_day_combo.currentData()
        )


class DeductionDialog(QDialog):
    """Dialog for adding/editing a deduction"""

    def __init__(self, parent=None, gross_pay: float = 0, deduction: PaycheckDeduction = None):
        super().__init__(parent)
        self.deduction = deduction
        self.gross_pay = gross_pay
        self.setWindowTitle("Edit Deduction" if deduction else "Add Deduction")
        self.setMinimumWidth(400)
        self._setup_ui()
        if deduction:
            self._populate_fields()

    def _setup_ui(self):
        """Set up the dialog UI"""
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        layout.addRow("Name:", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["FIXED", "PERCENTAGE"])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        layout.addRow("Type:", self.type_combo)

        self.amount_spin = MoneySpinBox()
        self.amount_spin.setMinimum(0)
        self.amount_spin.setMaximum(100000)
        layout.addRow("Amount:", self.amount_spin)

        self.percent_spin = PercentSpinBox(decimals=4)
        self.percent_spin.setVisible(False)
        layout.addRow("Percentage:", self.percent_spin)

        self.calc_label = QLabel()
        layout.addRow("Calculated:", self.calc_label)

        self.amount_spin.valueChanged.connect(self._update_calculated)
        self.percent_spin.valueChanged.connect(self._update_calculated)

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

    def _on_type_changed(self, index: int):
        """Handle type change"""
        is_percentage = index == 1
        self.amount_spin.setVisible(not is_percentage)
        self.percent_spin.setVisible(is_percentage)
        self._update_calculated()

    def _update_calculated(self):
        """Update the calculated amount label"""
        if self.type_combo.currentText() == 'PERCENTAGE':
            amount = self.gross_pay * (self.percent_spin.value() / 100)
        else:
            amount = self.amount_spin.value()
        self.calc_label.setText(f"${amount:,.2f}")

    def _populate_fields(self):
        """Populate fields with existing deduction data"""
        self.name_edit.setText(self.deduction.name)

        type_index = 0 if self.deduction.amount_type == 'FIXED' else 1
        self.type_combo.setCurrentIndex(type_index)

        if self.deduction.amount_type == 'PERCENTAGE':
            self.percent_spin.setValue(self.deduction.amount * 100)
        else:
            self.amount_spin.setValue(self.deduction.amount)

        self._update_calculated()

    def get_deduction(self) -> PaycheckDeduction:
        """Get the deduction from the form values"""
        is_percentage = self.type_combo.currentText() == 'PERCENTAGE'
        amount = self.percent_spin.value() / 100 if is_percentage else self.amount_spin.value()

        return PaycheckDeduction(
            id=None,
            paycheck_config_id=0,  # Will be set by caller
            name=self.name_edit.text().strip(),
            amount_type=self.type_combo.currentText(),
            amount=amount
        )
