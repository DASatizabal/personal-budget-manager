"""Unit tests for PostedTransactionsView"""

import pytest
from PyQt6.QtGui import QColor


class TestPostedTransactionsView:
    """Tests for PostedTransactionsView"""

    def test_empty_render_no_refresh_in_init(self, qtbot, temp_db):
        """__init__ sets _data_dirty=True but does NOT call refresh, so table is empty"""
        from budget_app.views.posted_transactions_view import PostedTransactionsView
        view = PostedTransactionsView()
        qtbot.addWidget(view)
        assert view._data_dirty is True
        assert view.table.rowCount() == 0

    def test_mark_dirty_sets_flag(self, qtbot, temp_db):
        """mark_dirty() sets _data_dirty to True"""
        from budget_app.views.posted_transactions_view import PostedTransactionsView
        view = PostedTransactionsView()
        qtbot.addWidget(view)
        # Calling refresh clears the flag
        view.refresh()
        assert view._data_dirty is False
        view.mark_dirty()
        assert view._data_dirty is True

    def test_refresh_populates_posted_transactions(self, qtbot, temp_db, sample_transactions):
        """After calling refresh(), posted transactions populate the table"""
        from budget_app.views.posted_transactions_view import PostedTransactionsView
        view = PostedTransactionsView()
        qtbot.addWidget(view)
        view.refresh()
        # sample_transactions has exactly 1 posted transaction ('Old Payment')
        assert view.table.rowCount() == 1
        assert view.table.item(0, 3).text() == 'Old Payment'

    def test_refresh_skips_when_not_dirty(self, qtbot, temp_db, sample_transactions):
        """refresh() returns early if _data_dirty is False (no-op)"""
        from budget_app.views.posted_transactions_view import PostedTransactionsView
        view = PostedTransactionsView()
        qtbot.addWidget(view)
        view.refresh()
        assert view.table.rowCount() == 1
        # Clear the table manually, then call refresh again without marking dirty
        view.table.setRowCount(0)
        view.refresh()  # Should be a no-op since _data_dirty is False
        assert view.table.rowCount() == 0

    def test_date_format_conversion(self, qtbot, temp_db, sample_transactions):
        """ISO 'YYYY-MM-DD' dates are displayed as 'MM/DD/YYYY'"""
        from budget_app.views.posted_transactions_view import PostedTransactionsView
        view = PostedTransactionsView()
        qtbot.addWidget(view)
        view.refresh()
        # The posted transaction: date='2026-01-15', posted_date='2026-01-20'
        due_date_text = view.table.item(0, 0).text()
        posted_date_text = view.table.item(0, 1).text()
        assert due_date_text == '01/15/2026'
        assert posted_date_text == '01/20/2026'

    def test_amount_color_negative_red(self, qtbot, temp_db, sample_transactions):
        """Negative amounts are displayed in red (#f44336)"""
        from budget_app.views.posted_transactions_view import PostedTransactionsView
        view = PostedTransactionsView()
        qtbot.addWidget(view)
        view.refresh()
        # 'Old Payment' has amount=-200.0 (negative)
        amount_item = view.table.item(0, 4)
        assert amount_item.foreground().color() == QColor("#f44336")

    def test_amount_color_positive_green(self, qtbot, temp_db):
        """Positive amounts are displayed in green (#4caf50)"""
        from budget_app.models.transaction import Transaction
        from budget_app.views.posted_transactions_view import PostedTransactionsView
        # Create a posted transaction with a positive amount
        t = Transaction(
            id=None, date='2026-02-01', description='Refund',
            amount=500.0, payment_method='C',
            is_posted=True, posted_date='2026-02-05'
        )
        t.save()
        view = PostedTransactionsView()
        qtbot.addWidget(view)
        view.refresh()
        amount_item = view.table.item(0, 4)
        assert amount_item.foreground().color() == QColor("#4caf50")

    def test_info_label_shows_count(self, qtbot, temp_db, sample_transactions):
        """info_label displays 'Showing N posted transaction(s)'"""
        from budget_app.views.posted_transactions_view import PostedTransactionsView
        view = PostedTransactionsView()
        qtbot.addWidget(view)
        view.refresh()
        assert view.info_label.text() == "Showing 1 posted transaction(s)"

    def test_description_filter_hides_non_matching_rows(self, qtbot, temp_db):
        """Typing in desc_filter hides rows that don't match (case-insensitive)"""
        from budget_app.models.transaction import Transaction
        from budget_app.views.posted_transactions_view import PostedTransactionsView
        # Create two posted transactions
        Transaction(
            id=None, date='2026-01-10', description='Grocery Store',
            amount=-75.0, payment_method='C',
            is_posted=True, posted_date='2026-01-12'
        ).save()
        Transaction(
            id=None, date='2026-01-11', description='Electric Bill',
            amount=-120.0, payment_method='C',
            is_posted=True, posted_date='2026-01-13'
        ).save()
        view = PostedTransactionsView()
        qtbot.addWidget(view)
        view.refresh()
        assert view.table.rowCount() == 2
        # Filter by "grocery" (case-insensitive)
        view.desc_filter.setText("grocery")
        # One row should be visible, the other hidden
        visible_count = sum(
            1 for r in range(view.table.rowCount())
            if not view.table.isRowHidden(r)
        )
        assert visible_count == 1
        # The visible row should be 'Grocery Store'
        for r in range(view.table.rowCount()):
            if not view.table.isRowHidden(r):
                assert view.table.item(r, 3).text() == 'Grocery Store'

    def test_clear_filters_restores_all_rows(self, qtbot, temp_db):
        """_clear_filters() resets desc_filter and pay_type_filter, unhides all rows"""
        from budget_app.models.transaction import Transaction
        from budget_app.views.posted_transactions_view import PostedTransactionsView
        Transaction(
            id=None, date='2026-01-10', description='Grocery Store',
            amount=-75.0, payment_method='C',
            is_posted=True, posted_date='2026-01-12'
        ).save()
        Transaction(
            id=None, date='2026-01-11', description='Electric Bill',
            amount=-120.0, payment_method='C',
            is_posted=True, posted_date='2026-01-13'
        ).save()
        view = PostedTransactionsView()
        qtbot.addWidget(view)
        view.refresh()
        # Apply filter to hide some rows
        view.desc_filter.setText("grocery")
        hidden_before_clear = sum(
            1 for r in range(view.table.rowCount())
            if view.table.isRowHidden(r)
        )
        assert hidden_before_clear == 1
        # Clear filters
        view._clear_filters()
        assert view.desc_filter.text() == ""
        assert view.pay_type_filter.currentIndex() == 0
        hidden_after_clear = sum(
            1 for r in range(view.table.rowCount())
            if view.table.isRowHidden(r)
        )
        assert hidden_after_clear == 0

    def test_delete_no_selection_warns(self, qtbot, temp_db, mock_qmessagebox):
        """_delete_selected() with no selection shows a warning"""
        from budget_app.views.posted_transactions_view import PostedTransactionsView
        view = PostedTransactionsView()
        qtbot.addWidget(view)
        view._delete_selected()
        assert mock_qmessagebox.warning_called
        assert "Please select a transaction to delete" in mock_qmessagebox.warning_text

    def test_clear_all_with_no_posted_shows_info(self, qtbot, temp_db, mock_qmessagebox):
        """_clear_all_posted() when count==0 shows info 'There are no posted transactions.'"""
        from budget_app.views.posted_transactions_view import PostedTransactionsView
        view = PostedTransactionsView()
        qtbot.addWidget(view)
        view._clear_all_posted()
        assert mock_qmessagebox.info_called
        assert "There are no posted transactions." in mock_qmessagebox.info_text

    def test_table_has_six_columns(self, qtbot, temp_db):
        """Table should have 6 columns: Due Date, Posted Date, Pay Type, Description, Amount, Notes"""
        from budget_app.views.posted_transactions_view import PostedTransactionsView
        view = PostedTransactionsView()
        qtbot.addWidget(view)
        assert view.table.columnCount() == 6
        expected = ["Due Date", "Posted Date", "Pay Type", "Description", "Amount", "Notes"]
        for i, label in enumerate(expected):
            assert view.table.horizontalHeaderItem(i).text() == label


