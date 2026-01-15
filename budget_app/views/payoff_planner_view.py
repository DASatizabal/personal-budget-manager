"""Credit Card Payoff Planner view"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QGroupBox, QLabel, QHeaderView, QSplitter,
    QTextEdit, QMessageBox, QFormLayout
)
from .widgets import MoneySpinBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from ..utils.payoff_calculator import (
    calculate_all_methods, get_cards_from_database, PayoffResult
)


class PayoffPlannerView(QWidget):
    """View for planning credit card payoff strategies"""

    def __init__(self):
        super().__init__()
        self.results: list[PayoffResult] = []
        self.selected_result: PayoffResult = None
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        """Set up the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header = QLabel("Credit Card Payoff Planner")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        layout.addWidget(header)

        subtitle = QLabel(
            "Compare different payoff strategies to find the best approach for your situation"
        )
        subtitle.setStyleSheet("color: #888;")
        layout.addWidget(subtitle)

        # Settings panel
        settings_group = QGroupBox("Settings")
        settings_layout = QFormLayout(settings_group)

        self.extra_payment_spin = MoneySpinBox()
        self.extra_payment_spin.setMinimum(0)
        self.extra_payment_spin.setMaximum(10000)
        self.extra_payment_spin.setValue(100)
        self.extra_payment_spin.setToolTip(
            "Extra amount available each month beyond minimum payments"
        )
        settings_layout.addRow("Monthly Extra Payment:", self.extra_payment_spin)

        calc_btn = QPushButton("Calculate Strategies")
        calc_btn.clicked.connect(self._calculate)
        settings_layout.addRow("", calc_btn)

        layout.addWidget(settings_group)

        # Create splitter for results and details
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Comparison table
        comparison_widget = QWidget()
        comparison_layout = QVBoxLayout(comparison_widget)
        comparison_layout.setContentsMargins(0, 0, 0, 0)

        comparison_label = QLabel("Strategy Comparison")
        comparison_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        comparison_layout.addWidget(comparison_label)

        self.comparison_table = QTableWidget()
        self.comparison_table.setColumnCount(6)
        self.comparison_table.setHorizontalHeaderLabels([
            "Method", "Payoff Date", "Months", "Total Interest",
            "Total Paid", "Avg Monthly"
        ])
        self.comparison_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for i in range(1, 6):
            self.comparison_table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.ResizeToContents
            )
        self.comparison_table.setAlternatingRowColors(True)
        self.comparison_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.comparison_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.comparison_table.itemSelectionChanged.connect(self._on_selection_changed)
        comparison_layout.addWidget(self.comparison_table)

        splitter.addWidget(comparison_widget)

        # Details panel
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)

        details_header = QHBoxLayout()
        self.details_label = QLabel("Select a strategy above to see details")
        self.details_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        details_header.addWidget(self.details_label)
        details_header.addStretch()
        details_layout.addLayout(details_header)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Consolas", 10))
        details_layout.addWidget(self.details_text)

        splitter.addWidget(details_widget)

        # Set splitter sizes (60% comparison, 40% details)
        splitter.setSizes([300, 200])
        layout.addWidget(splitter)

        # Summary bar at bottom
        summary_layout = QHBoxLayout()

        self.total_debt_label = QLabel()
        self.total_min_label = QLabel()
        self.cards_count_label = QLabel()

        summary_layout.addWidget(self.total_debt_label)
        summary_layout.addWidget(self.total_min_label)
        summary_layout.addWidget(self.cards_count_label)
        summary_layout.addStretch()

        layout.addLayout(summary_layout)

    def refresh(self):
        """Refresh the view with current data"""
        cards = get_cards_from_database()

        # Update summary
        total_debt = sum(c.balance for c in cards)
        total_min = sum(c.min_payment for c in cards)

        self.total_debt_label.setText(f"Total Debt: ${total_debt:,.2f}")
        self.total_min_label.setText(f"Total Minimums: ${total_min:,.2f}/mo")
        self.cards_count_label.setText(f"Cards with Balance: {len(cards)}")

        if cards:
            self._calculate()
        else:
            self.comparison_table.setRowCount(0)
            self.details_text.setPlainText("No credit card balances to pay off.")

    def _calculate(self):
        """Calculate all payoff strategies"""
        cards = get_cards_from_database()

        if not cards:
            QMessageBox.information(
                self,
                "No Balances",
                "No credit cards have balances to pay off."
            )
            return

        monthly_extra = self.extra_payment_spin.value()
        self.results = calculate_all_methods(cards, monthly_extra)

        # Populate comparison table
        self.comparison_table.setRowCount(len(self.results))

        for row, result in enumerate(self.results):
            # Method name
            method_item = QTableWidgetItem(result.method)
            method_item.setToolTip(result.method_description)
            self.comparison_table.setItem(row, 0, method_item)

            # Payoff date
            date_str = result.payoff_date.strftime("%b %Y")
            self.comparison_table.setItem(row, 1, QTableWidgetItem(date_str))

            # Months
            self.comparison_table.setItem(row, 2, QTableWidgetItem(str(result.months_to_payoff)))

            # Total interest
            interest_item = QTableWidgetItem(f"${result.total_interest:,.2f}")
            interest_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.comparison_table.setItem(row, 3, interest_item)

            # Total paid
            total_item = QTableWidgetItem(f"${result.total_payments:,.2f}")
            total_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.comparison_table.setItem(row, 4, total_item)

            # Average monthly
            avg_item = QTableWidgetItem(f"${result.monthly_payment_avg:,.2f}")
            avg_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.comparison_table.setItem(row, 5, avg_item)

            # Color coding: best method (first row) in green
            if row == 0:
                for col in range(self.comparison_table.columnCount()):
                    item = self.comparison_table.item(row, col)
                    if item:
                        item.setForeground(QColor("#4caf50"))

        # Select first row
        if self.results:
            self.comparison_table.selectRow(0)

    def _on_selection_changed(self):
        """Handle selection change in comparison table"""
        selected = self.comparison_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        if row < len(self.results):
            self.selected_result = self.results[row]
            self._show_details(self.selected_result)

    def _show_details(self, result: PayoffResult):
        """Show detailed breakdown for selected method"""
        self.details_label.setText(f"{result.method} Strategy Details")

        lines = []
        lines.append(f"Strategy: {result.method}")
        lines.append(f"Description: {result.method_description}")
        lines.append("")
        lines.append(f"Payoff Date: {result.payoff_date.strftime('%B %Y')}")
        lines.append(f"Time to Payoff: {result.months_to_payoff} months ({result.months_to_payoff / 12:.1f} years)")
        lines.append(f"Total Interest Paid: ${result.total_interest:,.2f}")
        lines.append(f"Total Amount Paid: ${result.total_payments:,.2f}")
        lines.append(f"Average Monthly Payment: ${result.monthly_payment_avg:,.2f}")
        lines.append("")

        # Card payoff order
        lines.append("Card Payoff Order:")
        for i, card_name in enumerate(result.card_payoff_order, 1):
            lines.append(f"  {i}. {card_name}")

        lines.append("")

        # Monthly breakdown summary (first 12 months)
        lines.append("Payment Schedule (First 12 Months):")
        lines.append("-" * 60)

        # Group payments by month
        monthly_totals = {}
        for entry in result.payment_schedule:
            month_key = entry.date.strftime("%Y-%m")
            if month_key not in monthly_totals:
                monthly_totals[month_key] = {
                    'date': entry.date,
                    'total': 0,
                    'interest': 0,
                    'principal': 0,
                    'cards': {}
                }
            monthly_totals[month_key]['total'] += entry.amount
            monthly_totals[month_key]['interest'] += entry.interest
            monthly_totals[month_key]['principal'] += entry.principal

            if entry.card_name not in monthly_totals[month_key]['cards']:
                monthly_totals[month_key]['cards'][entry.card_name] = 0
            monthly_totals[month_key]['cards'][entry.card_name] += entry.amount

        # Show first 12 months
        month_count = 0
        for month_key in sorted(monthly_totals.keys()):
            if month_count >= 12:
                break
            month_data = monthly_totals[month_key]
            date_str = month_data['date'].strftime("%b %Y")
            lines.append(
                f"{date_str}: ${month_data['total']:,.2f} "
                f"(Principal: ${month_data['principal']:,.2f}, "
                f"Interest: ${month_data['interest']:,.2f})"
            )

            # Show per-card breakdown
            for card_name, amount in month_data['cards'].items():
                lines.append(f"    {card_name}: ${amount:,.2f}")

            month_count += 1

        if len(monthly_totals) > 12:
            lines.append(f"... and {len(monthly_totals) - 12} more months")

        self.details_text.setPlainText("\n".join(lines))

    def _get_interest_savings_vs_baseline(self, result: PayoffResult) -> float:
        """Calculate interest savings compared to minimum-only payments"""
        if not self.results:
            return 0

        # Find cash-on-hand (minimum only) result
        baseline = next((r for r in self.results if r.method == "Cash on Hand"), None)
        if baseline:
            return baseline.total_interest - result.total_interest
        return 0
