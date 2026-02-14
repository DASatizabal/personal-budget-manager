"""Unit tests for Shared Expenses view and dialog"""

import pytest
from PyQt6.QtCore import Qt


class TestSharedExpensesView:
    """Tests for SharedExpensesView"""

    def test_empty_table_on_init(self, qtbot, temp_db):
        from budget_app.views.shared_expenses_view import SharedExpensesView
        view = SharedExpensesView()
        qtbot.addWidget(view)
        assert view.table.rowCount() == 0

    def test_empty_summary_labels(self, qtbot, temp_db):
        from budget_app.views.shared_expenses_view import SharedExpensesView
        view = SharedExpensesView()
        qtbot.addWidget(view)
        assert view.total_monthly_label.text() == "$0.00"
        assert view.two_paycheck_label.text() == "$0.00"
        assert view.two_per_paycheck_label.text() == "$0.00"
        assert view.three_paycheck_label.text() == "$0.00"
        assert view.three_per_paycheck_label.text() == "$0.00"

    def test_table_populates_with_expenses(self, qtbot, temp_db, sample_shared_expenses):
        from budget_app.views.shared_expenses_view import SharedExpensesView
        view = SharedExpensesView()
        qtbot.addWidget(view)
        assert view.table.rowCount() == 2

    def test_table_column_headers(self, qtbot, temp_db):
        from budget_app.views.shared_expenses_view import SharedExpensesView
        view = SharedExpensesView()
        qtbot.addWidget(view)
        expected = ["Expense", "Monthly Amount", "Split Type",
                    "2-Paycheck Split", "3-Paycheck Split"]
        for i, label in enumerate(expected):
            assert view.table.horizontalHeaderItem(i).text() == label

    def test_table_data_displayed(self, qtbot, temp_db, sample_shared_expenses):
        from budget_app.views.shared_expenses_view import SharedExpensesView
        view = SharedExpensesView()
        qtbot.addWidget(view)
        # Rows are ordered by name: Rent (row 0), Utilities (row 1)
        assert view.table.item(0, 0).text() == "Rent"
        assert "$2,000.00" in view.table.item(0, 1).text()
        assert view.table.item(0, 2).text() == "HALF"
        assert view.table.item(1, 0).text() == "Utilities"
        assert "$300.00" in view.table.item(1, 1).text()
        assert view.table.item(1, 2).text() == "THIRD"

    def test_summary_labels_with_expenses(self, qtbot, temp_db, sample_shared_expenses):
        from budget_app.views.shared_expenses_view import SharedExpensesView
        view = SharedExpensesView()
        qtbot.addWidget(view)
        # total_monthly = 2000 + 300 = 2300
        assert "$2,300.00" in view.total_monthly_label.text()
        # two_paycheck_total = get_split_amount(2)*2 for each:
        #   Rent HALF: 2000/2 * 2 = 2000
        #   Utilities THIRD: 300/3 * 2 = 200
        #   total = 2200
        assert "$2,200.00" in view.two_paycheck_label.text()
        # two_per_paycheck = 2200 / 2 = 1100
        assert "$1,100.00" in view.two_per_paycheck_label.text()
        # three_paycheck_total = get_split_amount(3)*3 for each:
        #   Rent HALF with paycheck_count=3: 2000/3 * 3 = 2000
        #   Utilities THIRD: 300/3 * 3 = 300
        #   total = 2300
        assert "$2,300.00" in view.three_paycheck_label.text()
        # three_per_paycheck = 2300 / 3 = 766.67
        assert "$766.67" in view.three_per_paycheck_label.text()

    def test_expense_id_stored_in_user_role(self, qtbot, temp_db, sample_shared_expenses):
        from budget_app.views.shared_expenses_view import SharedExpensesView
        view = SharedExpensesView()
        qtbot.addWidget(view)
        stored_id = view.table.item(0, 0).data(Qt.ItemDataRole.UserRole)
        assert stored_id == sample_shared_expenses[0].id

    def test_edit_no_selection_warns(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.shared_expenses_view import SharedExpensesView
        view = SharedExpensesView()
        qtbot.addWidget(view)
        view._edit_expense()
        assert mock_qmessagebox.warning_called
        assert "select" in mock_qmessagebox.warning_text.lower()

    def test_delete_no_selection_warns(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.shared_expenses_view import SharedExpensesView
        view = SharedExpensesView()
        qtbot.addWidget(view)
        view._delete_expense()
        assert mock_qmessagebox.warning_called
        assert "select" in mock_qmessagebox.warning_text.lower()


class TestSharedExpenseDialog:
    """Tests for SharedExpenseDialog"""

    def test_title_add(self, qtbot, temp_db):
        from budget_app.views.shared_expenses_view import SharedExpenseDialog
        dialog = SharedExpenseDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Add Shared Expense"

    def test_title_edit(self, qtbot, temp_db, sample_shared_expenses):
        from budget_app.views.shared_expenses_view import SharedExpenseDialog
        dialog = SharedExpenseDialog(expense=sample_shared_expenses[0])
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Edit Shared Expense"

    def test_populate_fields_half(self, qtbot, temp_db, sample_shared_expenses):
        from budget_app.views.shared_expenses_view import SharedExpenseDialog
        rent = sample_shared_expenses[0]  # Rent, $2000, HALF
        dialog = SharedExpenseDialog(expense=rent)
        qtbot.addWidget(dialog)
        assert dialog.name_edit.text() == "Rent"
        assert dialog.amount_spin.value() == 2000.0
        assert dialog.half_radio.isChecked()
        assert not dialog.third_radio.isChecked()
        assert not dialog.custom_radio.isChecked()

    def test_populate_fields_third(self, qtbot, temp_db, sample_shared_expenses):
        from budget_app.views.shared_expenses_view import SharedExpenseDialog
        utilities = sample_shared_expenses[1]  # Utilities, $300, THIRD
        dialog = SharedExpenseDialog(expense=utilities)
        qtbot.addWidget(dialog)
        assert dialog.name_edit.text() == "Utilities"
        assert dialog.amount_spin.value() == 300.0
        assert dialog.third_radio.isChecked()
        assert not dialog.half_radio.isChecked()
        assert not dialog.custom_radio.isChecked()

    def test_get_expense_half(self, qtbot, temp_db):
        from budget_app.views.shared_expenses_view import SharedExpenseDialog
        dialog = SharedExpenseDialog()
        qtbot.addWidget(dialog)
        dialog.name_edit.setText("Internet")
        dialog.amount_spin.setValue(80.0)
        dialog.half_radio.setChecked(True)

        expense = dialog.get_expense()
        assert expense.name == "Internet"
        assert expense.monthly_amount == 80.0
        assert expense.split_type == "HALF"
        assert expense.custom_split_ratio is None

    def test_get_expense_third(self, qtbot, temp_db):
        from budget_app.views.shared_expenses_view import SharedExpenseDialog
        dialog = SharedExpenseDialog()
        qtbot.addWidget(dialog)
        dialog.name_edit.setText("Groceries")
        dialog.amount_spin.setValue(600.0)
        dialog.third_radio.setChecked(True)

        expense = dialog.get_expense()
        assert expense.name == "Groceries"
        assert expense.monthly_amount == 600.0
        assert expense.split_type == "THIRD"
        assert expense.custom_split_ratio is None

    def test_get_expense_custom(self, qtbot, temp_db):
        from budget_app.views.shared_expenses_view import SharedExpenseDialog
        dialog = SharedExpenseDialog()
        qtbot.addWidget(dialog)
        dialog.name_edit.setText("Water")
        dialog.amount_spin.setValue(120.0)
        dialog.custom_radio.setChecked(True)
        dialog.custom_spin.setValue(40.0)

        expense = dialog.get_expense()
        assert expense.name == "Water"
        assert expense.monthly_amount == 120.0
        assert expense.split_type == "CUSTOM"
        assert abs(expense.custom_split_ratio - 0.40) < 0.001

    def test_preview_updates_half(self, qtbot, temp_db):
        from budget_app.views.shared_expenses_view import SharedExpenseDialog
        dialog = SharedExpenseDialog()
        qtbot.addWidget(dialog)
        dialog.half_radio.setChecked(True)
        dialog.amount_spin.setValue(1000.0)

        # HALF: split_2 = 1000/2 = 500, split_3 = 1000/3 = 333.33
        assert "$500.00" in dialog.preview_2_label.text()
        assert "$333.33" in dialog.preview_3_label.text()

    def test_preview_updates_third(self, qtbot, temp_db):
        from budget_app.views.shared_expenses_view import SharedExpenseDialog
        dialog = SharedExpenseDialog()
        qtbot.addWidget(dialog)
        dialog.third_radio.setChecked(True)
        dialog.amount_spin.setValue(900.0)

        # THIRD: split_2 = 900/3 = 300, split_3 = 900/3 = 300
        assert "$300.00" in dialog.preview_2_label.text()
        assert "$300.00" in dialog.preview_3_label.text()

    def test_preview_updates_custom(self, qtbot, temp_db):
        from budget_app.views.shared_expenses_view import SharedExpenseDialog
        dialog = SharedExpenseDialog()
        qtbot.addWidget(dialog)
        dialog.custom_radio.setChecked(True)
        dialog.custom_spin.setValue(60.0)
        dialog.amount_spin.setValue(1000.0)

        # CUSTOM: ratio=0.60, split_2 = 1000*0.60/2 = 300, split_3 = 1000*0.60/3 = 200
        assert "$300.00" in dialog.preview_2_label.text()
        assert "$200.00" in dialog.preview_3_label.text()

    def test_custom_spin_enabled_only_when_custom_radio(self, qtbot, temp_db):
        from budget_app.views.shared_expenses_view import SharedExpenseDialog
        dialog = SharedExpenseDialog()
        qtbot.addWidget(dialog)

        # Default is half_radio checked, custom_spin should be disabled
        assert dialog.half_radio.isChecked()
        assert not dialog.custom_spin.isEnabled()

        # Switch to third - still disabled
        dialog.third_radio.setChecked(True)
        assert not dialog.custom_spin.isEnabled()

        # Switch to custom - should be enabled
        dialog.custom_radio.setChecked(True)
        assert dialog.custom_spin.isEnabled()

        # Switch back to half - disabled again
        dialog.half_radio.setChecked(True)
        assert not dialog.custom_spin.isEnabled()
