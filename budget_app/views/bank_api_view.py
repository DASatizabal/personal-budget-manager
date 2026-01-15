"""Bank API integration placeholder view"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor


class BankAPIView(QWidget):
    """Placeholder view for bank API integration (Plaid/Yodlee)"""

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        """Set up the placeholder UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Header
        header = QLabel("Bank API Integration")
        header.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        subtitle = QLabel("Connect to your bank for automatic transaction imports")
        subtitle.setFont(QFont("Segoe UI", 12))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #888;")
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Status section
        status_group = QGroupBox("Connection Status")
        status_layout = QVBoxLayout(status_group)

        status_row = QHBoxLayout()
        status_label = QLabel("Status:")
        status_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        status_row.addWidget(status_label)

        self.status_value = QLabel("Not Connected")
        self.status_value.setStyleSheet("color: #f44336;")
        status_row.addWidget(self.status_value)
        status_row.addStretch()

        status_layout.addLayout(status_row)

        info_label = QLabel(
            "Bank API integration requires setting up credentials with a service like "
            "Plaid or Yodlee. This feature will allow automatic importing of:\n\n"
            "• Account balances (checking, savings)\n"
            "• Transaction history\n"
            "• Credit card statements\n"
            "• Real-time balance updates"
        )
        info_label.setWordWrap(True)
        status_layout.addWidget(info_label)

        layout.addWidget(status_group)

        # Actions section
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout(actions_group)

        connect_btn = QPushButton("Connect Bank Account")
        connect_btn.setEnabled(False)
        connect_btn.setToolTip("Requires API credentials - not yet configured")
        actions_layout.addWidget(connect_btn)

        sync_btn = QPushButton("Sync Transactions")
        sync_btn.setEnabled(False)
        sync_btn.setToolTip("Connect a bank account first")
        actions_layout.addWidget(sync_btn)

        settings_btn = QPushButton("API Settings")
        settings_btn.setEnabled(False)
        settings_btn.setToolTip("Configure API credentials")
        actions_layout.addWidget(settings_btn)

        actions_layout.addStretch()
        layout.addWidget(actions_group)

        # Connected accounts table (placeholder)
        accounts_group = QGroupBox("Connected Accounts")
        accounts_layout = QVBoxLayout(accounts_group)

        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(4)
        self.accounts_table.setHorizontalHeaderLabels([
            "Account", "Type", "Last Sync", "Status"
        ])
        self.accounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.accounts_table.setRowCount(0)

        # Add placeholder row
        self.accounts_table.setRowCount(1)
        self.accounts_table.setItem(0, 0, QTableWidgetItem("No accounts connected"))
        self.accounts_table.setItem(0, 1, QTableWidgetItem("-"))
        self.accounts_table.setItem(0, 2, QTableWidgetItem("-"))
        self.accounts_table.setItem(0, 3, QTableWidgetItem("-"))

        accounts_layout.addWidget(self.accounts_table)
        layout.addWidget(accounts_group)

        # Requirements note
        note = QLabel(
            "Note: To enable bank API integration, you will need to:\n"
            "1. Create an account with Plaid (plaid.com) or Yodlee\n"
            "2. Obtain API credentials (client ID and secret)\n"
            "3. Configure credentials in application settings\n\n"
            "This is a future feature (TODO 9.10)."
        )
        note.setStyleSheet("color: #666; font-style: italic;")
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addStretch()

    def refresh(self):
        """Placeholder refresh method"""
        pass
