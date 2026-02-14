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
