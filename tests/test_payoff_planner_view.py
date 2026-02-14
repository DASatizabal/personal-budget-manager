"""Unit tests for Payoff Planner view"""

import pytest
from PyQt6.QtGui import QColor


class TestPayoffPlannerView:
    """Tests for PayoffPlannerView"""

    def test_no_cards_empty_table_and_message(self, qtbot, temp_db):
        """No cards: empty comparison table and 'No credit card balances' message"""
        from budget_app.views.payoff_planner_view import PayoffPlannerView
        view = PayoffPlannerView()
        qtbot.addWidget(view)
        assert view.comparison_table.rowCount() == 0
        assert "No credit card balances to pay off." in view.details_text.toPlainText()

    def test_summary_labels_no_cards(self, qtbot, temp_db):
        """Summary labels show zeros when no cards exist"""
        from budget_app.views.payoff_planner_view import PayoffPlannerView
        view = PayoffPlannerView()
        qtbot.addWidget(view)
        assert "$0.00" in view.total_debt_label.text()
        assert "$0.00" in view.total_min_label.text()
        assert "Cards with Balance: 0" in view.cards_count_label.text()

    def test_summary_labels_with_multiple_cards(self, qtbot, temp_db, multiple_cards):
        """Summary labels show correct totals with multiple cards"""
        from budget_app.views.payoff_planner_view import PayoffPlannerView
        view = PayoffPlannerView()
        qtbot.addWidget(view)
        # Cards with balance > 0: Chase $3000, Amex $4500, Discover $3200
        # Citi has $0 balance so get_cards_from_database excludes it
        assert "$10,700.00" in view.total_debt_label.text()
        assert "Cards with Balance: 3" in view.cards_count_label.text()

    def test_comparison_table_populates_with_strategies(self, qtbot, temp_db, sample_card):
        """Comparison table should populate with strategy rows when cards exist"""
        from budget_app.views.payoff_planner_view import PayoffPlannerView
        view = PayoffPlannerView()
        qtbot.addWidget(view)
        # Should have at least 5 strategies (Avalanche, Snowball, Hybrid, High Utilization, Cash on Hand)
        assert view.comparison_table.rowCount() >= 5
        # Verify method names appear in the table
        method_names = set()
        for row in range(view.comparison_table.rowCount()):
            method_names.add(view.comparison_table.item(row, 0).text())
        assert 'Avalanche' in method_names
        assert 'Snowball' in method_names
        assert 'Cash on Hand' in method_names

    def test_comparison_table_has_six_columns(self, qtbot, temp_db, sample_card):
        """Comparison table should have 6 columns"""
        from budget_app.views.payoff_planner_view import PayoffPlannerView
        view = PayoffPlannerView()
        qtbot.addWidget(view)
        assert view.comparison_table.columnCount() == 6
        expected_headers = [
            "Method", "Payoff Date", "Months", "Total Interest",
            "Total Paid", "Avg Monthly"
        ]
        for i, label in enumerate(expected_headers):
            assert view.comparison_table.horizontalHeaderItem(i).text() == label

    def test_first_row_colored_green(self, qtbot, temp_db, sample_card):
        """First row (best method) should be colored green (#4caf50)"""
        from budget_app.views.payoff_planner_view import PayoffPlannerView
        view = PayoffPlannerView()
        qtbot.addWidget(view)
        assert view.comparison_table.rowCount() > 0
        green = QColor("#4caf50")
        for col in range(view.comparison_table.columnCount()):
            item = view.comparison_table.item(0, col)
            assert item is not None
            assert item.foreground().color() == green

    def test_extra_payment_spin_default(self, qtbot, temp_db):
        """Extra payment spin should default to $100"""
        from budget_app.views.payoff_planner_view import PayoffPlannerView
        view = PayoffPlannerView()
        qtbot.addWidget(view)
        assert view.extra_payment_spin.value() == 100

    def test_details_text_shows_strategy_and_payoff_order(self, qtbot, temp_db, multiple_cards):
        """Details text should show strategy name and card payoff order"""
        from budget_app.views.payoff_planner_view import PayoffPlannerView
        view = PayoffPlannerView()
        qtbot.addWidget(view)
        # The first row is auto-selected on calculate, triggering _show_details
        assert len(view.results) > 0
        assert view.selected_result is not None
        details = view.details_text.toPlainText()
        # Details should contain the strategy name
        assert view.selected_result.method in details
        # Details should contain card payoff order section
        assert "Card Payoff Order:" in details
        # At least one card name should appear in payoff order
        for card_name in view.selected_result.card_payoff_order:
            assert card_name in details

    def test_details_label_shows_strategy_name(self, qtbot, temp_db, sample_card):
        """Details label should show the selected strategy name"""
        from budget_app.views.payoff_planner_view import PayoffPlannerView
        view = PayoffPlannerView()
        qtbot.addWidget(view)
        assert view.selected_result is not None
        expected = f"{view.selected_result.method} Strategy Details"
        assert view.details_label.text() == expected

    def test_interest_savings_vs_baseline(self, qtbot, temp_db, multiple_cards):
        """_get_interest_savings_vs_baseline should return correct savings"""
        from budget_app.views.payoff_planner_view import PayoffPlannerView
        view = PayoffPlannerView()
        qtbot.addWidget(view)
        assert len(view.results) >= 2
        # Find the Cash on Hand baseline
        baseline = next((r for r in view.results if r.method == "Cash on Hand"), None)
        assert baseline is not None
        # The best result (first) should have savings >= 0
        best = view.results[0]
        savings = view._get_interest_savings_vs_baseline(best)
        expected = baseline.total_interest - best.total_interest
        assert savings == pytest.approx(expected)
        assert savings >= 0

    def test_interest_savings_no_results(self, qtbot, temp_db):
        """_get_interest_savings_vs_baseline returns 0 when no results exist"""
        from budget_app.views.payoff_planner_view import PayoffPlannerView
        view = PayoffPlannerView()
        qtbot.addWidget(view)
        # No cards, so results should be empty
        assert len(view.results) == 0
        from budget_app.utils.payoff_calculator import PayoffResult
        from datetime import date
        dummy = PayoffResult(
            method="Dummy", method_description="", payoff_date=date.today(),
            months_to_payoff=0, total_interest=0, total_payments=0,
            monthly_payment_avg=0, payment_schedule=[], card_payoff_order=[]
        )
        savings = view._get_interest_savings_vs_baseline(dummy)
        assert savings == 0

    def test_results_stored_after_calculate(self, qtbot, temp_db, sample_card):
        """self.results should be populated after _calculate()"""
        from budget_app.views.payoff_planner_view import PayoffPlannerView
        view = PayoffPlannerView()
        qtbot.addWidget(view)
        assert len(view.results) == 5
        for result in view.results:
            assert result.method != ""
            assert result.months_to_payoff > 0

    def test_on_selection_changed_updates_selected_result(self, qtbot, temp_db, multiple_cards):
        """Selecting a different row updates selected_result"""
        from budget_app.views.payoff_planner_view import PayoffPlannerView
        view = PayoffPlannerView()
        qtbot.addWidget(view)
        assert view.comparison_table.rowCount() >= 2
        # Select second row
        view.comparison_table.selectRow(1)
        assert view.selected_result == view.results[1]
        assert view.selected_result.method in view.details_label.text()