class TestPostedTransactionsViewAdditional:
    """Additional tests for PostedTransactionsView"""

    def test_multiple_posted_transactions_display(self, qtbot, temp_db):
        """Create 3 posted transactions, refresh, verify table has 3 rows"""
        from budget_app.models.transaction import Transaction
        from budget_app.views.posted_transactions_view import PostedTransactionsView

        for i, (date, desc, amount) in enumerate([
            ('2026-01-10', 'Rent Payment', -1200.0),
            ('2026-01-15', 'Grocery Store', -85.50),
            ('2026-01-20', 'Salary Deposit', 3000.0),
        ]):
            Transaction(
                id=None, date=date, description=desc,
                amount=amount, payment_method='C',
                is_posted=True, posted_date=f'2026-01-{22 + i}'
            ).save()

        view = PostedTransactionsView()
        qtbot.addWidget(view)
        view.refresh()
        assert view.table.rowCount() == 3

    def test_pay_type_filter_hides_non_matching(self, qtbot, temp_db):
        """Create posted transactions with different payment methods, filter by one type"""
        from budget_app.models.transaction import Transaction
        from budget_app.views.posted_transactions_view import PostedTransactionsView

        Transaction(
            id=None, date='2026-01-10', description='Bank Payment',
            amount=-100.0, payment_method='C',
            is_posted=True, posted_date='2026-01-12'
        ).save()
        Transaction(
            id=None, date='2026-01-11', description='Card Payment',
            amount=-50.0, payment_method='CH',
            is_posted=True, posted_date='2026-01-13'
        ).save()

        view = PostedTransactionsView()
        qtbot.addWidget(view)
        view.refresh()
        assert view.table.rowCount() == 2

        # The pay_type_filter combo has "All" at index 0, "Chase (Bank)" with data "C" at index 1.
        # Find the index with data == "C"
        for i in range(view.pay_type_filter.count()):
            if view.pay_type_filter.itemData(i) == "C":
                view.pay_type_filter.setCurrentIndex(i)
                break

        # Count visible rows - only the 'C' transaction should be visible
        visible_rows = [
            r for r in range(view.table.rowCount())
            if not view.table.isRowHidden(r)
        ]
        assert len(visible_rows) == 1
        assert view.table.item(visible_rows[0], 2).text() == 'C'

    def test_table_sorting_enabled(self, qtbot, temp_db):
        """Verify table.isSortingEnabled() is False (sorting is not explicitly enabled)"""
        from budget_app.views.posted_transactions_view import PostedTransactionsView

        view = PostedTransactionsView()
        qtbot.addWidget(view)
        assert view.table.isSortingEnabled() is False

    def test_notes_column_display(self, qtbot, temp_db):
        """Create a posted transaction with notes, verify notes appear in the last column"""
        from budget_app.models.transaction import Transaction
        from budget_app.views.posted_transactions_view import PostedTransactionsView

        Transaction(
            id=None, date='2026-02-01', description='Test Item',
            amount=-25.0, payment_method='C',
            is_posted=True, posted_date='2026-02-03',
            notes='Test note'
        ).save()

        view = PostedTransactionsView()
        qtbot.addWidget(view)
        view.refresh()
        assert view.table.rowCount() == 1
        # Notes is column index 5 (the last column)
        notes_item = view.table.item(0, 5)
        assert notes_item.text() == 'Test note'
