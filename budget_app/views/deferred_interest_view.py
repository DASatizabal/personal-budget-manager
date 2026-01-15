"""Deferred Interest tracking view"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QFormLayout, QLineEdit, QDateEdit,
    QComboBox, QHeaderView, QMessageBox, QLabel, QGroupBox
)
from .widgets import MoneySpinBox, PercentSpinBox
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont

from ..models.deferred_interest import DeferredPurchase
from ..models.credit_card import CreditCard


class DeferredInterestView(QWidget):
    """View for managing deferred interest purchases"""

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        """Set up the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header = QLabel("Deferred Interest Tracking")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        layout.addWidget(header)

        subtitle = QLabel(
            "Track 0% APR promotional purchases to avoid retroactive interest charges"
        )
        subtitle.setStyleSheet("color: #888;")
        layout.addWidget(subtitle)

        # Toolbar
        toolbar = QHBoxLayout()

        add_btn = QPushButton("Add Purchase")
        add_btn.clicked.connect(self._add_purchase)
        toolbar.addWidget(add_btn)

        edit_btn = QPushButton("Edit Selected")
        edit_btn.clicked.connect(self._edit_purchase)
        toolbar.addWidget(edit_btn)

        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self._delete_purchase)
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
            "Card", "Description", "Original", "Remaining",
            "Promo End", "Days Left", "Monthly Needed", "Standard APR", "Risk"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_purchase)
        layout.addWidget(self.table)

        # Summary section
        summary_group = QGroupBox("Summary")
        summary_layout = QHBoxLayout(summary_group)

        self.total_balance_label = QLabel()
        self.total_interest_label = QLabel()
        self.at_risk_label = QLabel()

        summary_layout.addWidget(self.total_balance_label)
        summary_layout.addWidget(self.total_interest_label)
        summary_layout.addWidget(self.at_risk_label)
        summary_layout.addStretch()

        layout.addWidget(summary_group)

        # Alert section (for high-risk items)
        self.alert_group = QGroupBox("Alerts")
        self.alert_layout = QVBoxLayout(self.alert_group)
        self.alert_label = QLabel()
        self.alert_label.setWordWrap(True)
        self.alert_layout.addWidget(self.alert_label)
        layout.addWidget(self.alert_group)

    def refresh(self):
        """Refresh the table data"""
        purchases = DeferredPurchase.get_all()
        self.table.setRowCount(len(purchases))

        # Build card lookup
        cards = {card.id: card for card in CreditCard.get_all()}

        for row, purchase in enumerate(purchases):
            card = cards.get(purchase.credit_card_id)
            card_name = card.name if card else "Unknown"

            self.table.setItem(row, 0, QTableWidgetItem(card_name))
            self.table.setItem(row, 1, QTableWidgetItem(purchase.description))
            self.table.setItem(row, 2, QTableWidgetItem(f"${purchase.purchase_amount:,.2f}"))

            remaining_item = QTableWidgetItem(f"${purchase.remaining_balance:,.2f}")
            self.table.setItem(row, 3, remaining_item)

            self.table.setItem(row, 4, QTableWidgetItem(purchase.promo_end_date))

            days_item = QTableWidgetItem(str(purchase.days_until_expiry))
            self.table.setItem(row, 5, days_item)

            monthly_item = QTableWidgetItem(f"${purchase.monthly_payment_needed:,.2f}")
            self.table.setItem(row, 6, monthly_item)

            self.table.setItem(row, 7, QTableWidgetItem(f"{purchase.standard_apr * 100:.1f}%"))

            risk_item = QTableWidgetItem(purchase.risk_level)
            self.table.setItem(row, 8, risk_item)

            # Color coding based on risk
            risk_color = self._get_risk_color(purchase.risk_level)
            if risk_color:
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setForeground(risk_color)

            # Store purchase id in first column
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, purchase.id)

        # Update summary
        total_balance = DeferredPurchase.get_total_deferred_balance()
        total_interest = DeferredPurchase.get_total_potential_interest()
        at_risk = len(DeferredPurchase.get_at_risk())

        self.total_balance_label.setText(f"Total Deferred: ${total_balance:,.2f}")
        self.total_interest_label.setText(f"Potential Interest: ${total_interest:,.2f}")

        if at_risk > 0:
            self.at_risk_label.setText(f"At Risk: {at_risk} purchase(s)")
            self.at_risk_label.setStyleSheet("color: #f44336; font-weight: bold;")
        else:
            self.at_risk_label.setText("At Risk: None")
            self.at_risk_label.setStyleSheet("color: #4caf50;")

        # Update alerts
        self._update_alerts(purchases)

    def _get_risk_color(self, risk_level: str) -> QColor:
        """Get color for risk level"""
        if risk_level == "EXPIRED":
            return QColor("#f44336")  # Red
        elif risk_level == "HIGH":
            return QColor("#ff5722")  # Deep orange
        elif risk_level == "MEDIUM":
            return QColor("#ff9800")  # Orange
        return None  # Default color for LOW

    def _update_alerts(self, purchases):
        """Update the alerts section"""
        alerts = []

        expired = [p for p in purchases if p.risk_level == "EXPIRED"]
        high_risk = [p for p in purchases if p.risk_level == "HIGH"]

        if expired:
            alerts.append(f"EXPIRED: {len(expired)} promotional period(s) have ended!")
            for p in expired[:3]:
                potential = p.potential_interest_charge
                alerts.append(f"  - {p.description}: Potential interest ${potential:,.2f}")

        if high_risk:
            alerts.append(f"HIGH RISK: {len(high_risk)} purchase(s) expire within 60 days")
            for p in high_risk[:3]:
                alerts.append(
                    f"  - {p.description}: ${p.remaining_balance:,.2f} "
                    f"(need ${p.monthly_payment_needed:,.2f}/mo)"
                )

        if alerts:
            self.alert_label.setText("\n".join(alerts))
            self.alert_group.setStyleSheet("QGroupBox { border: 2px solid #f44336; }")
            self.alert_group.show()
        else:
            self.alert_group.hide()

    def _get_selected_purchase_id(self) -> int:
        """Get the ID of the selected purchase"""
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def _add_purchase(self):
        """Add a new deferred purchase"""
        dialog = DeferredPurchaseDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            purchase = dialog.get_purchase()
            purchase.save()
            self.refresh()

    def _edit_purchase(self):
        """Edit the selected deferred purchase"""
        purchase_id = self._get_selected_purchase_id()
        if not purchase_id:
            QMessageBox.warning(self, "Warning", "Please select a purchase to edit")
            return

        purchase = DeferredPurchase.get_by_id(purchase_id)
        if purchase:
            dialog = DeferredPurchaseDialog(self, purchase)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                updated = dialog.get_purchase()
                updated.id = purchase.id
                updated.save()
                self.refresh()

    def _delete_purchase(self):
        """Delete the selected deferred purchase"""
        purchase_id = self._get_selected_purchase_id()
        if not purchase_id:
            QMessageBox.warning(self, "Warning", "Please select a purchase to delete")
            return

        purchase = DeferredPurchase.get_by_id(purchase_id)
        if purchase:
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Delete '{purchase.description}'?\n\n"
                f"Remaining balance: ${purchase.remaining_balance:,.2f}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                purchase.delete()
                self.refresh()


