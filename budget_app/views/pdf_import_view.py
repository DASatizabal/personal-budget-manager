"""PDF Import placeholder view"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class PDFImportView(QWidget):
    """Placeholder view for PDF import features (paystubs and CC statements)"""

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        """Set up the placeholder UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Header
        header = QLabel("PDF Import")
        header.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        subtitle = QLabel("Coming Soon")
        subtitle.setFont(QFont("Segoe UI", 14))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #888;")
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Paystub section
        paystub_group = QGroupBox("Paycheck/Paystub Parsing (9.6)")
        paystub_layout = QVBoxLayout(paystub_group)

        paystub_desc = QLabel(
            "Upload PDF paystubs to automatically extract:\n"
            "• Gross pay and net pay amounts\n"
            "• Tax withholdings (Federal, State, Local)\n"
            "• Deductions (401k, insurance, etc.)\n"
            "• Pay period dates"
        )
        paystub_desc.setWordWrap(True)
        paystub_layout.addWidget(paystub_desc)

        paystub_btn = QPushButton("Upload Paystub PDF")
        paystub_btn.setEnabled(False)
        paystub_btn.setToolTip("Feature not yet implemented")
        paystub_layout.addWidget(paystub_btn)

        layout.addWidget(paystub_group)

        # CC Statement section
        cc_group = QGroupBox("Credit Card Statement Parsing (9.7)")
        cc_layout = QVBoxLayout(cc_group)

        cc_desc = QLabel(
            "Upload credit card statements (PDF or CSV) to:\n"
            "• Import transaction history\n"
            "• Reconcile against projected transactions\n"
            "• Update current balances automatically\n"
            "• Categorize expenses"
        )
        cc_desc.setWordWrap(True)
        cc_layout.addWidget(cc_desc)

        cc_btn = QPushButton("Upload Statement")
        cc_btn.setEnabled(False)
        cc_btn.setToolTip("Feature not yet implemented")
        cc_layout.addWidget(cc_btn)

        layout.addWidget(cc_group)

        # Drop zone placeholder
        drop_frame = QFrame()
        drop_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        drop_frame.setMinimumHeight(100)
        drop_layout = QVBoxLayout(drop_frame)

        drop_label = QLabel("Drag and drop PDF files here\n(Not yet functional)")
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_label.setStyleSheet("color: #666;")
        drop_layout.addWidget(drop_label)

        layout.addWidget(drop_frame)

        layout.addStretch()

    def refresh(self):
        """Placeholder refresh method"""
        pass
