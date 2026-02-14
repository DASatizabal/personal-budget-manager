"""Unit tests for Recurring Charges view and dialogs"""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class TestRecurringChargesView:
    """Tests for RecurringChargesView"""

    def test_empty_table_on_init(self, qtbot, temp_db):
        from budget_app.views.recurring_charges_view import RecurringChargesView
        view = RecurringChargesView()
        qtbot.addWidget(view)
        assert view.table.rowCount() == 0

    def test_table_column_count(self, qtbot, temp_db):
        from budget_app.views.recurring_charges_view import RecurringChargesView
        view = RecurringChargesView()
        qtbot.addWidget(view)
        assert view.table.columnCount() == 7

    def test_table_headers(self, qtbot, temp_db):
        from budget_app.views.recurring_charges_view import RecurringChargesView
        view = RecurringChargesView()
        qtbot.addWidget(view)
        expected = ["Name", "Amount", "Day", "Payment Method", "Frequency", "Type", "Active"]
        for i, label in enumerate(expected):
            assert view.table.horizontalHeaderItem(i).text() == label

    def test_mark_dirty_sets_flag(self, qtbot, temp_db):
        from budget_app.views.recurring_charges_view import RecurringChargesView
        view = RecurringChargesView()
        qtbot.addWidget(view)
        # After init, refresh() clears _data_dirty to False
        assert view._data_dirty is False
        view.mark_dirty()
        assert view._data_dirty is True

    def test_refresh_skips_when_not_dirty(self, qtbot, temp_db, sample_recurring_charge):
        from budget_app.views.recurring_charges_view import RecurringChargesView
        view = RecurringChargesView()
        qtbot.addWidget(view)
        # show_inactive is unchecked by default, so active charges show
        assert view.table.rowCount() == 1
        # _data_dirty should be False after init refresh
        assert view._data_dirty is False
        # Clear the table manually to prove refresh doesn't reload
        view.table.setRowCount(0)
        view.refresh(force=False)
        # Table should still be empty because refresh was skipped (not dirty)
        assert view.table.rowCount() == 0

    def test_refresh_force_reloads(self, qtbot, temp_db, sample_recurring_charge):
        from budget_app.views.recurring_charges_view import RecurringChargesView
        view = RecurringChargesView()
        qtbot.addWidget(view)
        assert view.table.rowCount() == 1
        # Clear table manually
        view.table.setRowCount(0)
        # Force refresh should reload
        view.refresh(force=True)
        assert view.table.rowCount() == 1

    def test_table_displays_charge_data(self, qtbot, temp_db, sample_recurring_charge):
        """Test that charge data is displayed correctly in the table.

        Note: sample_recurring_charge alone (without sample_card) creates only
        one recurring charge.  We avoid sample_card here because CreditCard.save()
        auto-creates a linked recurring charge, which would add an extra row.
        """
        from budget_app.views.recurring_charges_view import RecurringChargesView
        view = RecurringChargesView()
        qtbot.addWidget(view)
        assert view.table.rowCount() == 1
        assert view.table.item(0, 0).text() == 'Netflix'
        assert '$-15.99' in view.table.item(0, 1).text()
        assert view.table.item(0, 2).text() == '15'
        assert view.table.item(0, 4).text() == 'MONTHLY'
        assert view.table.item(0, 5).text() == 'FIXED'
        assert view.table.item(0, 6).text() == 'Yes'

    def test_amount_color_negative_red(self, qtbot, temp_db):
        from budget_app.models.recurring_charge import RecurringCharge
        from budget_app.views.recurring_charges_view import RecurringChargesView
        RecurringCharge(
            id=None, name='Netflix', amount=-15.99,
            day_of_month=15, payment_method='C',
            frequency='MONTHLY', amount_type='FIXED'
        ).save()
        view = RecurringChargesView()
        qtbot.addWidget(view)
        amount_item = view.table.item(0, 1)
        assert amount_item.foreground().color() == QColor("#f44336")

    def test_amount_color_positive_green(self, qtbot, temp_db):
        from budget_app.models.recurring_charge import RecurringCharge
        from budget_app.views.recurring_charges_view import RecurringChargesView
        RecurringCharge(
            id=None, name='Income', amount=500.0,
            day_of_month=1, payment_method='C',
            frequency='MONTHLY', amount_type='FIXED'
        ).save()
        view = RecurringChargesView()
        qtbot.addWidget(view)
        amount_item = view.table.item(0, 1)
        assert amount_item.foreground().color() == QColor("#4caf50")

    def test_special_day_display(self, qtbot, temp_db):
        from budget_app.models.recurring_charge import RecurringCharge
        from budget_app.views.recurring_charges_view import RecurringChargesView
        RecurringCharge(
            id=None, name='Special Charge', amount=-50.0,
            day_of_month=991, payment_method='C',
            frequency='SPECIAL', amount_type='FIXED'
        ).save()
        view = RecurringChargesView()
        qtbot.addWidget(view)
        day_item = view.table.item(0, 2)
        assert day_item.text() == 'Special (991)'

    def test_inactive_charge_display(self, qtbot, temp_db):
        from budget_app.models.recurring_charge import RecurringCharge
        from budget_app.views.recurring_charges_view import RecurringChargesView
        RecurringCharge(
            id=None, name='Old Sub', amount=-9.99,
            day_of_month=5, payment_method='C',
            frequency='MONTHLY', amount_type='FIXED',
            is_active=False
        ).save()
        view = RecurringChargesView()
        qtbot.addWidget(view)
        # By default show_inactive is unchecked, so inactive won't show
        assert view.table.rowCount() == 0
        # Check the show_inactive checkbox
        view.show_inactive.setChecked(True)
        assert view.table.rowCount() == 1
        active_item = view.table.item(0, 6)
        assert active_item.text() == 'No'
        assert active_item.foreground().color() == QColor("#808080")

    def test_get_selected_charge_id_none_when_empty(self, qtbot, temp_db):
        from budget_app.views.recurring_charges_view import RecurringChargesView
        view = RecurringChargesView()
        qtbot.addWidget(view)
        assert view._get_selected_charge_id() is None

    def test_edit_no_selection_warns(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.recurring_charges_view import RecurringChargesView
        view = RecurringChargesView()
        qtbot.addWidget(view)
        view._edit_charge()
        assert mock_qmessagebox.warning_called

    def test_delete_no_selection_warns(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.recurring_charges_view import RecurringChargesView
        view = RecurringChargesView()
        qtbot.addWidget(view)
        view._delete_charge()
        assert mock_qmessagebox.warning_called

    def test_charge_id_stored_in_user_role(self, qtbot, temp_db, sample_recurring_charge):
        from budget_app.views.recurring_charges_view import RecurringChargesView
        view = RecurringChargesView()
        qtbot.addWidget(view)
        stored_id = view.table.item(0, 0).data(Qt.ItemDataRole.UserRole)
        assert stored_id == sample_recurring_charge.id


class TestRecurringChargeDialog:
    """Tests for RecurringChargeDialog"""

    def test_title_add(self, qtbot, temp_db):
        from budget_app.views.recurring_charges_view import RecurringChargeDialog
        dialog = RecurringChargeDialog()
        qtbot.addWidget(dialog)
        assert "Add" in dialog.windowTitle()

    def test_title_edit(self, qtbot, temp_db, sample_recurring_charge):
        from budget_app.views.recurring_charges_view import RecurringChargeDialog
        dialog = RecurringChargeDialog(charge=sample_recurring_charge)
        qtbot.addWidget(dialog)
        assert "Edit" in dialog.windowTitle()

    def test_populate_fields_from_charge(self, qtbot, temp_db, sample_recurring_charge):
        from budget_app.views.recurring_charges_view import RecurringChargeDialog
        dialog = RecurringChargeDialog(charge=sample_recurring_charge)
        qtbot.addWidget(dialog)
        assert dialog.name_edit.text() == 'Netflix'
        assert dialog.amount_spin.value() == -15.99
        assert dialog.day_spin.value() == 15
        assert dialog.frequency_combo.currentText() == 'MONTHLY'
        assert dialog.type_combo.currentText() == 'FIXED'
        assert dialog.active_check.isChecked() is True

    def test_get_charge_returns_correct_model(self, qtbot, temp_db):
        from budget_app.views.recurring_charges_view import RecurringChargeDialog
        dialog = RecurringChargeDialog()
        qtbot.addWidget(dialog)
        dialog.name_edit.setText("Spotify")
        dialog.amount_spin.setValue(-9.99)
        dialog.day_spin.setValue(20)
        dialog.frequency_combo.setCurrentIndex(0)  # MONTHLY
        dialog.type_combo.setCurrentIndex(0)  # FIXED
        dialog.active_check.setChecked(True)

        charge = dialog.get_charge()
        assert charge.id is None
        assert charge.name == "Spotify"
        assert charge.amount == -9.99
        assert charge.day_of_month == 20
        assert charge.frequency == "MONTHLY"
        assert charge.amount_type == "FIXED"
        assert charge.is_active is True

    def test_validate_empty_name(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.recurring_charges_view import RecurringChargeDialog
        dialog = RecurringChargeDialog()
        qtbot.addWidget(dialog)
        dialog.name_edit.setText("")
        dialog.amount_spin.setValue(-10.0)
        dialog.day_spin.setValue(15)
        dialog._validate_and_accept()
        assert mock_qmessagebox.warning_called

    def test_validate_invalid_day_range(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.recurring_charges_view import RecurringChargeDialog
        dialog = RecurringChargeDialog()
        qtbot.addWidget(dialog)
        dialog.name_edit.setText("Test Charge")
        dialog.amount_spin.setValue(-10.0)
        dialog.day_spin.setValue(500)  # 32-990 is invalid
        dialog._validate_and_accept()
        assert mock_qmessagebox.warning_called
        assert "Day" in mock_qmessagebox.warning_text or "day" in mock_qmessagebox.warning_text

    def test_validate_cc_balance_requires_linked_card(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.recurring_charges_view import RecurringChargeDialog
        dialog = RecurringChargeDialog()
        qtbot.addWidget(dialog)
        dialog.name_edit.setText("CC Payment")
        dialog.amount_spin.setValue(-100.0)
        dialog.day_spin.setValue(15)
        dialog.type_combo.setCurrentIndex(1)  # CREDIT_CARD_BALANCE
        # linked_card_combo left at "None" (index 0, data=None)
        dialog._validate_and_accept()
        assert mock_qmessagebox.warning_called
        assert "Linked Card" in mock_qmessagebox.warning_text or "linked" in mock_qmessagebox.warning_text.lower()

    def test_type_change_enables_linked_card_combo(self, qtbot, temp_db):
        from budget_app.views.recurring_charges_view import RecurringChargeDialog
        dialog = RecurringChargeDialog()
        qtbot.addWidget(dialog)
        # Initially linked_card_combo should be disabled (type is FIXED, index 0)
        assert dialog.linked_card_combo.isEnabled() is False
        # Change to CREDIT_CARD_BALANCE (index 1)
        dialog.type_combo.setCurrentIndex(1)
        assert dialog.linked_card_combo.isEnabled() is True
        # Change back to FIXED (index 0)
        dialog.type_combo.setCurrentIndex(0)
        assert dialog.linked_card_combo.isEnabled() is False

    def test_type_change_calculated_disables_linked_card(self, qtbot, temp_db):
        from budget_app.views.recurring_charges_view import RecurringChargeDialog
        dialog = RecurringChargeDialog()
        qtbot.addWidget(dialog)
        # Change to CALCULATED (index 2)
        dialog.type_combo.setCurrentIndex(2)
        assert dialog.linked_card_combo.isEnabled() is False


class TestDeleteRecurringChargeDialog:
    """Tests for DeleteRecurringChargeDialog"""

    def test_get_action_default_keep(self, qtbot, temp_db, sample_recurring_charge):
        from budget_app.views.recurring_charges_view import DeleteRecurringChargeDialog
        dialog = DeleteRecurringChargeDialog(None, sample_recurring_charge)
        qtbot.addWidget(dialog)
        assert dialog.get_action() == "keep"

    def test_window_title(self, qtbot, temp_db, sample_recurring_charge):
        from budget_app.views.recurring_charges_view import DeleteRecurringChargeDialog
        dialog = DeleteRecurringChargeDialog(None, sample_recurring_charge)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Delete Recurring Charge"

    def test_no_linked_transactions_shows_no_radios(self, qtbot, temp_db, sample_recurring_charge):
        from budget_app.views.recurring_charges_view import DeleteRecurringChargeDialog
        dialog = DeleteRecurringChargeDialog(None, sample_recurring_charge)
        qtbot.addWidget(dialog)
        # With no linked transactions, radio buttons should not exist
        assert not hasattr(dialog, 'delete_all_radio')
        assert not hasattr(dialog, 'delete_from_radio')

    def test_linked_transactions_shows_radio_buttons(self, qtbot, temp_db, sample_recurring_charge):
        from budget_app.models.database import Database
        from budget_app.views.recurring_charges_view import DeleteRecurringChargeDialog
        # Insert a transaction linked to this recurring charge
        db = Database()
        db.execute(
            "INSERT INTO transactions (date, description, amount, payment_method, recurring_charge_id) "
            "VALUES (?, ?, ?, ?, ?)",
            ('2026-02-01', 'Netflix', -15.99, 'C', sample_recurring_charge.id)
        )
        db.commit()
        dialog = DeleteRecurringChargeDialog(None, sample_recurring_charge)
        qtbot.addWidget(dialog)
        # With linked transactions, radio buttons should exist
        assert hasattr(dialog, 'keep_radio')
        assert hasattr(dialog, 'delete_all_radio')
        assert hasattr(dialog, 'delete_from_radio')
        # keep_radio should be checked by default
        assert dialog.keep_radio.isChecked() is True

    def test_get_action_delete_all(self, qtbot, temp_db, sample_recurring_charge):
        from budget_app.models.database import Database
        from budget_app.views.recurring_charges_view import DeleteRecurringChargeDialog
        db = Database()
        db.execute(
            "INSERT INTO transactions (date, description, amount, payment_method, recurring_charge_id) "
            "VALUES (?, ?, ?, ?, ?)",
            ('2026-02-01', 'Netflix', -15.99, 'C', sample_recurring_charge.id)
        )
        db.commit()
        dialog = DeleteRecurringChargeDialog(None, sample_recurring_charge)
        qtbot.addWidget(dialog)
        dialog.delete_all_radio.setChecked(True)
        assert dialog.get_action() == "delete_all"

    def test_get_action_delete_from_date(self, qtbot, temp_db, sample_recurring_charge):
        from budget_app.models.database import Database
        from budget_app.views.recurring_charges_view import DeleteRecurringChargeDialog
        db = Database()
        db.execute(
            "INSERT INTO transactions (date, description, amount, payment_method, recurring_charge_id) "
            "VALUES (?, ?, ?, ?, ?)",
            ('2026-02-01', 'Netflix', -15.99, 'C', sample_recurring_charge.id)
        )
        db.commit()
        dialog = DeleteRecurringChargeDialog(None, sample_recurring_charge)
        qtbot.addWidget(dialog)
        dialog.delete_from_radio.setChecked(True)
        assert dialog.get_action() == "delete_from_date"