class DeferredPurchaseDialog(QDialog):
    """Dialog for adding/editing a deferred interest purchase"""

    def __init__(self, parent=None, purchase: DeferredPurchase = None):
        super().__init__(parent)
        self.purchase = purchase
        self.setWindowTitle("Edit Deferred Purchase" if purchase else "Add Deferred Purchase")
        self.setMinimumWidth(450)
        self._setup_ui()
        if purchase:
            self._populate_fields()

    def _setup_ui(self):
        """Set up the dialog UI"""
        layout = QFormLayout(self)
        layout.setSpacing(12)

        # Credit card selection
        self.card_combo = QComboBox()
        cards = CreditCard.get_all()
        for card in cards:
            self.card_combo.addItem(f"{card.name} ({card.pay_type_code})", card.id)
        layout.addRow("Credit Card:", self.card_combo)

        # Description
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("e.g., Best Buy TV Purchase")
        layout.addRow("Description:", self.description_edit)

        # Purchase amount
        self.purchase_amount_spin = MoneySpinBox()
        self.purchase_amount_spin.setMinimum(0)
        self.purchase_amount_spin.setMaximum(100000)
        layout.addRow("Original Purchase Amount:", self.purchase_amount_spin)

        # Remaining balance
        self.remaining_spin = MoneySpinBox()
        self.remaining_spin.setMinimum(0)
        self.remaining_spin.setMaximum(100000)
        layout.addRow("Remaining Balance:", self.remaining_spin)

        # Promo APR
        self.promo_apr_spin = PercentSpinBox()
        self.promo_apr_spin.setValue(0)  # Usually 0% for deferred interest
        layout.addRow("Promotional APR:", self.promo_apr_spin)

        # Standard APR
        self.standard_apr_spin = PercentSpinBox()
        self.standard_apr_spin.setValue(29.99)  # Common default
        layout.addRow("Standard APR (after promo):", self.standard_apr_spin)

        # Promo end date
        self.promo_end_edit = QDateEdit()
        self.promo_end_edit.setCalendarPopup(True)
        self.promo_end_edit.setDate(QDate.currentDate().addMonths(12))
        self.promo_end_edit.setMinimumDate(QDate.currentDate().addDays(-365))
        layout.addRow("Promotional Period Ends:", self.promo_end_edit)

        # Min monthly payment
        self.min_payment_spin = MoneySpinBox()
        self.min_payment_spin.setMinimum(0)
        self.min_payment_spin.setMaximum(10000)
        layout.addRow("Min Monthly Payment:", self.min_payment_spin)

        # Info label
        info_label = QLabel(
            "Deferred interest means if ANY balance remains when the promo ends, "
            "you owe interest on the FULL original purchase amount from day one."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #ff9800; font-style: italic;")
        layout.addRow(info_label)

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

        if not self.description_edit.text().strip():
            errors.append("Description is required.")

        if self.purchase_amount_spin.value() <= 0:
            errors.append("Original purchase amount must be greater than 0.")

        if self.remaining_spin.value() < 0:
            errors.append("Remaining balance cannot be negative.")

        if self.remaining_spin.value() > self.purchase_amount_spin.value():
            errors.append("Remaining balance cannot exceed original purchase amount.")

        if self.standard_apr_spin.value() <= 0:
            errors.append("Standard APR must be greater than 0.")

        if errors:
            QMessageBox.warning(self, "Validation Error", "\n".join(errors))
            return

        self.accept()

    def _populate_fields(self):
        """Populate fields with existing purchase data"""
        # Find and select the card
        for i in range(self.card_combo.count()):
            if self.card_combo.itemData(i) == self.purchase.credit_card_id:
                self.card_combo.setCurrentIndex(i)
                break

        self.description_edit.setText(self.purchase.description)
        self.purchase_amount_spin.setValue(self.purchase.purchase_amount)
        self.remaining_spin.setValue(self.purchase.remaining_balance)
        self.promo_apr_spin.setValue(self.purchase.promo_apr * 100)
        self.standard_apr_spin.setValue(self.purchase.standard_apr * 100)

        promo_date = QDate.fromString(self.purchase.promo_end_date, "yyyy-MM-dd")
        self.promo_end_edit.setDate(promo_date)

        if self.purchase.min_monthly_payment:
            self.min_payment_spin.setValue(self.purchase.min_monthly_payment)

    def get_purchase(self) -> DeferredPurchase:
        """Get the purchase from the form values"""
        return DeferredPurchase(
            id=None,
            credit_card_id=self.card_combo.currentData(),
            description=self.description_edit.text().strip(),
            purchase_amount=self.purchase_amount_spin.value(),
            remaining_balance=self.remaining_spin.value(),
            promo_apr=self.promo_apr_spin.value() / 100,
            standard_apr=self.standard_apr_spin.value() / 100,
            promo_end_date=self.promo_end_edit.date().toString("yyyy-MM-dd"),
            min_monthly_payment=self.min_payment_spin.value() or None,
            created_date=self.purchase.created_date if self.purchase else None
        )
