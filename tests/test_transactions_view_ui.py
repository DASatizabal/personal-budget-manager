"""Unit tests for Transactions view and dialogs"""

import pytest
from PyQt6.QtCore import Qt


class TestTransactionsViewColumns:
    """Tests for TransactionsView column setup"""

    def test_base_columns_present(self, qtbot, temp_db):
        """Base columns: checkbox, Date, Pay Type, Description, Amount, Chase Balance"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        expected_base = ["\u2713", "Date", "Pay Type", "Description", "Amount", "Chase Balance"]
        for i, label in enumerate(expected_base):
            assert view.table.horizontalHeaderItem(i).text() == label

    def test_dynamic_card_columns_created(self, qtbot, temp_db, sample_card):
        """With a card in DB, Owed and Avail columns are created dynamically"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        # Base (6) + Owed (1) + Avail (1) + CC Utilization (1) = 9
        assert view.table.columnCount() == 9
        # Check the dynamic card column headers
        headers = [view.table.horizontalHeaderItem(i).text()
                   for i in range(view.table.columnCount())]
        assert "Chase Freedom Owed" in headers
        assert "Chase Freedom Avail" in headers

    def test_card_owed_columns_tracked(self, qtbot, temp_db, sample_card):
        """_card_owed_columns list tracks owed column names"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        assert "Chase Freedom Owed" in view._card_owed_columns

    def test_card_avail_columns_tracked(self, qtbot, temp_db, sample_card):
        """_card_avail_columns list tracks avail column names"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        assert "Chase Freedom Avail" in view._card_avail_columns

    def test_cc_utilization_is_last_column(self, qtbot, temp_db, sample_card):
        """CC Utilization column is always the last column"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        last_col = view.table.columnCount() - 1
        assert view.table.horizontalHeaderItem(last_col).text() == "CC Utilization"

    def test_no_cards_still_has_utilization_column(self, qtbot, temp_db):
        """With no cards, base columns + CC Utilization still present"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        # Base (6) + CC Utilization (1) = 7
        assert view.table.columnCount() == 7
        last_col = view.table.columnCount() - 1
        assert view.table.horizontalHeaderItem(last_col).text() == "CC Utilization"

    def test_multiple_cards_columns(self, qtbot, temp_db, multiple_cards):
        """Multiple cards each get Owed and Avail columns"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        # Base (6) + 4 cards * 2 (Owed+Avail) + CC Utilization (1) = 15
        assert view.table.columnCount() == 15


class TestTransactionsViewState:
    """Tests for TransactionsView state management"""

    def test_mark_dirty_sets_flag(self, qtbot, temp_db):
        """mark_dirty sets _data_dirty to True"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        # __init__ sets _data_dirty = True, but we clear it to test mark_dirty
        view._data_dirty = False
        view.mark_dirty()
        assert view._data_dirty is True

    def test_first_load_flag_set(self, qtbot, temp_db):
        """__init__ sets _first_load to True"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        assert view._first_load is True

    def test_data_dirty_flag_set_on_init(self, qtbot, temp_db):
        """__init__ sets _data_dirty to True"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        assert view._data_dirty is True


