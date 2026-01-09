"""Posted transactions view - shows transactions that have been marked as posted"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMessageBox, QLabel, QLineEdit, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ..models.transaction import Transaction
from ..models.credit_card import CreditCard


class PostedTransactionsView(QWidget):
    """View for posted (historical) transactions"""

    def __init__(self):
        super().__init__()
        self._data_dirty = True
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Posted Transactions")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Delete selected button
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setToolTip("Permanently delete the selected posted transaction")
        delete_btn.clicked.connect(self._delete_selected)
        header_layout.addWidget(delete_btn)

        # Clear all button
        clear_btn = QPushButton("Clear All Posted")
        clear_btn.setToolTip("Permanently delete all posted transactions")
        clear_btn.clicked.connect(self._clear_all_posted)
        header_layout.addWidget(clear_btn)

        layout.addLayout(header_layout)

        # Filter row
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)

        filter_layout.addWidget(QLabel("Filters:"))

        # Description filter
        filter_layout.addWidget(QLabel("Description:"))
        self.desc_filter = QLineEdit()
        self.desc_filter.setPlaceholderText("Search...")
        self.desc_filter.setFixedWidth(150)
        self.desc_filter.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.desc_filter)

        # Payment type filter
        filter_layout.addWidget(QLabel("Pay Type:"))
        self.pay_type_filter = QComboBox()
        self.pay_type_filter.addItem("All", None)
        self.pay_type_filter.addItem("Chase (Bank)", "C")
        for card in CreditCard.get_all():
            self.pay_type_filter.addItem(card.name, card.pay_type_code)
        self.pay_type_filter.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.pay_type_filter)

        # Clear filters button
        clear_filters_btn = QPushButton("Clear Filters")
        clear_filters_btn.clicked.connect(self._clear_filters)
        filter_layout.addWidget(clear_filters_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Info label
        self.info_label = QLabel()
        layout.addWidget(self.info_label)

        # Main table
        self.table = QTableWidget()
        self._setup_table()
        layout.addWidget(self.table)

    def _setup_table(self):
        """Set up the table columns"""
        columns = ["Due Date", "Posted Date", "Pay Type", "Description", "Amount", "Notes"]
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)

        # Column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)

        self.table.setColumnWidth(0, 100)  # Due Date
        self.table.setColumnWidth(1, 100)  # Posted Date
        self.table.setColumnWidth(2, 80)   # Pay Type
        self.table.setColumnWidth(3, 250)  # Description
        self.table.setColumnWidth(4, 100)  # Amount

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    def mark_dirty(self):
        """Mark data as dirty so next refresh reloads from database"""
        self._data_dirty = True

    def refresh(self):
        """Refresh the table with posted transactions"""
        if not self._data_dirty:
            return

        self._data_dirty = False

        # Get all posted transactions
        transactions = Transaction.get_posted()

        self.table.setRowCount(len(transactions))

        for row, trans in enumerate(transactions):
            # Due Date (original transaction date)
            due_date = trans.date[:10]
            display_due = f"{due_date[5:7]}/{due_date[8:10]}/{due_date[:4]}"
            due_item = QTableWidgetItem(display_due)
            self.table.setItem(row, 0, due_item)

            # Posted Date
            if trans.posted_date:
                posted_date = trans.posted_date[:10]
                display_posted = f"{posted_date[5:7]}/{posted_date[8:10]}/{posted_date[:4]}"
            else:
                display_posted = "-"
            posted_item = QTableWidgetItem(display_posted)
            self.table.setItem(row, 1, posted_item)

            # Pay Type
            pay_item = QTableWidgetItem(trans.payment_method)
            self.table.setItem(row, 2, pay_item)

            # Description
            desc_item = QTableWidgetItem(trans.description)
            desc_item.setData(Qt.ItemDataRole.UserRole, trans.id)
            self.table.setItem(row, 3, desc_item)

            # Amount
            amount_item = QTableWidgetItem(f"${trans.amount:,.2f}")
            if trans.amount < 0:
                amount_item.setForeground(QColor("#f44336"))
            else:
                amount_item.setForeground(QColor("#4caf50"))
            self.table.setItem(row, 4, amount_item)

            # Notes
            notes_item = QTableWidgetItem(trans.notes or "")
            self.table.setItem(row, 5, notes_item)

        self.info_label.setText(f"Showing {len(transactions)} posted transaction(s)")

    def _apply_filters(self):
        """Apply filters to show/hide rows"""
        desc_filter = self.desc_filter.text().lower().strip()
        pay_type = self.pay_type_filter.currentData()

        for row in range(self.table.rowCount()):
            show_row = True

            # Description filter
            if desc_filter:
                desc_item = self.table.item(row, 3)
                if desc_item and desc_filter not in desc_item.text().lower():
                    show_row = False

            # Pay type filter
            if show_row and pay_type:
                pay_item = self.table.item(row, 2)
                if pay_item and pay_item.text() != pay_type:
                    show_row = False

            self.table.setRowHidden(row, not show_row)

    def _clear_filters(self):
        """Clear all filters"""
        self.desc_filter.setText("")
        self.pay_type_filter.setCurrentIndex(0)
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, False)

    def _get_selected_transaction_id(self) -> int:
        """Get the ID of the selected transaction"""
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        desc_item = self.table.item(row, 3)
        return desc_item.data(Qt.ItemDataRole.UserRole) if desc_item else None

    def _delete_selected(self):
        """Delete the selected posted transaction"""
        trans_id = self._get_selected_transaction_id()
        if not trans_id:
            QMessageBox.warning(self, "Warning", "Please select a transaction to delete")
            return

        trans = Transaction.get_by_id(trans_id)
        if trans:
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Permanently delete '{trans.description}'?\n\n"
                "This cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                trans.delete()
                self.mark_dirty()
                self.refresh()

    def _clear_all_posted(self):
        """Clear all posted transactions"""
        count = len(Transaction.get_posted())

        if count == 0:
            QMessageBox.information(self, "Info", "There are no posted transactions.")
            return

        reply = QMessageBox.warning(
            self,
            "Confirm Clear All",
            f"This will permanently delete ALL {count} posted transaction(s).\n\n"
            "This action cannot be undone.\n\n"
            "Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            deleted = Transaction.clear_posted()
            QMessageBox.information(self, "Cleared", f"Deleted {deleted} posted transaction(s).")
            self.mark_dirty()
            self.refresh()
