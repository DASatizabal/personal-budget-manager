"""Unit tests for Credit Cards view and dialogs"""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class TestCreditCardsView:
    """Tests for CreditCardsView"""

    def test_empty_table_on_init(self, qtbot, temp_db):
        from budget_app.views.credit_cards_view import CreditCardsView
        view = CreditCardsView()
        qtbot.addWidget(view)
        assert view.table.rowCount() == 0

    def test_table_column_count(self, qtbot, temp_db):
        from budget_app.views.credit_cards_view import CreditCardsView
        view = CreditCardsView()
        qtbot.addWidget(view)
        assert view.table.columnCount() == 9

    def test_table_headers(self, qtbot, temp_db):
        from budget_app.views.credit_cards_view import CreditCardsView
        view = CreditCardsView()
        qtbot.addWidget(view)
        expected = ["Code", "Name", "Balance", "Limit", "Available",
                    "Utilization", "Min Payment", "Interest Rate", "Due Day"]
        for i, label in enumerate(expected):
            assert view.table.horizontalHeaderItem(i).text() == label

    def test_refresh_populates_table(self, qtbot, temp_db, sample_card):
        from budget_app.views.credit_cards_view import CreditCardsView
        view = CreditCardsView()
        qtbot.addWidget(view)
        assert view.table.rowCount() == 1

    def test_card_data_displayed(self, qtbot, temp_db, sample_card):
        from budget_app.views.credit_cards_view import CreditCardsView
        view = CreditCardsView()
        qtbot.addWidget(view)
        assert view.table.item(0, 0).text() == 'CH'
        assert view.table.item(0, 1).text() == 'Chase Freedom'
        assert '$3,000.00' in view.table.item(0, 2).text()
        assert '$10,000.00' in view.table.item(0, 3).text()
        assert '$7,000.00' in view.table.item(0, 4).text()

    def test_utilization_color_red_above_80(self, qtbot, temp_db):
        from budget_app.models.credit_card import CreditCard
        from budget_app.views.credit_cards_view import CreditCardsView
        CreditCard(id=None, pay_type_code='HI', name='High',
                   credit_limit=1000, current_balance=850,
                   interest_rate=0.20, due_day=15).save()
        view = CreditCardsView()
        qtbot.addWidget(view)
        util_item = view.table.item(0, 5)
        assert util_item.foreground().color() == QColor("#f44336")

    def test_utilization_color_orange_above_50(self, qtbot, temp_db):
        from budget_app.models.credit_card import CreditCard
        from budget_app.views.credit_cards_view import CreditCardsView
        CreditCard(id=None, pay_type_code='MD', name='Med',
                   credit_limit=1000, current_balance=600,
                   interest_rate=0.20, due_day=15).save()
        view = CreditCardsView()
        qtbot.addWidget(view)
        util_item = view.table.item(0, 5)
        assert util_item.foreground().color() == QColor("#ff9800")

    def test_balance_over_limit_red(self, qtbot, temp_db):
        from budget_app.models.credit_card import CreditCard
        from budget_app.views.credit_cards_view import CreditCardsView
        CreditCard(id=None, pay_type_code='OV', name='Over',
                   credit_limit=1000, current_balance=1500,
                   interest_rate=0.20, due_day=15).save()
        view = CreditCardsView()
        qtbot.addWidget(view)
        balance_item = view.table.item(0, 2)
        assert balance_item.foreground().color() == QColor("#f44336")

    def test_summary_labels(self, qtbot, temp_db, multiple_cards):
        from budget_app.views.credit_cards_view import CreditCardsView
        view = CreditCardsView()
        qtbot.addWidget(view)
        # Total balance: 3000+4500+3200+0 = 10700
        assert '$10,700.00' in view.total_balance_label.text()
        # Total limit: 10000+5000+8000+15000 = 38000
        assert '$38,000.00' in view.total_limit_label.text()

    def test_card_id_stored_in_user_role(self, qtbot, temp_db, sample_card):
        from budget_app.views.credit_cards_view import CreditCardsView
        view = CreditCardsView()
        qtbot.addWidget(view)
        stored_id = view.table.item(0, 0).data(Qt.ItemDataRole.UserRole)
        assert stored_id == sample_card.id

    def test_get_selected_card_id_none_when_empty(self, qtbot, temp_db):
        from budget_app.views.credit_cards_view import CreditCardsView
        view = CreditCardsView()
        qtbot.addWidget(view)
        assert view._get_selected_card_id() is None

    def test_edit_no_selection_warns(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.credit_cards_view import CreditCardsView
        view = CreditCardsView()
        qtbot.addWidget(view)
        view._edit_card()
        assert mock_qmessagebox.warning_called

    def test_delete_no_selection_warns(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.credit_cards_view import CreditCardsView
        view = CreditCardsView()
        qtbot.addWidget(view)
        view._delete_card()
        assert mock_qmessagebox.warning_called

    def test_multiple_cards_rows(self, qtbot, temp_db, multiple_cards):
        from budget_app.views.credit_cards_view import CreditCardsView
        view = CreditCardsView()
        qtbot.addWidget(view)
        assert view.table.rowCount() == 4


class TestCreditCardDialog:
    """Tests for CreditCardDialog"""

    def test_title_new(self, qtbot, temp_db):
        from budget_app.views.credit_cards_view import CreditCardDialog
        dialog = CreditCardDialog()
        qtbot.addWidget(dialog)
        assert "Add" in dialog.windowTitle()

    def test_title_edit(self, qtbot, temp_db, sample_card):
        from budget_app.views.credit_cards_view import CreditCardDialog
        dialog = CreditCardDialog(card=sample_card)
        qtbot.addWidget(dialog)
        assert "Edit" in dialog.windowTitle()

    def test_populate_fields(self, qtbot, temp_db, sample_card):
        from budget_app.views.credit_cards_view import CreditCardDialog
        dialog = CreditCardDialog(card=sample_card)
        qtbot.addWidget(dialog)
        assert dialog.code_edit.text() == 'CH'
        assert dialog.name_edit.text() == 'Chase Freedom'
        assert dialog.limit_spin.value() == 10000.0
        assert dialog.balance_spin.value() == 3000.0
        assert abs(dialog.rate_spin.value() - 18.99) < 0.01
        assert dialog.due_day_spin.value() == 15

    def test_get_card_returns_correct_values(self, qtbot, temp_db):
        from budget_app.views.credit_cards_view import CreditCardDialog
        dialog = CreditCardDialog()
        qtbot.addWidget(dialog)
        dialog.code_edit.setText("TST")
        dialog.name_edit.setText("Test Card")
        dialog.limit_spin.setValue(5000.0)
        dialog.balance_spin.setValue(1500.0)
        dialog.rate_spin.setValue(18.99)
        dialog.due_day_spin.setValue(20)
        dialog.min_type_combo.setCurrentIndex(1)  # FIXED
        dialog.min_amount_spin.setValue(75.0)

        card = dialog.get_card()
        assert card.pay_type_code == "TST"
        assert card.name == "Test Card"
        assert card.credit_limit == 5000.0
        assert card.current_balance == 1500.0
        assert abs(card.interest_rate - 0.1899) < 0.0001
        assert card.due_day == 20
        assert card.min_payment_type == "FIXED"
        assert card.min_payment_amount == 75.0

    def test_rate_conversion(self, qtbot, temp_db):
        """Rate spin shows %, get_card returns decimal"""
        from budget_app.views.credit_cards_view import CreditCardDialog
        dialog = CreditCardDialog()
        qtbot.addWidget(dialog)
        dialog.code_edit.setText("X")
        dialog.name_edit.setText("X")
        dialog.limit_spin.setValue(1000)
        dialog.rate_spin.setValue(24.50)
        card = dialog.get_card()
        assert abs(card.interest_rate - 0.245) < 0.0001

    def test_validate_empty_code(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.credit_cards_view import CreditCardDialog
        dialog = CreditCardDialog()
        qtbot.addWidget(dialog)
        dialog.code_edit.setText("")
        dialog.name_edit.setText("Valid")
        dialog.limit_spin.setValue(5000)
        dialog._validate_and_accept()
        assert mock_qmessagebox.warning_called
        assert "Code" in mock_qmessagebox.warning_text

    def test_validate_empty_name(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.credit_cards_view import CreditCardDialog
        dialog = CreditCardDialog()
        qtbot.addWidget(dialog)
        dialog.code_edit.setText("TST")
        dialog.name_edit.setText("")
        dialog.limit_spin.setValue(5000)
        dialog._validate_and_accept()
        assert mock_qmessagebox.warning_called
        assert "Name" in mock_qmessagebox.warning_text

    def test_validate_zero_limit(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.credit_cards_view import CreditCardDialog
        dialog = CreditCardDialog()
        qtbot.addWidget(dialog)
        dialog.code_edit.setText("TST")
        dialog.name_edit.setText("Card")
        dialog.limit_spin.setValue(0)
        dialog._validate_and_accept()
        assert mock_qmessagebox.warning_called
        assert "Limit" in mock_qmessagebox.warning_text

    def test_validate_duplicate_code(self, qtbot, temp_db, sample_card, mock_qmessagebox):
        from budget_app.views.credit_cards_view import CreditCardDialog
        dialog = CreditCardDialog()
        qtbot.addWidget(dialog)
        dialog.code_edit.setText("CH")  # Same as sample_card
        dialog.name_edit.setText("New Card")
        dialog.limit_spin.setValue(5000)
        dialog._validate_and_accept()
        assert mock_qmessagebox.warning_called
        assert "already in use" in mock_qmessagebox.warning_text

    def test_min_type_enables_amount(self, qtbot, temp_db):
        from budget_app.views.credit_cards_view import CreditCardDialog
        dialog = CreditCardDialog()
        qtbot.addWidget(dialog)
        dialog.min_type_combo.setCurrentIndex(1)  # Fixed Amount
        assert dialog.min_amount_spin.isEnabled()

    def test_min_type_disables_amount(self, qtbot, temp_db):
        from budget_app.views.credit_cards_view import CreditCardDialog
        dialog = CreditCardDialog()
        qtbot.addWidget(dialog)
        dialog.min_type_combo.setCurrentIndex(0)  # Calculated
        assert not dialog.min_amount_spin.isEnabled()

    def test_min_payment_type_mapping(self, qtbot, temp_db):
        from budget_app.views.credit_cards_view import CreditCardDialog
        dialog = CreditCardDialog()
        qtbot.addWidget(dialog)
        dialog.code_edit.setText("X")
        dialog.name_edit.setText("X")
        dialog.limit_spin.setValue(1000)

        for idx, expected_type in [(0, 'CALCULATED'), (1, 'FIXED'), (2, 'FULL_BALANCE')]:
            dialog.min_type_combo.setCurrentIndex(idx)
            card = dialog.get_card()
            assert card.min_payment_type == expected_type


class TestCardDeletionDialog:
    """Tests for CardDeletionDialog"""

    def test_get_delete_transactions_default(self, qtbot, temp_db, sample_card):
        from budget_app.views.credit_cards_view import CardDeletionDialog
        dialog = CardDeletionDialog(None, sample_card, [], [])
        qtbot.addWidget(dialog)
        assert dialog.get_delete_transactions() is False

    def test_get_target_card_id_no_charges(self, qtbot, temp_db, sample_card):
        from budget_app.views.credit_cards_view import CardDeletionDialog
        dialog = CardDeletionDialog(None, sample_card, [], [])
        qtbot.addWidget(dialog)
        assert dialog.get_target_card_id() is None

    def test_dialog_title_includes_card_name(self, qtbot, temp_db, sample_card):
        from budget_app.views.credit_cards_view import CardDeletionDialog
        dialog = CardDeletionDialog(None, sample_card, [], [])
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == f"Delete {sample_card.name}"

    def test_charges_combo_appears_with_linked_charges(self, qtbot, temp_db, sample_card):
        from budget_app.views.credit_cards_view import CardDeletionDialog
        linked_charges = [{'name': 'Netflix', 'id': 1}]
        dialog = CardDeletionDialog(None, sample_card, linked_charges, [])
        qtbot.addWidget(dialog)
        assert hasattr(dialog, 'charges_combo')

    def test_charges_combo_has_unlink_option(self, qtbot, temp_db, sample_card):
        from budget_app.views.credit_cards_view import CardDeletionDialog
        linked_charges = [{'name': 'Netflix', 'id': 1}]
        dialog = CardDeletionDialog(None, sample_card, linked_charges, [])
        qtbot.addWidget(dialog)
        assert dialog.charges_combo.itemData(0) is None

    def test_charges_combo_excludes_deleted_card(self, qtbot, temp_db, multiple_cards):
        from budget_app.views.credit_cards_view import CardDeletionDialog
        linked_charges = [{'name': 'Netflix', 'id': 1}]
        card_to_delete = multiple_cards[0]
        dialog = CardDeletionDialog(None, card_to_delete, linked_charges, [])
        qtbot.addWidget(dialog)
        combo_card_ids = [
            dialog.charges_combo.itemData(i)
            for i in range(dialog.charges_combo.count())
            if dialog.charges_combo.itemData(i) is not None
        ]
        assert card_to_delete.id not in combo_card_ids
        for card in multiple_cards[1:]:
            assert card.id in combo_card_ids

    def test_transactions_section_with_transactions(self, qtbot, temp_db, sample_card):
        from budget_app.views.credit_cards_view import CardDeletionDialog
        transactions = [{'id': 1, 'date': '2026-01-01', 'description': 'Test', 'amount': -100}]
        dialog = CardDeletionDialog(None, sample_card, [], transactions)
        qtbot.addWidget(dialog)
        assert hasattr(dialog, 'trans_delete_radio')
        assert hasattr(dialog, 'trans_transfer_radio')

    def test_trans_transfer_radio_default_checked(self, qtbot, temp_db, sample_card):
        from budget_app.views.credit_cards_view import CardDeletionDialog
        transactions = [{'id': 1, 'date': '2026-01-01', 'description': 'Test', 'amount': -100}]
        dialog = CardDeletionDialog(None, sample_card, [], transactions)
        qtbot.addWidget(dialog)
        assert dialog.trans_transfer_radio.isChecked()

    def test_get_delete_transactions_when_delete_checked(self, qtbot, temp_db, sample_card):
        from budget_app.views.credit_cards_view import CardDeletionDialog
        transactions = [{'id': 1, 'date': '2026-01-01', 'description': 'Test', 'amount': -100}]
        dialog = CardDeletionDialog(None, sample_card, [], transactions)
        qtbot.addWidget(dialog)
        dialog.trans_delete_radio.setChecked(True)
        assert dialog.get_delete_transactions() is True

    def test_get_transaction_target_id_when_transfer(self, qtbot, temp_db, multiple_cards):
        from budget_app.views.credit_cards_view import CardDeletionDialog
        transactions = [{'id': 1, 'date': '2026-01-01', 'description': 'Test', 'amount': -100}]
        card_to_delete = multiple_cards[0]
        dialog = CardDeletionDialog(None, card_to_delete, [], transactions)
        qtbot.addWidget(dialog)
        dialog.trans_transfer_radio.setChecked(True)
        target_id = dialog.get_transaction_target_id()
        assert target_id is not None
        assert target_id == dialog.trans_target_combo.currentData()


class TestCreditCardsViewDelete:
    """Tests for _delete_card method"""

    @staticmethod
    def _unlink_auto_charges(card_id):
        """Remove auto-created recurring charges so delete takes the simple path"""
        from budget_app.models.database import Database
        db = Database()
        db.execute("DELETE FROM recurring_charges WHERE linked_card_id = ?", (card_id,))
        db.commit()

    def test_delete_no_linked_data_confirms_and_deletes(self, qtbot, temp_db, sample_card, mock_qmessagebox):
        """With no linked charges or transactions, simple confirm-and-delete"""
        from budget_app.views.credit_cards_view import CreditCardsView
        from budget_app.models.credit_card import CreditCard
        from PyQt6.QtWidgets import QMessageBox

        # Remove the auto-created recurring charge so the simple delete path is taken
        self._unlink_auto_charges(sample_card.id)

        view = CreditCardsView()
        qtbot.addWidget(view)
        view.table.selectRow(0)
        mock_qmessagebox.last_return = QMessageBox.StandardButton.Yes
        view._delete_card()
        assert mock_qmessagebox.question_called
        # Card should be deleted
        assert CreditCard.get_by_id(sample_card.id) is None

    def test_delete_no_linked_data_user_cancels(self, qtbot, temp_db, sample_card, mock_qmessagebox):
        """User cancels deletion, card should still exist"""
        from budget_app.views.credit_cards_view import CreditCardsView
        from budget_app.models.credit_card import CreditCard
        from PyQt6.QtWidgets import QMessageBox

        # Remove the auto-created recurring charge so the simple delete path is taken
        self._unlink_auto_charges(sample_card.id)

        view = CreditCardsView()
        qtbot.addWidget(view)
        view.table.selectRow(0)
        mock_qmessagebox.last_return = QMessageBox.StandardButton.No
        view._delete_card()
        assert CreditCard.get_by_id(sample_card.id) is not None

    def test_delete_card_not_found(self, qtbot, temp_db, sample_card, mock_qmessagebox):
        """If card was deleted between selection and delete click, graceful handling"""
        from budget_app.views.credit_cards_view import CreditCardsView

        view = CreditCardsView()
        qtbot.addWidget(view)
        view.table.selectRow(0)
        # Delete it first so get_by_id returns None
        sample_card.delete()
        view._delete_card()
        # Should not crash - early return when card not found

    def test_delete_with_linked_charges_shows_dialog(self, qtbot, temp_db, sample_card, mock_qmessagebox):
        """Card with auto-created linked charges should show CardDeletionDialog"""
        from budget_app.views.credit_cards_view import CreditCardsView

        # sample_card auto-creates a linked recurring charge, so linked_charges is non-empty
        view = CreditCardsView()
        qtbot.addWidget(view)
        view.table.selectRow(0)

        from unittest.mock import patch
        with patch('budget_app.views.credit_cards_view.CardDeletionDialog') as MockDialog:
            MockDialog.return_value.exec.return_value = 0  # Rejected
            view._delete_card()
            MockDialog.assert_called_once()

    def test_delete_with_transactions_shows_dialog(self, qtbot, temp_db, sample_card, mock_qmessagebox):
        """Card with transactions should show CardDeletionDialog"""
        from budget_app.views.credit_cards_view import CreditCardsView
        from budget_app.models.transaction import Transaction

        # Remove auto-created linked charge so we isolate the transactions path
        self._unlink_auto_charges(sample_card.id)

        # Create a transaction with the card's pay_type_code
        Transaction(id=None, date='2026-02-01', description='Test',
                    amount=-50, payment_method=sample_card.pay_type_code,
                    is_posted=False).save()

        view = CreditCardsView()
        qtbot.addWidget(view)
        view.table.selectRow(0)

        from unittest.mock import patch
        with patch('budget_app.views.credit_cards_view.CardDeletionDialog') as MockDialog:
            MockDialog.return_value.exec.return_value = 0  # Rejected
            view._delete_card()
            MockDialog.assert_called_once()


class TestCreditCardsViewNotify:
    """Tests for _notify_recurring_changes"""

    def test_notify_no_parent(self, qtbot, temp_db):
        """With no parent, should not crash"""
        from budget_app.views.credit_cards_view import CreditCardsView

        view = CreditCardsView()
        qtbot.addWidget(view)
        view._notify_recurring_changes()  # Should not crash

    def test_notify_finds_recurring_view(self, qtbot, temp_db):
        """When parent has recurring_view, it should call mark_dirty()"""
        from budget_app.views.credit_cards_view import CreditCardsView
        from PyQt6.QtWidgets import QWidget
        from unittest.mock import MagicMock

        # Create a fake parent that has a recurring_view attribute
        parent = QWidget()
        parent.recurring_view = MagicMock()
        qtbot.addWidget(parent)

        view = CreditCardsView()
        view.setParent(parent)

        view._notify_recurring_changes()
        parent.recurring_view.mark_dirty.assert_called_once()


class TestCreditCardsViewAdd:
    """Tests for _add_card with mocked dialog"""

    def test_add_card_dialog_accepted(self, qtbot, temp_db):
        """When dialog returns accepted, card is saved and table refreshes"""
        from budget_app.views.credit_cards_view import CreditCardsView
        from budget_app.models.credit_card import CreditCard
        from unittest.mock import patch
        from PyQt6.QtWidgets import QDialog

        view = CreditCardsView()
        qtbot.addWidget(view)
        assert view.table.rowCount() == 0

        mock_card = CreditCard(id=None, pay_type_code='TS', name='Test Card',
                               credit_limit=5000, current_balance=0,
                               interest_rate=0.18, due_day=10)

        with patch('budget_app.views.credit_cards_view.CreditCardDialog') as MockDialog:
            MockDialog.return_value.exec.return_value = QDialog.DialogCode.Accepted
            MockDialog.return_value.get_card.return_value = mock_card
            view._add_card()

        assert view.table.rowCount() == 1

    def test_add_card_dialog_cancelled(self, qtbot, temp_db):
        """When dialog is cancelled, no card is added"""
        from budget_app.views.credit_cards_view import CreditCardsView
        from unittest.mock import patch
        from PyQt6.QtWidgets import QDialog

        view = CreditCardsView()
        qtbot.addWidget(view)

        with patch('budget_app.views.credit_cards_view.CreditCardDialog') as MockDialog:
            MockDialog.return_value.exec.return_value = QDialog.DialogCode.Rejected
            view._add_card()

        assert view.table.rowCount() == 0


class TestCreditCardsViewEdit:
    """Tests for _edit_card with mocked dialog"""

    def test_edit_card_dialog_accepted(self, qtbot, temp_db, sample_card):
        """When edit dialog returns accepted, card is updated"""
        from budget_app.views.credit_cards_view import CreditCardsView
        from budget_app.models.credit_card import CreditCard
        from unittest.mock import patch
        from PyQt6.QtWidgets import QDialog

        view = CreditCardsView()
        qtbot.addWidget(view)
        view.table.selectRow(0)

        updated_card = CreditCard(id=None, pay_type_code='CH', name='Chase Updated',
                                  credit_limit=12000, current_balance=2500,
                                  interest_rate=0.1599, due_day=20)

        with patch('budget_app.views.credit_cards_view.CreditCardDialog') as MockDialog:
            MockDialog.return_value.exec.return_value = QDialog.DialogCode.Accepted
            MockDialog.return_value.get_card.return_value = updated_card
            view._edit_card()

        # Verify the card was updated in the database
        saved = CreditCard.get_by_id(sample_card.id)
        assert saved.name == 'Chase Updated'
        assert saved.credit_limit == 12000
        assert saved.due_day == 20

    def test_edit_card_dialog_cancelled(self, qtbot, temp_db, sample_card):
        """When edit dialog is cancelled, card is unchanged"""
        from budget_app.views.credit_cards_view import CreditCardsView
        from budget_app.models.credit_card import CreditCard
        from unittest.mock import patch
        from PyQt6.QtWidgets import QDialog

        view = CreditCardsView()
        qtbot.addWidget(view)
        view.table.selectRow(0)

        with patch('budget_app.views.credit_cards_view.CreditCardDialog') as MockDialog:
            MockDialog.return_value.exec.return_value = QDialog.DialogCode.Rejected
            view._edit_card()

        # Card should remain unchanged
        saved = CreditCard.get_by_id(sample_card.id)
        assert saved.name == 'Chase Freedom'
        assert saved.credit_limit == 10000