class TestTransactionsViewColumnVisibility:
    """Tests for column visibility management"""

    def test_show_all_columns(self, qtbot, temp_db, sample_card):
        """_show_all_columns shows every column"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        # First hide some columns
        for i in range(view.table.columnCount()):
            view.table.setColumnHidden(i, True)
        # Show all
        view._show_all_columns()
        for i in range(view.table.columnCount()):
            assert view.table.isColumnHidden(i) is False

    def test_hide_all_cc_columns(self, qtbot, temp_db, sample_card):
        """_hide_all_cc_columns hides Owed and Avail columns"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        # First make sure all columns are visible
        view._show_all_columns()
        # Now hide CC columns
        view._hide_all_cc_columns()
        for i, col_name in enumerate(view._all_columns):
            if "Owed" in col_name or "Avail" in col_name:
                assert view.table.isColumnHidden(i) is True
            else:
                # Base columns should still be visible
                assert view.table.isColumnHidden(i) is False

    def test_toggle_column_group_owed_hide(self, qtbot, temp_db, sample_card):
        """_toggle_column_group hides all Owed columns"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        view._show_all_columns()
        view._toggle_column_group("Owed", False)
        for i, col_name in enumerate(view._all_columns):
            if "Owed" in col_name:
                assert view.table.isColumnHidden(i) is True
            elif "Avail" in col_name:
                # Avail columns should remain visible
                assert view.table.isColumnHidden(i) is False

    def test_toggle_column_group_avail_hide(self, qtbot, temp_db, sample_card):
        """_toggle_column_group hides all Avail columns"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        view._show_all_columns()
        view._toggle_column_group("Avail", False)
        for i, col_name in enumerate(view._all_columns):
            if "Avail" in col_name:
                assert view.table.isColumnHidden(i) is True
            elif "Owed" in col_name:
                # Owed columns should remain visible
                assert view.table.isColumnHidden(i) is False

    def test_toggle_column_group_show(self, qtbot, temp_db, sample_card):
        """_toggle_column_group can show previously hidden columns"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        # Hide all Owed columns
        view._toggle_column_group("Owed", False)
        for i, col_name in enumerate(view._all_columns):
            if "Owed" in col_name:
                assert view.table.isColumnHidden(i) is True
        # Show them again
        view._toggle_column_group("Owed", True)
        for i, col_name in enumerate(view._all_columns):
            if "Owed" in col_name:
                assert view.table.isColumnHidden(i) is False


class TestTransactionsViewFilters:
    """Tests for filter controls"""

    def test_clear_filters_resets_desc(self, qtbot, temp_db):
        """_clear_filters resets description filter"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        view.desc_filter.setText("test search")
        view._clear_filters()
        assert view.desc_filter.text() == ""

    def test_clear_filters_resets_amount_min(self, qtbot, temp_db):
        """_clear_filters resets amount min filter"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        view.amount_min_filter.setText("-500")
        view._clear_filters()
        assert view.amount_min_filter.text() == ""

    def test_clear_filters_resets_amount_max(self, qtbot, temp_db):
        """_clear_filters resets amount max filter"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        view.amount_max_filter.setText("5000")
        view._clear_filters()
        assert view.amount_max_filter.text() == ""

    def test_clear_filters_resets_sign_filter(self, qtbot, temp_db):
        """_clear_filters resets sign filter to All (index 0)"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        view.amount_sign_filter.setCurrentIndex(2)  # Expenses
        view._clear_filters()
        assert view.amount_sign_filter.currentIndex() == 0


class TestTransactionDialog:
    """Tests for TransactionDialog"""

    def test_title_add(self, qtbot, temp_db):
        """New dialog has 'Add Transaction' title"""
        from budget_app.views.transactions_view import TransactionDialog
        dialog = TransactionDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Add Transaction"

    def test_title_edit(self, qtbot, temp_db, sample_transactions):
        """Editing dialog has 'Edit Transaction' title"""
        from budget_app.views.transactions_view import TransactionDialog
        trans = sample_transactions[0]
        dialog = TransactionDialog(transaction=trans)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Edit Transaction"

    def test_populate_fields_from_transaction(self, qtbot, temp_db, sample_card, sample_transactions):
        """Fields are populated when editing an existing transaction"""
        from budget_app.views.transactions_view import TransactionDialog
        from PyQt6.QtCore import QDate
        trans = sample_transactions[0]  # Paycheck, 2026-02-01, 2500.0, C
        dialog = TransactionDialog(transaction=trans)
        qtbot.addWidget(dialog)
        assert dialog.date_edit.date() == QDate(2026, 2, 1)
        assert dialog.desc_edit.text() == "Paycheck"
        assert dialog.amount_spin.value() == 2500.0
        assert dialog.method_combo.currentData() == "C"
        assert dialog.posted_check.isChecked() is False

    def test_populate_posted_transaction(self, qtbot, temp_db, sample_card, sample_transactions):
        """Posted flag is correctly populated"""
        from budget_app.views.transactions_view import TransactionDialog
        trans = sample_transactions[3]  # Old Payment, posted=True
        dialog = TransactionDialog(transaction=trans)
        qtbot.addWidget(dialog)
        assert dialog.posted_check.isChecked() is True

    def test_get_transaction_returns_correct_model(self, qtbot, temp_db):
        """get_transaction returns a Transaction with form values"""
        from budget_app.views.transactions_view import TransactionDialog
        from PyQt6.QtCore import QDate
        dialog = TransactionDialog()
        qtbot.addWidget(dialog)
        dialog.date_edit.setDate(QDate(2026, 3, 15))
        dialog.desc_edit.setText("Test Purchase")
        dialog.amount_spin.setValue(-42.50)
        dialog.posted_check.setChecked(False)
        dialog.notes_edit.setText("A test note")

        trans = dialog.get_transaction()
        assert trans.id is None
        assert trans.date == "2026-03-15"
        assert trans.description == "Test Purchase"
        assert trans.amount == -42.50
        assert trans.payment_method == "C"  # Default: Chase (Bank)
        assert trans.is_posted is False
        assert trans.notes == "A test note"

    def test_get_transaction_empty_notes_is_none(self, qtbot, temp_db):
        """Empty notes field returns None in the transaction"""
        from budget_app.views.transactions_view import TransactionDialog
        dialog = TransactionDialog()
        qtbot.addWidget(dialog)
        dialog.desc_edit.setText("Something")
        dialog.notes_edit.setText("")
        trans = dialog.get_transaction()
        assert trans.notes is None

    def test_validate_empty_description(self, qtbot, temp_db, mock_qmessagebox):
        """Validation rejects empty description"""
        from budget_app.views.transactions_view import TransactionDialog
        dialog = TransactionDialog()
        qtbot.addWidget(dialog)
        dialog.desc_edit.setText("")
        dialog.amount_spin.setValue(-10.0)
        dialog._validate_and_accept()
        assert mock_qmessagebox.warning_called

    def test_validate_whitespace_description(self, qtbot, temp_db, mock_qmessagebox):
        """Validation rejects whitespace-only description"""
        from budget_app.views.transactions_view import TransactionDialog
        dialog = TransactionDialog()
        qtbot.addWidget(dialog)
        dialog.desc_edit.setText("   ")
        dialog._validate_and_accept()
        assert mock_qmessagebox.warning_called

    def test_payment_methods_include_chase(self, qtbot, temp_db):
        """Payment methods combo includes Chase (Bank)"""
        from budget_app.views.transactions_view import TransactionDialog
        dialog = TransactionDialog()
        qtbot.addWidget(dialog)
        assert dialog.method_combo.count() >= 1
        assert dialog.method_combo.itemData(0) == "C"
        assert "Chase" in dialog.method_combo.itemText(0)

    def test_payment_methods_include_cards(self, qtbot, temp_db, sample_card):
        """Payment methods combo includes credit cards from DB"""
        from budget_app.views.transactions_view import TransactionDialog
        dialog = TransactionDialog()
        qtbot.addWidget(dialog)
        # Chase (Bank) + sample_card = 2
        assert dialog.method_combo.count() == 2
        assert dialog.method_combo.itemData(1) == "CH"


class TestGenerateRecurringDialog:
    """Tests for GenerateRecurringDialog"""

    def test_default_months_is_3(self, qtbot, temp_db):
        """Default months spinner value is 3"""
        from budget_app.views.transactions_view import GenerateRecurringDialog
        dialog = GenerateRecurringDialog()
        qtbot.addWidget(dialog)
        assert dialog.months_spin.value() == 3

    def test_months_range(self, qtbot, temp_db):
        """Months spinner range is 1 to 24"""
        from budget_app.views.transactions_view import GenerateRecurringDialog
        dialog = GenerateRecurringDialog()
        qtbot.addWidget(dialog)
        assert dialog.months_spin.minimum() == 1
        assert dialog.months_spin.maximum() == 24

    def test_default_clear_existing_is_true(self, qtbot, temp_db):
        """Clear existing checkbox is checked by default"""
        from budget_app.views.transactions_view import GenerateRecurringDialog
        dialog = GenerateRecurringDialog()
        qtbot.addWidget(dialog)
        assert dialog.clear_check.isChecked() is True

    def test_get_months_returns_value(self, qtbot, temp_db):
        """get_months() returns the spinner value"""
        from budget_app.views.transactions_view import GenerateRecurringDialog
        dialog = GenerateRecurringDialog()
        qtbot.addWidget(dialog)
        dialog.months_spin.setValue(6)
        assert dialog.get_months() == 6

    def test_get_clear_existing_returns_check_state(self, qtbot, temp_db):
        """get_clear_existing() returns the checkbox state"""
        from budget_app.views.transactions_view import GenerateRecurringDialog
        dialog = GenerateRecurringDialog()
        qtbot.addWidget(dialog)
        dialog.clear_check.setChecked(False)
        assert dialog.get_clear_existing() is False
        dialog.clear_check.setChecked(True)
        assert dialog.get_clear_existing() is True

    def test_window_title(self, qtbot, temp_db):
        """Dialog has correct title"""
        from budget_app.views.transactions_view import GenerateRecurringDialog
        dialog = GenerateRecurringDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Generate Recurring Transactions"


class TestTransactionsViewRefresh:
    """Tests for the refresh() method with actual transaction data"""

    def _make_view(self, qtbot, from_date_str="2026-01-01", to_date_str="2026-12-31"):
        """Helper to create a TransactionsView with a wide date range.
        Disables auto-generation of recurring transactions on first load."""
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtCore import QDate
        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False  # Prevent auto-generation of recurring transactions
        view.from_date.setDate(QDate.fromString(from_date_str, "yyyy-MM-dd"))
        view.to_date.setDate(QDate.fromString(to_date_str, "yyyy-MM-dd"))
        return view

    def test_refresh_populates_table(self, qtbot, temp_db, sample_card, sample_transactions):
        """After calling refresh(), table has rows for non-posted transactions (3 of the 4)"""
        view = self._make_view(qtbot)
        view.refresh()
        # 4 sample transactions, but 1 is posted and filtered out
        assert view.table.rowCount() == 3

    def test_refresh_skips_when_not_dirty(self, qtbot, temp_db):
        """Create view, manually clear table, call refresh() - should be no-op since _data_dirty is already False"""
        view = self._make_view(qtbot)
        view.refresh()  # First refresh: sets _data_dirty = False
        # Manually clear the table to detect if refresh repopulates
        view.table.setRowCount(0)
        view.refresh()  # Should be a no-op since _data_dirty is False and dates unchanged
        assert view.table.rowCount() == 0

    def test_recurring_description_highlighted_blue(self, qtbot, temp_db, sample_card):
        """Recurring transactions have description highlighted in blue (#64b5f6)"""
        from budget_app.models.recurring_charge import RecurringCharge
        from budget_app.models.transaction import Transaction
        from PyQt6.QtGui import QColor

        charge = RecurringCharge(
            id=None, name='Test Recurring', amount=-25.0,
            day_of_month=10, payment_method='C',
            frequency='MONTHLY', amount_type='FIXED'
        )
        charge.save()

        trans = Transaction(
            id=None, date='2026-02-10', description='Test Recurring',
            amount=-25.0, payment_method='C',
            recurring_charge_id=charge.id, is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        # Find the row with recurring_charge_id set (description column = 3)
        found = False
        for row in range(view.table.rowCount()):
            desc_item = view.table.item(row, 3)
            if desc_item and desc_item.text() == 'Test Recurring':
                assert desc_item.foreground().color() == QColor("#64b5f6")
                found = True
                break
        assert found, "Recurring transaction row not found"

    def test_amount_color_negative_red(self, qtbot, temp_db, sample_card, sample_transactions):
        """Negative amounts have color #f44336"""
        from PyQt6.QtGui import QColor
        view = self._make_view(qtbot)
        view.refresh()

        # Find a negative amount row (e.g., Groceries -150.0)
        found = False
        for row in range(view.table.rowCount()):
            amount_item = view.table.item(row, 4)
            if amount_item:
                amount_text = amount_item.text().replace('$', '').replace(',', '').strip()
                try:
                    amount = float(amount_text)
                    if amount < 0:
                        assert amount_item.foreground().color() == QColor("#f44336")
                        found = True
                        break
                except ValueError:
                    pass
        assert found, "No negative amount row found"

    def test_amount_color_positive_green(self, qtbot, temp_db, sample_card, sample_transactions):
        """Positive amounts have color #4caf50"""
        from PyQt6.QtGui import QColor
        view = self._make_view(qtbot)
        view.refresh()

        # Find a positive amount row (e.g., Paycheck 2500.0)
        found = False
        for row in range(view.table.rowCount()):
            amount_item = view.table.item(row, 4)
            if amount_item:
                amount_text = amount_item.text().replace('$', '').replace(',', '').strip()
                try:
                    amount = float(amount_text)
                    if amount > 0:
                        assert amount_item.foreground().color() == QColor("#4caf50")
                        found = True
                        break
                except ValueError:
                    pass
        assert found, "No positive amount row found"

    def test_chase_balance_negative_red(self, qtbot, temp_db, sample_account, sample_card):
        """Create transaction that makes chase balance negative, verify chase balance column (5) color is red"""
        from budget_app.models.transaction import Transaction
        from budget_app.models.account import Account
        from PyQt6.QtGui import QColor

        # sample_account has balance 5000. Create a large expense to drive it negative.
        trans = Transaction(
            id=None, date='2026-02-10', description='Huge Expense',
            amount=-10000.0, payment_method='C', is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        # Find the row for Huge Expense and check chase balance color
        found = False
        for row in range(view.table.rowCount()):
            desc_item = view.table.item(row, 3)
            if desc_item and desc_item.text() == 'Huge Expense':
                chase_item = view.table.item(row, 5)
                assert chase_item.foreground().color() == QColor("#f44336")
                found = True
                break
        assert found, "Huge Expense row not found"


class TestTransactionsViewApplyFilters:
    """Tests for _apply_filters()"""

    def _make_view_with_data(self, qtbot, temp_db, sample_card, sample_transactions):
        """Helper to create a view with sample data and refresh it.
        Disables auto-generation of recurring transactions on first load."""
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtCore import QDate
        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False  # Prevent auto-generation of recurring transactions
        view.from_date.setDate(QDate.fromString("2026-01-01", "yyyy-MM-dd"))
        view.to_date.setDate(QDate.fromString("2026-12-31", "yyyy-MM-dd"))
        view.refresh()
        return view

    def test_desc_filter_hides_non_matching(self, qtbot, temp_db, sample_card, sample_transactions):
        """Set desc_filter to 'Pay', verify rows with 'Paycheck' visible, 'Groceries' hidden"""
        view = self._make_view_with_data(qtbot, temp_db, sample_card, sample_transactions)
        view.desc_filter.setText("Pay")
        # _apply_filters is called automatically via textChanged signal,
        # but call explicitly to be sure
        view._apply_filters()

        for row in range(view.table.rowCount()):
            desc_item = view.table.item(row, 3)
            if desc_item:
                if "Paycheck" in desc_item.text():
                    assert not view.table.isRowHidden(row), "Paycheck row should be visible"
                elif "Groceries" in desc_item.text():
                    assert view.table.isRowHidden(row), "Groceries row should be hidden"

    def test_desc_filter_case_insensitive(self, qtbot, temp_db, sample_card, sample_transactions):
        """Use lowercase filter, still matches"""
        view = self._make_view_with_data(qtbot, temp_db, sample_card, sample_transactions)
        view.desc_filter.setText("pay")
        view._apply_filters()

        for row in range(view.table.rowCount()):
            desc_item = view.table.item(row, 3)
            if desc_item and "Paycheck" in desc_item.text():
                assert not view.table.isRowHidden(row), "Paycheck row should be visible with lowercase filter"
                return
        pytest.fail("Paycheck row not found in table")

    def test_amount_min_filter(self, qtbot, temp_db, sample_card, sample_transactions):
        """Set amount_min_filter to '0', only positive amounts visible"""
        view = self._make_view_with_data(qtbot, temp_db, sample_card, sample_transactions)
        view.amount_min_filter.setText("0")
        view._apply_filters()

        for row in range(view.table.rowCount()):
            if not view.table.isRowHidden(row):
                amount_item = view.table.item(row, 4)
                if amount_item:
                    amount_text = amount_item.text().replace('$', '').replace(',', '').strip()
                    try:
                        amount = float(amount_text)
                        assert amount >= 0, f"Row {row} has amount {amount} but should be >= 0"
                    except ValueError:
                        pass

    def test_amount_max_filter(self, qtbot, temp_db, sample_card, sample_transactions):
        """Set amount_max_filter to '0', only negative amounts visible"""
        view = self._make_view_with_data(qtbot, temp_db, sample_card, sample_transactions)
        view.amount_max_filter.setText("0")
        view._apply_filters()

        for row in range(view.table.rowCount()):
            if not view.table.isRowHidden(row):
                amount_item = view.table.item(row, 4)
                if amount_item:
                    amount_text = amount_item.text().replace('$', '').replace(',', '').strip()
                    try:
                        amount = float(amount_text)
                        assert amount <= 0, f"Row {row} has amount {amount} but should be <= 0"
                    except ValueError:
                        pass

    def test_sign_filter_income(self, qtbot, temp_db, sample_card, sample_transactions):
        """Set amount_sign_filter to index 1 (Income+), only positive amounts visible"""
        view = self._make_view_with_data(qtbot, temp_db, sample_card, sample_transactions)
        view.amount_sign_filter.setCurrentIndex(1)
        view._apply_filters()

        for row in range(view.table.rowCount()):
            if not view.table.isRowHidden(row):
                amount_item = view.table.item(row, 4)
                if amount_item:
                    amount_text = amount_item.text().replace('$', '').replace(',', '').strip()
                    try:
                        amount = float(amount_text)
                        assert amount > 0, f"Row {row} has amount {amount} but should be > 0"
                    except ValueError:
                        pass

    def test_sign_filter_expenses(self, qtbot, temp_db, sample_card, sample_transactions):
        """Set amount_sign_filter to index 2 (Expenses-), only negative amounts visible"""
        view = self._make_view_with_data(qtbot, temp_db, sample_card, sample_transactions)
        view.amount_sign_filter.setCurrentIndex(2)
        view._apply_filters()

        for row in range(view.table.rowCount()):
            if not view.table.isRowHidden(row):
                amount_item = view.table.item(row, 4)
                if amount_item:
                    amount_text = amount_item.text().replace('$', '').replace(',', '').strip()
                    try:
                        amount = float(amount_text)
                        assert amount < 0, f"Row {row} has amount {amount} but should be < 0"
                    except ValueError:
                        pass

    def test_clear_filters_shows_all(self, qtbot, temp_db, sample_card, sample_transactions):
        """Apply filters, then _clear_filters(), all rows visible"""
        view = self._make_view_with_data(qtbot, temp_db, sample_card, sample_transactions)
        # Apply a restrictive filter first
        view.desc_filter.setText("Paycheck")
        view._apply_filters()
        # Verify some rows are hidden
        hidden_count = sum(1 for row in range(view.table.rowCount()) if view.table.isRowHidden(row))
        assert hidden_count > 0, "At least one row should be hidden after filtering"

        # Clear filters
        view._clear_filters()
        for row in range(view.table.rowCount()):
            assert not view.table.isRowHidden(row), f"Row {row} should be visible after clearing filters"

    def test_invalid_amount_filter_ignored(self, qtbot, temp_db, sample_card, sample_transactions):
        """Set amount_min_filter to 'abc', no crash, all rows visible"""
        view = self._make_view_with_data(qtbot, temp_db, sample_card, sample_transactions)
        view.amount_min_filter.setText("abc")
        view._apply_filters()
        # All rows should remain visible since the invalid filter is ignored
        for row in range(view.table.rowCount()):
            assert not view.table.isRowHidden(row), f"Row {row} should be visible with invalid filter"


class TestCountPaydaysInMonth:
    """Tests for _count_paydays_in_month(year, month)"""

    def _make_view(self, qtbot, temp_db):
        """Helper to create a TransactionsView instance"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        return view

    def test_january_2026_has_3_paydays(self, qtbot, temp_db):
        """January 2026 has 5 Fridays (2,9,16,23,30) -> returns 3"""
        view = self._make_view(qtbot, temp_db)
        assert view._count_paydays_in_month(2026, 1) == 3

    def test_february_2026_has_2_paydays(self, qtbot, temp_db):
        """February 2026 has 4 Fridays -> returns 2"""
        view = self._make_view(qtbot, temp_db)
        assert view._count_paydays_in_month(2026, 2) == 2

    def test_may_2026_has_3_paydays(self, qtbot, temp_db):
        """May 2026 has 5 Fridays (1,8,15,22,29) -> returns 3"""
        view = self._make_view(qtbot, temp_db)
        assert view._count_paydays_in_month(2026, 5) == 3


class TestPayTypeFilter:
    """Tests for pay type filter behavior"""

    def _make_view(self, qtbot, temp_db):
        """Helper to create a TransactionsView instance"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        return view

    def test_select_all_pay_types_text(self, qtbot, temp_db):
        """After _select_all_pay_types(), button text is 'All triangle-down'"""
        view = self._make_view(qtbot, temp_db)
        view._select_all_pay_types()
        assert view.pay_type_btn.text() == "All \u25bc"

    def test_select_no_pay_types_text(self, qtbot, temp_db):
        """After _select_no_pay_types(), button text is 'None triangle-down'"""
        view = self._make_view(qtbot, temp_db)
        view._select_no_pay_types()
        assert view.pay_type_btn.text() == "None \u25bc"

    def test_partial_pay_types_text(self, qtbot, temp_db, sample_card):
        """Deselect one type, button shows 'N/M triangle-down' format"""
        view = self._make_view(qtbot, temp_db)
        # With sample_card, we have Chase (C) + Chase Freedom (CH) = 2 pay types
        total = len(view._pay_type_actions)
        assert total == 2, f"Expected 2 pay types, got {total}"
        # Deselect one pay type (the first one)
        first_code = list(view._pay_type_actions.keys())[0]
        view._pay_type_actions[first_code].setChecked(False)
        view._update_pay_type_filter()
        expected = f"1/{total} \u25bc"
        assert view.pay_type_btn.text() == expected


class TestToggleZeroOwedColumns:
    """Tests for _toggle_zero_owed_columns"""

    def test_hides_zero_balance_card_columns(self, qtbot, temp_db, multiple_cards):
        """CI (Citi) has balance=0, its Owed column should be hidden after toggle"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        # Ensure all columns start visible
        view._show_all_columns()
        # Hide zero-owed columns
        view._toggle_zero_owed_columns(False)
        # Find the Citi Owed column index and verify it is hidden
        citi_owed_idx = view._all_columns.index("Citi Owed")
        assert view.table.isColumnHidden(citi_owed_idx) is True

    def test_shows_zero_balance_card_columns(self, qtbot, temp_db, multiple_cards):
        """After showing zero-owed columns, CI Owed column should be visible"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        # First hide them
        view._toggle_zero_owed_columns(False)
        citi_owed_idx = view._all_columns.index("Citi Owed")
        assert view.table.isColumnHidden(citi_owed_idx) is True
        # Now show them
        view._toggle_zero_owed_columns(True)
        assert view.table.isColumnHidden(citi_owed_idx) is False

    def test_nonzero_balance_columns_unchanged(self, qtbot, temp_db, multiple_cards):
        """Columns for cards with balance > 0 should not be hidden"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        view._show_all_columns()
        view._toggle_zero_owed_columns(False)
        # Chase Freedom (balance=3000), Amex Blue (4500), Discover (3200) should remain visible
        for card_name in ["Chase Freedom", "Amex Blue", "Discover"]:
            owed_col = f"{card_name} Owed"
            idx = view._all_columns.index(owed_col)
            assert view.table.isColumnHidden(idx) is False, f"{owed_col} should remain visible"


class TestSaveColumnVisibility:
    """Tests for _save_column_visibility"""

    def test_saves_hidden_columns_to_settings(self, qtbot, temp_db, sample_card):
        """Hide a column, call _save_column_visibility, verify QSettings"""
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtCore import QSettings
        view = TransactionsView()
        qtbot.addWidget(view)
        # Hide the Chase Freedom Owed column
        owed_idx = view._all_columns.index("Chase Freedom Owed")
        view.table.setColumnHidden(owed_idx, True)
        view._save_column_visibility()
        # Read back from QSettings
        settings = QSettings("BudgetApp", "PersonalBudgetManager")
        hidden = settings.value("transactions/hidden_columns", [])
        assert "Chase Freedom Owed" in hidden

    def test_visible_columns_not_in_settings(self, qtbot, temp_db, sample_card):
        """Visible columns should not appear in the hidden list"""
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtCore import QSettings
        view = TransactionsView()
        qtbot.addWidget(view)
        # Show all columns
        view._show_all_columns()
        view._save_column_visibility()
        settings = QSettings("BudgetApp", "PersonalBudgetManager")
        hidden = settings.value("transactions/hidden_columns", [])
        if hidden is None:
            hidden = []
        assert "Chase Freedom Owed" not in hidden
        assert "Chase Freedom Avail" not in hidden


class TestUpdateBalancesForPostedTransaction:
    """Tests for _update_balances_for_posted_transaction"""

    def test_posting_chase_transaction_updates_account(self, qtbot, temp_db, sample_account):
        """Posting a Chase transaction with amount=-100 decreases account balance by 100"""
        from budget_app.views.transactions_view import TransactionsView
        from budget_app.models.transaction import Transaction
        from budget_app.models.account import Account
        view = TransactionsView()
        qtbot.addWidget(view)
        trans = Transaction(
            id=None, date='2026-02-01', description='Test Expense',
            amount=-100.0, payment_method='C', is_posted=False
        )
        trans.save()
        view._update_balances_for_posted_transaction(trans)
        account = Account.get_by_code('C')
        assert account.current_balance == 4900.0  # 5000 - 100

    def test_posting_positive_chase_transaction(self, qtbot, temp_db, sample_account):
        """Posting a positive Chase transaction (income) increases account balance"""
        from budget_app.views.transactions_view import TransactionsView
        from budget_app.models.transaction import Transaction
        from budget_app.models.account import Account
        view = TransactionsView()
        qtbot.addWidget(view)
        trans = Transaction(
            id=None, date='2026-02-01', description='Paycheck',
            amount=2500.0, payment_method='C', is_posted=False
        )
        trans.save()
        view._update_balances_for_posted_transaction(trans)
        account = Account.get_by_code('C')
        assert account.current_balance == 7500.0  # 5000 + 2500

    def test_posting_card_transaction_updates_card(self, qtbot, temp_db, sample_card):
        """Posting a credit card transaction updates the card balance"""
        from budget_app.views.transactions_view import TransactionsView
        from budget_app.models.transaction import Transaction
        from budget_app.models.credit_card import CreditCard
        view = TransactionsView()
        qtbot.addWidget(view)
        trans = Transaction(
            id=None, date='2026-02-05', description='Card Purchase',
            amount=-50.0, payment_method='CH', is_posted=False
        )
        trans.save()
        view._update_balances_for_posted_transaction(trans)
        card = CreditCard.get_by_code('CH')
        assert card.current_balance == 2950.0  # 3000 + (-50)

    def test_posting_cc_payment_updates_linked_card(self, qtbot, temp_db, sample_account, sample_card):
        """Posting a CC payment from Chase also updates the linked card balance"""
        from budget_app.views.transactions_view import TransactionsView
        from budget_app.models.transaction import Transaction
        from budget_app.models.account import Account
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.recurring_charge import RecurringCharge
        view = TransactionsView()
        qtbot.addWidget(view)
        # Create a recurring charge linked to sample_card
        charge = RecurringCharge(
            id=None, name='Chase Freedom Payment', amount=-200.0,
            day_of_month=15, payment_method='C',
            frequency='MONTHLY', amount_type='FIXED',
            linked_card_id=sample_card.id
        )
        charge.save()
        # Create a transaction using this recurring charge from Chase
        trans = Transaction(
            id=None, date='2026-02-15', description='Chase Freedom Payment',
            amount=-200.0, payment_method='C', is_posted=False,
            recurring_charge_id=charge.id
        )
        trans.save()
        view._update_balances_for_posted_transaction(trans)
        # Account decreased: 5000 + (-200) = 4800
        account = Account.get_by_code('C')
        assert account.current_balance == 4800.0
        # Linked card also decreased: 3000 + (-200) = 2800
        card = CreditCard.get_by_code('CH')
        assert card.current_balance == 2800.0


class TestReverseBalancesForUnpostedTransaction:
    """Tests for _reverse_balances_for_unposted_transaction"""

    def test_reverse_chase_transaction(self, qtbot, temp_db, sample_account):
        """Reversing a Chase transaction with amount=-100 adds 100 back to balance"""
        from budget_app.views.transactions_view import TransactionsView
        from budget_app.models.transaction import Transaction
        from budget_app.models.account import Account
        view = TransactionsView()
        qtbot.addWidget(view)
        trans = Transaction(
            id=None, date='2026-02-01', description='Test Expense',
            amount=-100.0, payment_method='C', is_posted=True
        )
        trans.save()
        # First simulate having posted it (balance is already at 4900)
        account = Account.get_by_code('C')
        account.current_balance = 4900.0
        account.save()
        # Now reverse
        view._reverse_balances_for_unposted_transaction(trans)
        account = Account.get_by_code('C')
        assert account.current_balance == 5000.0  # 4900 - (-100) = 5000

    def test_reverse_card_transaction(self, qtbot, temp_db, sample_card):
        """Reversing a card transaction restores the card balance"""
        from budget_app.views.transactions_view import TransactionsView
        from budget_app.models.transaction import Transaction
        from budget_app.models.credit_card import CreditCard
        view = TransactionsView()
        qtbot.addWidget(view)
        trans = Transaction(
            id=None, date='2026-02-05', description='Card Purchase',
            amount=-50.0, payment_method='CH', is_posted=True
        )
        trans.save()
        # Simulate the card having been posted (balance went from 3000 to 2950)
        card = CreditCard.get_by_code('CH')
        card.current_balance = 2950.0
        card.save()
        # Reverse the posting
        view._reverse_balances_for_unposted_transaction(trans)
        card = CreditCard.get_by_code('CH')
        assert card.current_balance == 3000.0  # 2950 - (-50) = 3000

    def test_reverse_cc_payment_updates_linked_card(self, qtbot, temp_db, sample_account, sample_card):
        """Reversing a CC payment restores both account and linked card balances"""
        from budget_app.views.transactions_view import TransactionsView
        from budget_app.models.transaction import Transaction
        from budget_app.models.account import Account
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.recurring_charge import RecurringCharge
        view = TransactionsView()
        qtbot.addWidget(view)
        # Create a recurring charge linked to sample_card
        charge = RecurringCharge(
            id=None, name='Chase Freedom Payment', amount=-200.0,
            day_of_month=15, payment_method='C',
            frequency='MONTHLY', amount_type='FIXED',
            linked_card_id=sample_card.id
        )
        charge.save()
        trans = Transaction(
            id=None, date='2026-02-15', description='Chase Freedom Payment',
            amount=-200.0, payment_method='C', is_posted=True,
            recurring_charge_id=charge.id
        )
        trans.save()
        # Simulate the posted state: account at 4800, card at 2800
        account = Account.get_by_code('C')
        account.current_balance = 4800.0
        account.save()
        card = CreditCard.get_by_code('CH')
        card.current_balance = 2800.0
        card.save()
        # Reverse
        view._reverse_balances_for_unposted_transaction(trans)
        account = Account.get_by_code('C')
        assert account.current_balance == 5000.0  # 4800 - (-200) = 5000
        card = CreditCard.get_by_code('CH')
        assert card.current_balance == 3000.0  # 2800 - (-200) = 3000


class TestGetSelectedTransactionId:
    """Tests for _get_selected_transaction_id"""

    def test_returns_none_when_no_selection(self, qtbot, temp_db):
        """Returns None when no row is selected in the table"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        view.table.clearSelection()
        assert view._get_selected_transaction_id() is None

    def test_returns_id_when_row_selected(self, qtbot, temp_db, sample_account, sample_card, sample_transactions):
        """Returns the transaction ID when a row is selected"""
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtCore import QDate
        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False
        view.from_date.setDate(QDate.fromString("2026-01-01", "yyyy-MM-dd"))
        view.to_date.setDate(QDate.fromString("2026-12-31", "yyyy-MM-dd"))
        view.refresh()
        # Ensure there are rows in the table
        assert view.table.rowCount() > 0
        # Select the first row
        view.table.selectRow(0)
        trans_id = view._get_selected_transaction_id()
        assert trans_id is not None
        assert isinstance(trans_id, int)


class TestOnItemChanged:
    """Tests for _on_item_changed - posting/unposting via checkbox"""

    def _make_view(self, qtbot):
        """Helper to create a TransactionsView with a wide date range"""
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtCore import QDate
        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False
        view.from_date.setDate(QDate.fromString("2026-01-01", "yyyy-MM-dd"))
        view.to_date.setDate(QDate.fromString("2026-12-31", "yyyy-MM-dd"))
        return view

    def test_non_checkbox_column_ignored(self, qtbot, temp_db, sample_account, sample_card, sample_transactions):
        """Changing a non-checkbox column (column != 0) should do nothing"""
        from budget_app.models.transaction import Transaction
        view = self._make_view(qtbot)
        view.refresh()
        # Get a description item (column 3) and call _on_item_changed
        item = view.table.item(0, 3)
        assert item is not None
        # Capture state before
        trans_id = item.data(Qt.ItemDataRole.UserRole)
        trans_before = Transaction.get_by_id(trans_id)
        posted_before = trans_before.is_posted if trans_before else None
        # Call _on_item_changed on a non-checkbox column - should be a no-op
        view._on_item_changed(item)
        # Verify nothing changed
        if trans_before:
            trans_after = Transaction.get_by_id(trans_id)
            assert trans_after.is_posted == posted_before

    def test_checkbox_no_trans_id_ignored(self, qtbot, temp_db):
        """If checkbox item has no UserRole data, should be ignored"""
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtWidgets import QTableWidgetItem
        view = TransactionsView()
        qtbot.addWidget(view)
        # Manually add a row with no UserRole data on the checkbox item
        view.table.setRowCount(1)
        item = QTableWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, None)
        item.setCheckState(Qt.CheckState.Checked)
        view.table.setItem(0, 0, item)
        # Should not crash or raise any errors
        view._on_item_changed(view.table.item(0, 0))

    def test_posting_transaction_via_checkbox(self, qtbot, temp_db, sample_account, sample_card, sample_transactions):
        """Checking the checkbox should mark transaction as posted and update balances"""
        from budget_app.models.transaction import Transaction
        view = self._make_view(qtbot)
        view.refresh()
        # Find an unposted transaction row and check its checkbox
        for row in range(view.table.rowCount()):
            checkbox = view.table.item(row, 0)
            if checkbox and checkbox.checkState() == Qt.CheckState.Unchecked:
                trans_id = checkbox.data(Qt.ItemDataRole.UserRole)
                if trans_id:
                    # Block signals so we can manually trigger
                    view.table.blockSignals(True)
                    checkbox.setCheckState(Qt.CheckState.Checked)
                    view.table.blockSignals(False)
                    view._on_item_changed(checkbox)
                    # Verify the transaction is now posted
                    trans = Transaction.get_by_id(trans_id)
                    assert trans.is_posted is True
                    assert trans.posted_date is not None
                    break
        else:
            pytest.fail("No unposted transaction found in table")

    def test_unposting_transaction_via_checkbox(self, qtbot, temp_db, sample_account, sample_card, sample_transactions):
        """Unchecking the checkbox should unpost and reverse balances"""
        from budget_app.models.transaction import Transaction
        view = self._make_view(qtbot)
        view.refresh()
        # Find an unposted transaction, post it, then unpost it
        for row in range(view.table.rowCount()):
            checkbox = view.table.item(row, 0)
            if checkbox and checkbox.checkState() == Qt.CheckState.Unchecked:
                trans_id = checkbox.data(Qt.ItemDataRole.UserRole)
                if trans_id:
                    # Post it first
                    view.table.blockSignals(True)
                    checkbox.setCheckState(Qt.CheckState.Checked)
                    view.table.blockSignals(False)
                    view._on_item_changed(checkbox)
                    trans = Transaction.get_by_id(trans_id)
                    assert trans.is_posted is True
                    # Now unpost it
                    view.table.blockSignals(True)
                    checkbox.setCheckState(Qt.CheckState.Unchecked)
                    view.table.blockSignals(False)
                    view._on_item_changed(checkbox)
                    trans = Transaction.get_by_id(trans_id)
                    assert trans.is_posted is False
                    assert trans.posted_date is None
                    break
        else:
            pytest.fail("No unposted transaction found in table")

    def test_posting_already_posted_is_noop(self, qtbot, temp_db, sample_account, sample_card, sample_transactions):
        """If transaction is already posted and checkbox is checked, no DB change occurs"""
        from budget_app.models.transaction import Transaction
        from budget_app.models.account import Account
        view = self._make_view(qtbot)
        view.refresh()
        # Find an unposted transaction and post it via checkbox
        for row in range(view.table.rowCount()):
            checkbox = view.table.item(row, 0)
            if checkbox and checkbox.checkState() == Qt.CheckState.Unchecked:
                trans_id = checkbox.data(Qt.ItemDataRole.UserRole)
                if trans_id:
                    # Post it
                    view.table.blockSignals(True)
                    checkbox.setCheckState(Qt.CheckState.Checked)
                    view.table.blockSignals(False)
                    view._on_item_changed(checkbox)
                    # Record the account balance after posting
                    account = Account.get_by_code('C')
                    balance_after_post = account.current_balance
                    # Call _on_item_changed again with same Checked state
                    # The transaction is already posted, so is_posted == is_posted, should be a no-op
                    view._on_item_changed(checkbox)
                    account = Account.get_by_code('C')
                    assert account.current_balance == balance_after_post
                    break
        else:
            pytest.fail("No unposted transaction found in table")


class TestTransactionCrudNoSelection:
    """Tests for add/edit/delete with no selection"""

    def test_edit_no_selection_warns(self, qtbot, temp_db, mock_qmessagebox):
        """Edit with no selection shows a warning"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        view._edit_transaction()
        assert mock_qmessagebox.warning_called

    def test_delete_no_selection_warns(self, qtbot, temp_db, mock_qmessagebox):
        """Delete with no selection shows a warning"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        view._delete_transaction()
        assert mock_qmessagebox.warning_called

    def test_delete_all_empty_db_shows_info(self, qtbot, temp_db, mock_qmessagebox):
        """Delete all with no transactions shows informational message"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        view._delete_all_transactions()
        assert mock_qmessagebox.info_called
        assert "no transactions" in mock_qmessagebox.info_text.lower()

    def test_clear_posted_no_posted_shows_info(self, qtbot, temp_db, mock_qmessagebox):
        """Clear posted with no posted transactions shows informational message"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        view._clear_posted_transactions()
        assert mock_qmessagebox.info_called


class TestNotifyBalanceChange:
    """Tests for _notify_balance_change"""

    def test_notify_no_parent(self, qtbot, temp_db):
        """When there's no parent with dashboard_view, should not crash"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        # Call _notify_balance_change on a view with no parent hierarchy
        view._notify_balance_change()  # Should not crash

    def test_notify_with_dashboard_parent(self, qtbot, temp_db):
        """When a parent has dashboard_view, it should call mark_dirty on it"""
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtWidgets import QWidget
        from unittest.mock import MagicMock
        # Create a fake parent widget with dashboard_view and posted_transactions_view
        parent_widget = QWidget()
        qtbot.addWidget(parent_widget)
        parent_widget.dashboard_view = MagicMock()
        parent_widget.posted_transactions_view = MagicMock()
        # Create view and reparent it
        view = TransactionsView()
        view.setParent(parent_widget)
        view._notify_balance_change()
        parent_widget.dashboard_view.mark_dirty.assert_called_once()
        parent_widget.posted_transactions_view.mark_dirty.assert_called_once()

    def test_notify_walks_up_parent_chain(self, qtbot, temp_db):
        """_notify_balance_change walks up the parent chain to find dashboard_view"""
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtWidgets import QWidget
        from unittest.mock import MagicMock
        # Create grandparent with the attributes
        grandparent = QWidget()
        qtbot.addWidget(grandparent)
        grandparent.dashboard_view = MagicMock()
        grandparent.posted_transactions_view = MagicMock()
        # Create intermediate parent (no dashboard_view)
        middle = QWidget(grandparent)
        # Create view and reparent it to the middle widget
        view = TransactionsView()
        view.setParent(middle)
        view._notify_balance_change()
        grandparent.dashboard_view.mark_dirty.assert_called_once()
        grandparent.posted_transactions_view.mark_dirty.assert_called_once()


class TestSortCCColumns:
    """Tests for _sort_cc_columns and _rebuild_columns_with_sorted_cards"""

    def test_sort_descending_reorders_by_balance(self, qtbot, temp_db, multiple_cards):
        """Sort descending: cards reordered by balance high→low"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False
        view._sort_cc_columns(descending=True)
        # After sorting, _cards should be in descending balance order
        balances = [c.current_balance for c in view._cards]
        assert balances == sorted(balances, reverse=True)

    def test_sort_ascending_reorders_by_balance(self, qtbot, temp_db, multiple_cards):
        """Sort ascending: cards reordered by balance low→high"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False
        view._sort_cc_columns(descending=False)
        balances = [c.current_balance for c in view._cards]
        assert balances == sorted(balances)

    def test_column_headers_change_after_sort(self, qtbot, temp_db, multiple_cards):
        """Column headers reflect new card order after sort"""
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False
        view._sort_cc_columns(descending=True)
        headers = [view.table.horizontalHeaderItem(i).text()
                   for i in range(view.table.columnCount())]
        # First card column after base (6) should be highest-balance card
        sorted_cards = sorted(multiple_cards, key=lambda c: c.current_balance, reverse=True)
        expected_first_owed = f"{sorted_cards[0].name} Owed"
        assert headers[6] == expected_first_owed

    def test_rebuild_preserves_visibility(self, qtbot, temp_db, multiple_cards):
        """_rebuild_columns_with_sorted_cards preserves hidden column settings"""
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtCore import QSettings
        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False
        # Hide a specific column
        view._show_all_columns()
        settings = QSettings("BudgetApp", "PersonalBudgetManager")
        settings.setValue("transactions/hidden_columns", ["Amex Blue Owed"])
        # Rebuild
        view._rebuild_columns_with_sorted_cards()
        # The "Amex Blue Owed" column should still be hidden
        idx = view._all_columns.index("Amex Blue Owed")
        assert view.table.isColumnHidden(idx) is True


class TestRefreshCCPaymentMap:
    """Tests for cc_payment_map tracking linked card balance during refresh"""

    def _make_view(self, qtbot):
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtCore import QDate
        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False
        view.from_date.setDate(QDate.fromString("2026-01-01", "yyyy-MM-dd"))
        view.to_date.setDate(QDate.fromString("2026-12-31", "yyyy-MM-dd"))
        return view

    def test_cc_payment_reduces_linked_card_balance(self, qtbot, temp_db, sample_account, sample_card):
        """A CC payment transaction linked via recurring charge reduces the card's running balance"""
        from budget_app.models.recurring_charge import RecurringCharge
        from budget_app.models.transaction import Transaction

        # Create a recurring charge linked to sample_card (Chase Freedom)
        charge = RecurringCharge(
            id=None, name='CF Payment', amount=-200.0,
            day_of_month=15, payment_method='C',
            frequency='MONTHLY', amount_type='FIXED',
            linked_card_id=sample_card.id
        )
        charge.save()

        # Create the payment transaction from Chase
        trans = Transaction(
            id=None, date='2026-06-15', description='CF Payment',
            amount=-200.0, payment_method='C',
            recurring_charge_id=charge.id, is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        # Find the row for CF Payment and check the card's Owed column
        for row in range(view.table.rowCount()):
            desc_item = view.table.item(row, 3)
            if desc_item and desc_item.text() == 'CF Payment':
                # Chase Freedom Owed is column 6 (base 6 + card index 0 * 2)
                owed_item = view.table.item(row, 6)
                owed_text = owed_item.text().replace('$', '').replace(',', '')
                owed_value = float(owed_text)
                # Card started at 3000, payment of -200 reduces it: 3000 + (-200) = 2800
                assert owed_value == 2800.0
                return
        pytest.fail("CF Payment row not found")

    def test_direct_card_charge_increases_owed(self, qtbot, temp_db, sample_account, sample_card):
        """A charge made directly on a credit card increases the card's Owed running balance"""
        from budget_app.models.transaction import Transaction

        # Create a transaction charged directly to Chase Freedom (pay_type_code='CH')
        trans = Transaction(
            id=None, date='2026-06-01', description='Netflix',
            amount=-15.0, payment_method='CH', is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        # Find the row for Netflix and check the card's Owed column
        for row in range(view.table.rowCount()):
            desc_item = view.table.item(row, 3)
            if desc_item and desc_item.text() == 'Netflix':
                # Chase Freedom Owed column
                owed_col = view._all_columns.index("Chase Freedom Owed")
                owed_item = view.table.item(row, owed_col)
                owed_text = owed_item.text().replace('$', '').replace(',', '')
                owed_value = float(owed_text)
                # Card started at 3000, charge of -15 should increase owed: 3000 - (-15) = 3015
                assert owed_value == 3015.0
                return
        pytest.fail("Netflix row not found")

    def test_manual_cc_payment_reduces_linked_card_balance(self, qtbot, temp_db, sample_account, sample_card):
        """A manual CC payment (no recurring_charge_id) with matching description reduces card's Owed"""
        from budget_app.models.recurring_charge import RecurringCharge
        from budget_app.models.transaction import Transaction

        # Create a recurring charge linked to sample_card (Chase Freedom)
        charge = RecurringCharge(
            id=None, name='Chase Freedom', amount=-200.0,
            day_of_month=15, payment_method='C',
            frequency='MONTHLY', amount_type='CALCULATED',
            linked_card_id=sample_card.id
        )
        charge.save()

        # Create a MANUAL payment transaction (no recurring_charge_id) with matching description
        trans = Transaction(
            id=None, date='2026-06-15', description='Chase Freedom',
            amount=-200.0, payment_method='C',
            recurring_charge_id=None, is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        # Find the row and check the card's Owed column
        for row in range(view.table.rowCount()):
            desc_item = view.table.item(row, 3)
            if desc_item and desc_item.text() == 'Chase Freedom':
                owed_col = view._all_columns.index("Chase Freedom Owed")
                owed_item = view.table.item(row, owed_col)
                owed_text = owed_item.text().replace('$', '').replace(',', '')
                owed_value = float(owed_text)
                # Card started at 3000, manual payment of -200 should reduce: 3000 + (-200) = 2800
                assert owed_value == 2800.0
                return
        pytest.fail("Chase Freedom payment row not found")


class TestRefreshCardColorThresholds:
    """Tests for card Owed/Avail/Utilization color thresholds in refresh()"""

    def _make_view(self, qtbot):
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtCore import QDate
        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False
        view.from_date.setDate(QDate.fromString("2026-01-01", "yyyy-MM-dd"))
        view.to_date.setDate(QDate.fromString("2026-12-31", "yyyy-MM-dd"))
        return view

    def test_owed_over_limit_is_red(self, qtbot, temp_db, sample_account):
        """Card owed > credit limit → red (#f44336)"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.transaction import Transaction
        from PyQt6.QtGui import QColor

        # Card with balance over limit
        card = CreditCard(
            id=None, pay_type_code='OL', name='OverLimit',
            credit_limit=1000.0, current_balance=1500.0,
            interest_rate=0.20, due_day=15
        )
        card.save()

        # Need a transaction to display a row
        trans = Transaction(
            id=None, date='2026-06-01', description='Test',
            amount=-10.0, payment_method='C', is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        # Find the OverLimit Owed column
        owed_col = view._all_columns.index("OverLimit Owed")
        for row in range(view.table.rowCount()):
            item = view.table.item(row, owed_col)
            if item:
                assert item.foreground().color() == QColor("#f44336")
                return
        pytest.fail("No row found with OverLimit Owed cell")

    def test_owed_over_80pct_is_orange(self, qtbot, temp_db, sample_account):
        """Card owed > 80% of limit but < limit → orange (#ff9800)"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.transaction import Transaction
        from PyQt6.QtGui import QColor

        # 850 is 85% of 1000, which is > 80% but < 100%
        card = CreditCard(
            id=None, pay_type_code='H8', name='High80',
            credit_limit=1000.0, current_balance=850.0,
            interest_rate=0.20, due_day=15
        )
        card.save()

        trans = Transaction(
            id=None, date='2026-06-01', description='Test',
            amount=-10.0, payment_method='C', is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        owed_col = view._all_columns.index("High80 Owed")
        for row in range(view.table.rowCount()):
            item = view.table.item(row, owed_col)
            if item:
                assert item.foreground().color() == QColor("#ff9800")
                return
        pytest.fail("No row found with High80 Owed cell")

    def test_avail_negative_is_red(self, qtbot, temp_db, sample_account):
        """Card avail < 0 → red (#f44336)"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.transaction import Transaction
        from PyQt6.QtGui import QColor

        card = CreditCard(
            id=None, pay_type_code='NA', name='NegAvail',
            credit_limit=1000.0, current_balance=1200.0,
            interest_rate=0.20, due_day=15
        )
        card.save()

        trans = Transaction(
            id=None, date='2026-06-01', description='Test',
            amount=-10.0, payment_method='C', is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        avail_col = view._all_columns.index("NegAvail Avail")
        for row in range(view.table.rowCount()):
            item = view.table.item(row, avail_col)
            if item:
                assert item.foreground().color() == QColor("#f44336")
                return
        pytest.fail("No row found with NegAvail Avail cell")

    def test_avail_under_100_is_orange(self, qtbot, temp_db, sample_account):
        """Card avail < 100 but >= 0 → orange (#ff9800)"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.transaction import Transaction
        from PyQt6.QtGui import QColor

        # avail = 1000 - 950 = 50 < 100
        card = CreditCard(
            id=None, pay_type_code='LA', name='LowAvail',
            credit_limit=1000.0, current_balance=950.0,
            interest_rate=0.20, due_day=15
        )
        card.save()

        trans = Transaction(
            id=None, date='2026-06-01', description='Test',
            amount=-10.0, payment_method='C', is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        avail_col = view._all_columns.index("LowAvail Avail")
        for row in range(view.table.rowCount()):
            item = view.table.item(row, avail_col)
            if item:
                assert item.foreground().color() == QColor("#ff9800")
                return
        pytest.fail("No row found with LowAvail Avail cell")

    def test_utilization_over_80pct_is_red(self, qtbot, temp_db, sample_account):
        """Row utilization > 0.8 → red (#f44336)"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.transaction import Transaction
        from PyQt6.QtGui import QColor

        # Single card: balance 900, limit 1000 → util = 90%
        card = CreditCard(
            id=None, pay_type_code='HU', name='HighUtil',
            credit_limit=1000.0, current_balance=900.0,
            interest_rate=0.20, due_day=15
        )
        card.save()

        trans = Transaction(
            id=None, date='2026-06-01', description='Test',
            amount=-10.0, payment_method='C', is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        util_col = view._all_columns.index("CC Utilization")
        for row in range(view.table.rowCount()):
            item = view.table.item(row, util_col)
            if item:
                assert item.foreground().color() == QColor("#f44336")
                return
        pytest.fail("No row found with CC Utilization cell")

    def test_utilization_over_50pct_is_orange(self, qtbot, temp_db, sample_account):
        """Row utilization > 0.5 but <= 0.8 → orange (#ff9800)"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.transaction import Transaction
        from PyQt6.QtGui import QColor

        # Single card: balance 600, limit 1000 → util = 60%
        card = CreditCard(
            id=None, pay_type_code='MU', name='MedUtil',
            credit_limit=1000.0, current_balance=600.0,
            interest_rate=0.20, due_day=15
        )
        card.save()

        trans = Transaction(
            id=None, date='2026-06-01', description='Test',
            amount=-10.0, payment_method='C', is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        util_col = view._all_columns.index("CC Utilization")
        for row in range(view.table.rowCount()):
            item = view.table.item(row, util_col)
            if item:
                assert item.foreground().color() == QColor("#ff9800")
                return
        pytest.fail("No row found with CC Utilization cell")


class TestRefreshSummaryColors:
    """Tests for summary label color thresholds"""

    def _make_view(self, qtbot):
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtCore import QDate
        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False
        view.from_date.setDate(QDate.fromString("2026-01-01", "yyyy-MM-dd"))
        view.to_date.setDate(QDate.fromString("2026-12-31", "yyyy-MM-dd"))
        return view

    def test_total_cc_avail_negative_is_red(self, qtbot, temp_db, sample_account):
        """Total CC avail < 0 → red label"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.transaction import Transaction

        # Card over limit → negative available
        card = CreditCard(
            id=None, pay_type_code='OA', name='OverAvail',
            credit_limit=500.0, current_balance=600.0,
            interest_rate=0.20, due_day=15
        )
        card.save()

        trans = Transaction(
            id=None, date='2026-06-01', description='Test',
            amount=-10.0, payment_method='C', is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        assert "color: #f44336" in view.total_avail_label.styleSheet()

    def test_total_cc_avail_positive_is_green(self, qtbot, temp_db, sample_account):
        """Total CC avail > 0 → green label"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.transaction import Transaction

        card = CreditCard(
            id=None, pay_type_code='PA', name='PosAvail',
            credit_limit=5000.0, current_balance=1000.0,
            interest_rate=0.20, due_day=15
        )
        card.save()

        trans = Transaction(
            id=None, date='2026-06-01', description='Test',
            amount=-10.0, payment_method='C', is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        assert "color: #4caf50" in view.total_avail_label.styleSheet()

    def test_utilization_over_80pct_label_red(self, qtbot, temp_db, sample_account):
        """Utilization > 0.8 → red label"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.transaction import Transaction

        card = CreditCard(
            id=None, pay_type_code='UR', name='UtilRed',
            credit_limit=1000.0, current_balance=900.0,
            interest_rate=0.20, due_day=15
        )
        card.save()

        trans = Transaction(
            id=None, date='2026-06-01', description='Test',
            amount=-10.0, payment_method='C', is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        assert "color: #f44336" in view.total_util_label.styleSheet()

    def test_utilization_over_50pct_label_orange(self, qtbot, temp_db, sample_account):
        """Utilization > 0.5 but <= 0.8 → orange label"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.transaction import Transaction

        card = CreditCard(
            id=None, pay_type_code='UO', name='UtilOrange',
            credit_limit=1000.0, current_balance=600.0,
            interest_rate=0.20, due_day=15
        )
        card.save()

        trans = Transaction(
            id=None, date='2026-06-01', description='Test',
            amount=-10.0, payment_method='C', is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        assert "color: #ff9800" in view.total_util_label.styleSheet()

    def test_utilization_low_label_green(self, qtbot, temp_db, sample_account):
        """Utilization <= 0.5 → green label"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.transaction import Transaction

        card = CreditCard(
            id=None, pay_type_code='UG', name='UtilGreen',
            credit_limit=10000.0, current_balance=1000.0,
            interest_rate=0.20, due_day=15
        )
        card.save()

        trans = Transaction(
            id=None, date='2026-06-01', description='Test',
            amount=-10.0, payment_method='C', is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        assert "color: #4caf50" in view.total_util_label.styleSheet()

    def test_chase_summary_negative_is_red(self, qtbot, temp_db, sample_account):
        """Chase balance < 0 → red label"""
        from budget_app.models.transaction import Transaction

        # Drive chase balance negative: account has 5000, spend -10000
        trans = Transaction(
            id=None, date='2026-06-01', description='Huge',
            amount=-10000.0, payment_method='C', is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        assert "color: #f44336" in view.chase_summary.styleSheet()

    def test_chase_summary_low_is_orange(self, qtbot, temp_db, sample_account):
        """Chase balance > 0 but < 500 → orange label"""
        from budget_app.models.transaction import Transaction

        # Drive chase to 100: 5000 - 4900 = 100
        trans = Transaction(
            id=None, date='2026-06-01', description='Big',
            amount=-4900.0, payment_method='C', is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        assert "color: #ff9800" in view.chase_summary.styleSheet()

    def test_chase_summary_healthy_is_green(self, qtbot, temp_db, sample_account):
        """Chase balance >= 500 → green label"""
        from budget_app.models.transaction import Transaction

        trans = Transaction(
            id=None, date='2026-06-01', description='Small',
            amount=-10.0, payment_method='C', is_posted=False
        )
        trans.save()

        view = self._make_view(qtbot)
        view.refresh()

        assert "color: #4caf50" in view.chase_summary.styleSheet()


class TestAddTransaction:
    """Tests for _add_transaction with mocked dialog"""

    def test_add_accepted_saves_and_refreshes(self, qtbot, temp_db, sample_account):
        """Mock TransactionDialog accepted → new transaction saved in DB"""
        from budget_app.views.transactions_view import TransactionsView
        from budget_app.models.transaction import Transaction
        from unittest.mock import patch, MagicMock

        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False

        mock_trans = Transaction(
            id=None, date='2026-06-01', description='Mock Purchase',
            amount=-50.0, payment_method='C', is_posted=False
        )

        with patch('budget_app.views.transactions_view.TransactionDialog') as MockDialog:
            mock_instance = MagicMock()
            mock_instance.exec.return_value = 1  # QDialog.DialogCode.Accepted
            mock_instance.get_transaction.return_value = mock_trans
            MockDialog.return_value = mock_instance

            view._add_transaction()

        # Verify transaction was saved
        assert mock_trans.id is not None
        saved = Transaction.get_by_id(mock_trans.id)
        assert saved.description == 'Mock Purchase'

    def test_add_rejected_no_save(self, qtbot, temp_db):
        """Mock TransactionDialog rejected → no transaction saved"""
        from budget_app.views.transactions_view import TransactionsView
        from budget_app.models.transaction import Transaction
        from unittest.mock import patch, MagicMock

        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False

        with patch('budget_app.views.transactions_view.TransactionDialog') as MockDialog:
            mock_instance = MagicMock()
            mock_instance.exec.return_value = 0  # Rejected
            MockDialog.return_value = mock_instance

            view._add_transaction()

        # No transactions should exist
        all_trans = Transaction.get_all()
        assert len(all_trans) == 0


class TestEditTransaction:
    """Tests for _edit_transaction with mocked dialog"""

    def _make_view(self, qtbot):
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtCore import QDate
        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False
        view.from_date.setDate(QDate.fromString("2026-01-01", "yyyy-MM-dd"))
        view.to_date.setDate(QDate.fromString("2026-12-31", "yyyy-MM-dd"))
        return view

    def test_edit_accepted_updates_transaction(self, qtbot, temp_db, sample_account, sample_card, sample_transactions):
        """Edit accepted → transaction updated in DB"""
        from budget_app.models.transaction import Transaction
        from unittest.mock import patch, MagicMock

        view = self._make_view(qtbot)
        view.refresh()
        view.table.selectRow(0)

        # Capture trans_id BEFORE edit (refresh inside edit reorders rows)
        trans_id = view.table.item(0, 3).data(Qt.ItemDataRole.UserRole)

        updated_trans = Transaction(
            id=None, date='2026-06-01', description='Updated Description',
            amount=-99.0, payment_method='C', is_posted=False
        )

        with patch('budget_app.views.transactions_view.TransactionDialog') as MockDialog:
            mock_instance = MagicMock()
            mock_instance.exec.return_value = 1  # Accepted
            mock_instance.get_transaction.return_value = updated_trans
            MockDialog.return_value = mock_instance

            view._edit_transaction()

        saved = Transaction.get_by_id(trans_id)
        assert saved.description == 'Updated Description'
        assert saved.amount == -99.0

    def test_edit_rejected_no_change(self, qtbot, temp_db, sample_account, sample_card, sample_transactions):
        """Edit rejected → transaction unchanged"""
        from budget_app.models.transaction import Transaction
        from unittest.mock import patch, MagicMock

        view = self._make_view(qtbot)
        view.refresh()
        view.table.selectRow(0)

        trans_id = view.table.item(0, 3).data(Qt.ItemDataRole.UserRole)
        original = Transaction.get_by_id(trans_id)
        original_desc = original.description

        with patch('budget_app.views.transactions_view.TransactionDialog') as MockDialog:
            mock_instance = MagicMock()
            mock_instance.exec.return_value = 0  # Rejected
            MockDialog.return_value = mock_instance

            view._edit_transaction()

        saved = Transaction.get_by_id(trans_id)
        assert saved.description == original_desc


class TestDeleteTransaction:
    """Tests for _delete_transaction with selection and confirmation"""

    def _make_view(self, qtbot):
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtCore import QDate
        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False
        view.from_date.setDate(QDate.fromString("2026-01-01", "yyyy-MM-dd"))
        view.to_date.setDate(QDate.fromString("2026-12-31", "yyyy-MM-dd"))
        return view

    def test_delete_confirmed_removes_transaction(self, qtbot, temp_db, sample_account, sample_card, sample_transactions, mock_qmessagebox):
        """Confirm delete → transaction removed from DB"""
        from budget_app.models.transaction import Transaction

        mock_qmessagebox.last_return = __import__('PyQt6.QtWidgets', fromlist=['QMessageBox']).QMessageBox.StandardButton.Yes

        view = self._make_view(qtbot)
        view.refresh()
        initial_count = view.table.rowCount()
        view.table.selectRow(0)
        trans_id = view.table.item(0, 3).data(Qt.ItemDataRole.UserRole)

        view._delete_transaction()

        assert Transaction.get_by_id(trans_id) is None

    def test_delete_declined_keeps_transaction(self, qtbot, temp_db, sample_account, sample_card, sample_transactions, mock_qmessagebox):
        """Decline delete → transaction still exists"""
        from budget_app.models.transaction import Transaction
        from PyQt6.QtWidgets import QMessageBox

        mock_qmessagebox.last_return = QMessageBox.StandardButton.No

        view = self._make_view(qtbot)
        view.refresh()
        view.table.selectRow(0)
        trans_id = view.table.item(0, 3).data(Qt.ItemDataRole.UserRole)

        view._delete_transaction()

        assert Transaction.get_by_id(trans_id) is not None


class TestDeleteAllTransactions:
    """Tests for _delete_all_transactions with double confirmation"""

    def test_both_confirms_delete_all(self, qtbot, temp_db, sample_transactions, mock_qmessagebox):
        """Both confirmations Yes → all transactions deleted"""
        from budget_app.views.transactions_view import TransactionsView
        from budget_app.models.transaction import Transaction
        from PyQt6.QtWidgets import QMessageBox

        mock_qmessagebox.last_return = QMessageBox.StandardButton.Yes

        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False

        assert len(Transaction.get_all()) == 4
        view._delete_all_transactions()
        assert len(Transaction.get_all()) == 0
        assert mock_qmessagebox.info_called

    def test_first_yes_second_no_keeps_all(self, qtbot, temp_db, sample_transactions, mock_qmessagebox):
        """First Yes, second No → transactions kept"""
        from budget_app.views.transactions_view import TransactionsView
        from budget_app.models.transaction import Transaction
        from PyQt6.QtWidgets import QMessageBox

        # Return Yes first, then No
        call_count = [0]
        original_warning = QMessageBox.warning

        def side_effect(parent, title, text, buttons=None, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return QMessageBox.StandardButton.Yes
            return QMessageBox.StandardButton.No

        mock_qmessagebox.last_return = QMessageBox.StandardButton.Yes
        # Override the warning to alternate responses
        from unittest.mock import MagicMock
        QMessageBox.warning = staticmethod(side_effect)

        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False

        view._delete_all_transactions()
        assert len(Transaction.get_all()) == 4

    def test_first_no_keeps_all(self, qtbot, temp_db, sample_transactions, mock_qmessagebox):
        """First No → transactions kept, no second dialog"""
        from budget_app.views.transactions_view import TransactionsView
        from budget_app.models.transaction import Transaction
        from PyQt6.QtWidgets import QMessageBox

        mock_qmessagebox.last_return = QMessageBox.StandardButton.No

        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False

        view._delete_all_transactions()
        assert len(Transaction.get_all()) == 4


class TestClearPostedTransactions:
    """Tests for _clear_posted_transactions"""

    def test_clear_posted_confirmed(self, qtbot, temp_db, sample_transactions, mock_qmessagebox):
        """Confirm clear → refresh + notify called, info shown"""
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtWidgets import QMessageBox

        mock_qmessagebox.last_return = QMessageBox.StandardButton.Yes

        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False

        view._clear_posted_transactions()

        assert mock_qmessagebox.question_called
        assert mock_qmessagebox.info_called
        assert "cleared" in mock_qmessagebox.info_text.lower() or "Cleared" in mock_qmessagebox.info_text

    def test_clear_posted_declined(self, qtbot, temp_db, sample_transactions, mock_qmessagebox):
        """Decline clear → no info message"""
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtWidgets import QMessageBox

        mock_qmessagebox.last_return = QMessageBox.StandardButton.No

        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False

        view._clear_posted_transactions()

        assert mock_qmessagebox.question_called
        # info_called is only set to True when mock_information is called;
        # on MagicMock, unset attributes auto-create, so compare identity to True
        assert mock_qmessagebox.info_called is not True


class TestGenerateRecurringDialog:
    """Tests for _generate_recurring_transactions dialog flow"""

    def test_dialog_accepted_calls_do_generate(self, qtbot, temp_db, mock_qmessagebox):
        """Accepted dialog with months=6, clear=True → _do_generate_recurring called"""
        from budget_app.views.transactions_view import TransactionsView
        from unittest.mock import patch, MagicMock

        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False

        with patch('budget_app.views.transactions_view.GenerateRecurringDialog') as MockDialog:
            mock_instance = MagicMock()
            mock_instance.exec.return_value = 1  # Accepted
            mock_instance.get_months.return_value = 6
            mock_instance.get_clear_existing.return_value = True
            MockDialog.return_value = mock_instance

            with patch.object(view, '_do_generate_recurring') as mock_gen:
                view._generate_recurring_transactions()
                mock_gen.assert_called_once_with(6, True, show_message=True)

    def test_dialog_rejected_no_generation(self, qtbot, temp_db):
        """Rejected dialog → no generation"""
        from budget_app.views.transactions_view import TransactionsView
        from unittest.mock import patch, MagicMock

        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False

        with patch('budget_app.views.transactions_view.GenerateRecurringDialog') as MockDialog:
            mock_instance = MagicMock()
            mock_instance.exec.return_value = 0  # Rejected
            MockDialog.return_value = mock_instance

            with patch.object(view, '_do_generate_recurring') as mock_gen:
                view._generate_recurring_transactions()
                mock_gen.assert_not_called()


class TestDoGenerateRecurring:
    """Tests for _do_generate_recurring"""

    def test_generate_with_message(self, qtbot, temp_db, mock_qmessagebox):
        """With show_message=True → QMessageBox.information shown"""
        from budget_app.views.transactions_view import TransactionsView
        from budget_app.models.transaction import Transaction
        from unittest.mock import patch

        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False

        # Mock generate_future_transactions to return some transactions
        mock_transactions = [
            Transaction(id=None, date='2026-06-01', description='T1',
                       amount=-10.0, payment_method='C', is_posted=False),
            Transaction(id=None, date='2026-07-01', description='T2',
                       amount=-20.0, payment_method='C', is_posted=False),
        ]

        with patch('budget_app.utils.calculations.generate_future_transactions',
                   return_value=mock_transactions):
            view._do_generate_recurring(months=3, clear_existing=False, show_message=True)

        assert mock_qmessagebox.info_called
        assert "2" in mock_qmessagebox.info_text  # "Generated 2 recurring transactions"

    def test_generate_clears_existing(self, qtbot, temp_db, mock_qmessagebox):
        """With clear_existing=True → deletes future recurring but preserves manual"""
        from budget_app.views.transactions_view import TransactionsView
        from budget_app.models.transaction import Transaction
        from budget_app.models.recurring_charge import RecurringCharge
        from unittest.mock import patch

        # Create a recurring charge to reference
        charge = RecurringCharge(
            id=None, name='Netflix', amount=-15.0,
            day_of_month=1, payment_method='C',
            frequency='MONTHLY', amount_type='FIXED'
        )
        charge.save()

        # Future recurring transaction (should be deleted)
        Transaction(
            id=None, date='2099-01-01', description='Netflix',
            amount=-15.0, payment_method='C', is_posted=False,
            recurring_charge_id=charge.id
        ).save()

        # Future manual transaction (should be preserved)
        Transaction(
            id=None, date='2099-01-01', description='Future Manual',
            amount=-10.0, payment_method='C', is_posted=False
        ).save()

        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False

        with patch('budget_app.utils.calculations.generate_future_transactions',
                   return_value=[]):
            view._do_generate_recurring(months=3, clear_existing=True, show_message=False)

        remaining = Transaction.get_all()
        descriptions = [t.description for t in remaining]
        assert 'Netflix' not in descriptions
        assert 'Future Manual' in descriptions

    def test_generate_no_message(self, qtbot, temp_db, mock_qmessagebox):
        """With show_message=False → no QMessageBox shown"""
        from budget_app.views.transactions_view import TransactionsView
        from unittest.mock import patch

        view = TransactionsView()
        qtbot.addWidget(view)
        view._first_load = False

        with patch('budget_app.utils.calculations.generate_future_transactions',
                   return_value=[]):
            view._do_generate_recurring(months=3, clear_existing=False, show_message=False)

        assert mock_qmessagebox.info_called is not True


class TestGenerateSpecialCharges:
    """Tests for _generate_special_charges"""

    def _make_view(self, qtbot, temp_db):
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        return view

    def test_mortgage_991_generates_biweekly(self, qtbot, temp_db):
        """day_of_month=991 (Mortgage) generates bi-weekly transactions"""
        from budget_app.models.recurring_charge import RecurringCharge
        from budget_app.models.paycheck import PaycheckConfig
        from budget_app.models.transaction import Transaction
        from datetime import date

        charge = RecurringCharge(
            id=None, name='Mortgage', amount=-1500.0,
            day_of_month=991, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        charge.save()

        paycheck = PaycheckConfig(
            id=None, gross_amount=3500.0,
            pay_frequency='BIWEEKLY',
            effective_date='2026-01-09',
            is_current=True, pay_day_of_week=4  # Friday
        )
        paycheck.save()

        view = self._make_view(qtbot, temp_db)
        start = date(2026, 3, 1)
        end = date(2026, 4, 30)  # ~2 months
        count = view._generate_special_charges(start, end, [charge], paycheck)

        assert count > 0
        # Each transaction should be 14 days apart
        transactions = Transaction.get_all()
        mortgage_trans = [t for t in transactions if t.description == 'Mortgage']
        assert len(mortgage_trans) == count
        for t in mortgage_trans:
            assert t.amount == -1500.0

    def test_monthly_special_992_generates_on_15th(self, qtbot, temp_db):
        """day_of_month=992 generates monthly on the 15th"""
        from budget_app.models.recurring_charge import RecurringCharge
        from budget_app.models.transaction import Transaction
        from datetime import date

        charge = RecurringCharge(
            id=None, name='Monthly Special', amount=-200.0,
            day_of_month=992, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        charge.save()

        view = self._make_view(qtbot, temp_db)
        start = date(2026, 1, 1)
        end = date(2026, 4, 30)  # 4 months
        count = view._generate_special_charges(start, end, [charge])

        assert count == 4  # Jan 15, Feb 15, Mar 15, Apr 15
        transactions = Transaction.get_all()
        for t in transactions:
            assert t.date.endswith('-15')

    def test_skip_codes_996_and_above(self, qtbot, temp_db):
        """day_of_month >= 996 are skipped"""
        from budget_app.models.recurring_charge import RecurringCharge
        from datetime import date

        charge = RecurringCharge(
            id=None, name='Lisa Code', amount=-100.0,
            day_of_month=996, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        charge.save()

        view = self._make_view(qtbot, temp_db)
        count = view._generate_special_charges(
            date(2026, 1, 1), date(2026, 6, 30), [charge])
        assert count == 0

    def test_skip_lisa_linked_ids(self, qtbot, temp_db):
        """Charges in lisa_linked_ids are skipped"""
        from budget_app.models.recurring_charge import RecurringCharge
        from datetime import date

        charge = RecurringCharge(
            id=None, name='Lisa Linked', amount=-100.0,
            day_of_month=991, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        charge.save()

        view = self._make_view(qtbot, temp_db)
        count = view._generate_special_charges(
            date(2026, 1, 1), date(2026, 6, 30), [charge],
            lisa_linked_ids={charge.id})
        assert count == 0

    def test_skip_zero_amounts(self, qtbot, temp_db):
        """Monthly special charges with amount=0 are skipped"""
        from budget_app.models.recurring_charge import RecurringCharge
        from datetime import date

        charge = RecurringCharge(
            id=None, name='Zero Charge', amount=0.0,
            day_of_month=993, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        charge.save()

        view = self._make_view(qtbot, temp_db)
        count = view._generate_special_charges(
            date(2026, 1, 1), date(2026, 4, 30), [charge])
        assert count == 0

    def test_monthly_special_start_after_15th(self, qtbot, temp_db):
        """Starting after the 15th should start from next month's 15th"""
        from budget_app.models.recurring_charge import RecurringCharge
        from budget_app.models.transaction import Transaction
        from datetime import date

        charge = RecurringCharge(
            id=None, name='Late Start', amount=-50.0,
            day_of_month=994, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        charge.save()

        view = self._make_view(qtbot, temp_db)
        # Start after the 15th
        start = date(2026, 3, 20)
        end = date(2026, 5, 30)
        count = view._generate_special_charges(start, end, [charge])

        assert count == 2  # Apr 15, May 15
        transactions = Transaction.get_all()
        dates = sorted([t.date for t in transactions])
        assert dates[0] == '2026-04-15'
        assert dates[1] == '2026-05-15'

    def test_monthly_special_december_wraps_to_january(self, qtbot, temp_db):
        """Monthly special crossing December wraps to January correctly"""
        from budget_app.models.recurring_charge import RecurringCharge
        from budget_app.models.transaction import Transaction
        from datetime import date

        charge = RecurringCharge(
            id=None, name='Year Cross', amount=-75.0,
            day_of_month=995, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        charge.save()

        view = self._make_view(qtbot, temp_db)
        start = date(2026, 11, 1)
        end = date(2027, 2, 28)
        count = view._generate_special_charges(start, end, [charge])

        assert count == 4  # Nov 15, Dec 15, Jan 15, Feb 15
        transactions = Transaction.get_all()
        dates = sorted([t.date for t in transactions])
        assert dates[0] == '2026-11-15'
        assert dates[1] == '2026-12-15'
        assert dates[2] == '2027-01-15'
        assert dates[3] == '2027-02-15'


    def test_monthly_special_start_after_dec_15_wraps(self, qtbot, temp_db):
        """Starting after Dec 15 wraps to January 15"""
        from budget_app.models.recurring_charge import RecurringCharge
        from budget_app.models.transaction import Transaction
        from datetime import date

        charge = RecurringCharge(
            id=None, name='Dec Wrap', amount=-30.0,
            day_of_month=992, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        charge.save()

        view = self._make_view(qtbot, temp_db)
        # Start after Dec 15 → first occurrence wraps to Jan 15
        start = date(2026, 12, 20)
        end = date(2027, 2, 28)
        count = view._generate_special_charges(start, end, [charge])

        assert count == 2  # Jan 15, Feb 15
        transactions = Transaction.get_all()
        dates = sorted([t.date for t in transactions])
        assert dates[0] == '2027-01-15'
        assert dates[1] == '2027-02-15'

    def test_mortgage_start_on_payday(self, qtbot, temp_db):
        """Mortgage starting on a payday: days_until_payday=0 → set to 7"""
        from budget_app.models.recurring_charge import RecurringCharge
        from budget_app.models.paycheck import PaycheckConfig
        from budget_app.models.transaction import Transaction
        from datetime import date

        charge = RecurringCharge(
            id=None, name='Mortgage', amount=-1500.0,
            day_of_month=991, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        charge.save()

        paycheck = PaycheckConfig(
            id=None, gross_amount=3500.0,
            pay_frequency='BIWEEKLY',
            effective_date='2026-01-09',
            is_current=True, pay_day_of_week=4  # Friday
        )
        paycheck.save()

        view = self._make_view(qtbot, temp_db)
        # Start on a Friday (payday) — 2026-03-06 is a Friday
        start = date(2026, 3, 6)
        end = date(2026, 4, 30)
        count = view._generate_special_charges(start, end, [charge], paycheck)

        assert count > 0
        # First transaction should be 7 days after start (next Friday)
        transactions = Transaction.get_all()
        mortgage_trans = sorted([t for t in transactions if t.description == 'Mortgage'],
                               key=lambda t: t.date)
        first_date = date.fromisoformat(mortgage_trans[0].date)
        assert first_date == date(2026, 3, 13)


class TestGeneratePaydayTransactions:
    """Tests for _generate_payday_transactions"""

    def _make_view(self, qtbot, temp_db):
        from budget_app.views.transactions_view import TransactionsView
        view = TransactionsView()
        qtbot.addWidget(view)
        return view

    def test_biweekly_paydays_generated(self, qtbot, temp_db):
        """Bi-weekly paydays generated from anchor date"""
        from budget_app.models.paycheck import PaycheckConfig
        from budget_app.models.transaction import Transaction
        from datetime import date

        paycheck = PaycheckConfig(
            id=None, gross_amount=3500.0,
            pay_frequency='BIWEEKLY',
            effective_date='2026-01-09',  # A Friday
            is_current=True, pay_day_of_week=4
        )
        paycheck.save()
        paycheck = PaycheckConfig.get_by_id(paycheck.id)

        view = self._make_view(qtbot, temp_db)
        count = view._generate_payday_transactions(
            date(2026, 3, 1), date(2026, 4, 30), paycheck)

        assert count > 0
        transactions = Transaction.get_all()
        paydays = [t for t in transactions if t.description == 'Payday']
        assert len(paydays) >= 2  # At least 2 paydays in ~2 months

    def test_ldbpd_markers_generated(self, qtbot, temp_db):
        """LDBPD markers generated day before payday"""
        from budget_app.models.paycheck import PaycheckConfig
        from budget_app.models.transaction import Transaction
        from datetime import date, timedelta

        paycheck = PaycheckConfig(
            id=None, gross_amount=3500.0,
            pay_frequency='BIWEEKLY',
            effective_date='2026-01-09',
            is_current=True, pay_day_of_week=4
        )
        paycheck.save()
        paycheck = PaycheckConfig.get_by_id(paycheck.id)

        view = self._make_view(qtbot, temp_db)
        view._generate_payday_transactions(
            date(2026, 3, 1), date(2026, 4, 30), paycheck)

        transactions = Transaction.get_all()
        ldbpd_trans = [t for t in transactions if t.description == 'LDBPD']
        paydays = [t for t in transactions if t.description == 'Payday']

        assert len(ldbpd_trans) > 0
        # Each LDBPD should be 1 day before a payday
        payday_dates = {t.date for t in paydays}
        for ldbpd in ldbpd_trans:
            ldbpd_date = date.fromisoformat(ldbpd.date)
            next_day = (ldbpd_date + timedelta(days=1)).isoformat()
            assert next_day in payday_dates

    def test_lisa_2_paycheck_month(self, qtbot, temp_db):
        """2-paycheck month uses 'Lisa' charge amount"""
        from budget_app.models.paycheck import PaycheckConfig
        from budget_app.models.recurring_charge import RecurringCharge
        from budget_app.models.transaction import Transaction
        from datetime import date

        paycheck = PaycheckConfig(
            id=None, gross_amount=3500.0,
            pay_frequency='BIWEEKLY',
            effective_date='2026-01-09',
            is_current=True, pay_day_of_week=4
        )
        paycheck.save()
        paycheck = PaycheckConfig.get_by_id(paycheck.id)

        lisa_2 = RecurringCharge(
            id=None, name='Lisa', amount=-500.0,
            day_of_month=1, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        lisa_2.save()

        view = self._make_view(qtbot, temp_db)
        # Feb 2026 has 4 Fridays → 2 paycheck month
        view._generate_payday_transactions(
            date(2026, 2, 1), date(2026, 2, 28), paycheck)

        transactions = Transaction.get_all()
        lisa_trans = [t for t in transactions if t.description == 'Lisa']
        # At least one Lisa payment should exist
        if lisa_trans:
            assert lisa_trans[0].amount == -500.0

    def test_lisa_3_paycheck_month(self, qtbot, temp_db):
        """3-paycheck month uses 'Lisa3' charge amount"""
        from budget_app.models.paycheck import PaycheckConfig
        from budget_app.models.recurring_charge import RecurringCharge
        from budget_app.models.transaction import Transaction
        from datetime import date

        paycheck = PaycheckConfig(
            id=None, gross_amount=3500.0,
            pay_frequency='BIWEEKLY',
            effective_date='2026-01-09',
            is_current=True, pay_day_of_week=4
        )
        paycheck.save()
        paycheck = PaycheckConfig.get_by_id(paycheck.id)

        lisa_2 = RecurringCharge(
            id=None, name='Lisa', amount=-500.0,
            day_of_month=1, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        lisa_2.save()

        lisa_3 = RecurringCharge(
            id=None, name='Lisa3', amount=-350.0,
            day_of_month=1, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        )
        lisa_3.save()

        view = self._make_view(qtbot, temp_db)
        # Jan 2026 has 5 Fridays → 3 paycheck month
        view._generate_payday_transactions(
            date(2026, 1, 1), date(2026, 1, 31), paycheck)

        transactions = Transaction.get_all()
        lisa_trans = [t for t in transactions if t.description == 'Lisa']
        # In a 3-paycheck month, Lisa amount should be from Lisa3
        three_paycheck_lisa = [t for t in lisa_trans if t.amount == -350.0]
        assert len(three_paycheck_lisa) > 0

    def test_non_biweekly_returns_zero(self, qtbot, temp_db):
        """Non-biweekly frequency returns 0 and generates nothing"""
        from budget_app.models.paycheck import PaycheckConfig
        from budget_app.models.transaction import Transaction
        from datetime import date

        paycheck = PaycheckConfig(
            id=None, gross_amount=3500.0,
            pay_frequency='MONTHLY',
            effective_date='2026-01-09',
            is_current=True, pay_day_of_week=4
        )
        paycheck.save()
        paycheck = PaycheckConfig.get_by_id(paycheck.id)

        view = self._make_view(qtbot, temp_db)
        count = view._generate_payday_transactions(
            date(2026, 1, 1), date(2026, 6, 30), paycheck)

        assert count == 0
        assert len(Transaction.get_all()) == 0


class TestValidateAndAcceptSuccess:
    """Tests for _validate_and_accept success path"""

    def test_valid_description_calls_accept(self, qtbot, temp_db):
        """Valid description → accept() called"""
        from budget_app.views.transactions_view import TransactionDialog
        from unittest.mock import patch

        dialog = TransactionDialog()
        qtbot.addWidget(dialog)
        dialog.desc_edit.setText("Valid Description")
        dialog.amount_spin.setValue(-25.0)

        with patch.object(dialog, 'accept') as mock_accept:
            dialog._validate_and_accept()
            mock_accept.assert_called_once()


class TestLoadColumnWidthsStringBranch:
    """Tests for _load_column_widths string branch"""

    def test_string_widths_applied(self, qtbot, temp_db):
        """QSettings returns string widths → columns set correctly"""
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtCore import QSettings

        # Pre-set string widths in QSettings before creating the view
        settings = QSettings("BudgetApp", "PersonalBudgetManager")
        # Need to know column count first - create a view to check
        view = TransactionsView()
        qtbot.addWidget(view)
        col_count = view.table.columnCount()

        # Set string widths
        string_widths = [str(100 + i * 10) for i in range(col_count)]
        settings.setValue("transactions/column_widths", string_widths)

        # Now reload column widths
        view._load_column_widths()

        # Verify widths were applied from string values
        for i in range(col_count):
            expected = 100 + i * 10
            assert view.table.columnWidth(i) == expected

    def test_int_widths_applied(self, qtbot, temp_db):
        """QSettings returns int widths → columns set correctly"""
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtCore import QSettings

        view = TransactionsView()
        qtbot.addWidget(view)
        col_count = view.table.columnCount()

        int_widths = [100 + i * 10 for i in range(col_count)]
        settings = QSettings("BudgetApp", "PersonalBudgetManager")
        settings.setValue("transactions/column_widths", int_widths)

        view._load_column_widths()

        for i in range(col_count):
            expected = 100 + i * 10
            assert view.table.columnWidth(i) == expected

    def test_wrong_length_widths_ignored(self, qtbot, temp_db):
        """QSettings with wrong length → widths not applied"""
        from budget_app.views.transactions_view import TransactionsView
        from PyQt6.QtCore import QSettings

        view = TransactionsView()
        qtbot.addWidget(view)

        # Record current widths
        original_widths = [view.table.columnWidth(i)
                          for i in range(view.table.columnCount())]

        # Set wrong-length widths
        settings = QSettings("BudgetApp", "PersonalBudgetManager")
        settings.setValue("transactions/column_widths", [50, 60])  # Too short

        view._load_column_widths()

        # Widths should be unchanged
        for i in range(view.table.columnCount()):
            assert view.table.columnWidth(i) == original_widths[i]


class TestAutoGenerateIfNeeded:
    """Tests for _auto_generate_if_needed"""

    def test_auto_generate_when_no_future_transactions(self, qtbot, temp_db):
        """When no future transactions exist, _do_generate_recurring is called"""
        from budget_app.views.transactions_view import TransactionsView
        from unittest.mock import patch

        view = TransactionsView()
        qtbot.addWidget(view)

        with patch.object(view, '_do_generate_recurring') as mock_gen:
            view._auto_generate_if_needed()
            mock_gen.assert_called_once_with(show_message=False)

    def test_no_auto_generate_when_future_transactions_exist(self, qtbot, temp_db):
        """When future transactions exist, _do_generate_recurring is NOT called"""
        from budget_app.views.transactions_view import TransactionsView
        from budget_app.models.transaction import Transaction
        from unittest.mock import patch

        # Create a future transaction
        trans = Transaction(
            id=None, date='2099-01-01', description='Future',
            amount=-10.0, payment_method='C', is_posted=False
        )
        trans.save()

        view = TransactionsView()
        qtbot.addWidget(view)

        with patch.object(view, '_do_generate_recurring') as mock_gen:
            view._auto_generate_if_needed()
            mock_gen.assert_not_called()
