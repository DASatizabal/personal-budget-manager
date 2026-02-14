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
