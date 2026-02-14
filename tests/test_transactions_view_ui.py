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
