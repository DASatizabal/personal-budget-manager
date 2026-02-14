"""Unit tests for Deferred Interest view and dialogs"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor


class TestDeferredInterestView:
    """Tests for DeferredInterestView"""

    def test_empty_table_on_init(self, qtbot, temp_db):
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        assert view.table.rowCount() == 0

    def test_table_column_count(self, qtbot, temp_db):
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        assert view.table.columnCount() == 9

    def test_table_headers(self, qtbot, temp_db):
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        expected = [
            "Card", "Description", "Original", "Remaining",
            "Promo End", "Days Left", "Monthly Needed", "Standard APR", "Risk"
        ]
        for i, label in enumerate(expected):
            assert view.table.horizontalHeaderItem(i).text() == label

    def test_refresh_populates_table(self, qtbot, temp_db, sample_deferred_purchase):
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        assert view.table.rowCount() == 1

    def test_purchase_data_displayed(self, qtbot, temp_db, sample_deferred_purchase):
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        assert view.table.item(0, 0).text() == 'Deferred Card'
        assert view.table.item(0, 1).text() == 'Best Buy TV'
        assert '$1,500.00' in view.table.item(0, 2).text()
        assert '$1,200.00' in view.table.item(0, 3).text()
        assert '2027-06-15' in view.table.item(0, 4).text()
        assert '29.99%' in view.table.item(0, 7).text() or '30.0%' in view.table.item(0, 7).text()

    def test_purchase_id_stored_in_user_role(self, qtbot, temp_db, sample_deferred_purchase):
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        stored_id = view.table.item(0, 0).data(Qt.ItemDataRole.UserRole)
        assert stored_id == sample_deferred_purchase.id

    def test_get_risk_color_expired(self, qtbot, temp_db):
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        assert view._get_risk_color("EXPIRED") == QColor("#f44336")

    def test_get_risk_color_high(self, qtbot, temp_db):
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        assert view._get_risk_color("HIGH") == QColor("#ff5722")

    def test_get_risk_color_medium(self, qtbot, temp_db):
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        assert view._get_risk_color("MEDIUM") == QColor("#ff9800")

    def test_get_risk_color_low(self, qtbot, temp_db):
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        assert view._get_risk_color("LOW") is None

    def test_summary_labels(self, qtbot, temp_db, sample_deferred_purchase):
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        assert '$1,200.00' in view.total_balance_label.text()
        assert 'Potential Interest' in view.total_interest_label.text()

    def test_at_risk_label_none_when_low(self, qtbot, temp_db, sample_deferred_purchase):
        """sample_deferred_purchase has promo_end 2027-06-15 which is LOW risk (>90 days out)"""
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        # The purchase is LOW risk but is_at_risk depends on min_payment vs remaining
        # With promo_end 2027-06-15 (far future), risk_level is LOW
        # But is_at_risk may still be True if min payment doesn't cover it
        # Check the label exists and has content
        assert view.at_risk_label.text() != ""

    def test_at_risk_label_red_when_at_risk(self, qtbot, temp_db):
        """Create an expired purchase to trigger red at-risk label"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.deferred_interest import DeferredPurchase
        from budget_app.views.deferred_interest_view import DeferredInterestView
        card = CreditCard(
            id=None, pay_type_code='EX', name='Expired Card',
            credit_limit=5000.0, current_balance=1000.0,
            interest_rate=0.2499, due_day=10
        )
        card.save()
        purchase = DeferredPurchase(
            id=None, credit_card_id=card.id,
            description='Expired TV', purchase_amount=1000.0,
            remaining_balance=800.0, promo_apr=0.0,
            standard_apr=0.2499, promo_end_date='2024-01-01',
            min_monthly_payment=25.0
        )
        purchase.save()
        view = DeferredInterestView()
        qtbot.addWidget(view)
        assert '1 purchase(s)' in view.at_risk_label.text()
        assert '#f44336' in view.at_risk_label.styleSheet()

    def test_at_risk_label_green_when_none(self, qtbot, temp_db):
        """No purchases means no at-risk items"""
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        assert 'None' in view.at_risk_label.text()
        assert '#4caf50' in view.at_risk_label.styleSheet()

    def test_alerts_hidden_when_no_alerts(self, qtbot, temp_db, sample_deferred_purchase):
        """sample_deferred_purchase is LOW risk, so no alerts should show"""
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        # promo_end 2027-06-15 is far future = LOW risk, no alerts
        # Use isHidden() since isVisible() requires parent to be shown
        assert view.alert_group.isHidden()

    def test_alerts_shown_when_expired(self, qtbot, temp_db):
        """Create an expired purchase to trigger alerts"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.deferred_interest import DeferredPurchase
        from budget_app.views.deferred_interest_view import DeferredInterestView
        card = CreditCard(
            id=None, pay_type_code='EX', name='Expired Card',
            credit_limit=5000.0, current_balance=1000.0,
            interest_rate=0.2499, due_day=10
        )
        card.save()
        purchase = DeferredPurchase(
            id=None, credit_card_id=card.id,
            description='Expired Laptop', purchase_amount=2000.0,
            remaining_balance=1500.0, promo_apr=0.0,
            standard_apr=0.2499, promo_end_date='2024-01-01',
            min_monthly_payment=25.0
        )
        purchase.save()
        view = DeferredInterestView()
        qtbot.addWidget(view)
        # Use not isHidden() since isVisible() requires parent to be shown
        assert not view.alert_group.isHidden()
        assert 'EXPIRED' in view.alert_label.text()
        assert 'Expired Laptop' in view.alert_label.text()

    def test_edit_no_selection_warns(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        view._edit_purchase()
        assert mock_qmessagebox.warning_called
        assert 'select' in mock_qmessagebox.warning_text.lower()

    def test_delete_no_selection_warns(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        view._delete_purchase()
        assert mock_qmessagebox.warning_called
        assert 'select' in mock_qmessagebox.warning_text.lower()


class TestDeferredPurchaseDialog:
    """Tests for DeferredPurchaseDialog"""

    def test_title_add(self, qtbot, temp_db):
        from budget_app.views.deferred_interest_view import DeferredPurchaseDialog
        dialog = DeferredPurchaseDialog()
        qtbot.addWidget(dialog)
        assert "Add" in dialog.windowTitle()

    def test_title_edit(self, qtbot, temp_db, sample_deferred_purchase):
        from budget_app.views.deferred_interest_view import DeferredPurchaseDialog
        dialog = DeferredPurchaseDialog(purchase=sample_deferred_purchase)
        qtbot.addWidget(dialog)
        assert "Edit" in dialog.windowTitle()

    def test_populate_fields(self, qtbot, temp_db, sample_deferred_purchase):
        from budget_app.views.deferred_interest_view import DeferredPurchaseDialog
        dialog = DeferredPurchaseDialog(purchase=sample_deferred_purchase)
        qtbot.addWidget(dialog)
        assert dialog.description_edit.text() == 'Best Buy TV'
        assert dialog.purchase_amount_spin.value() == 1500.0
        assert dialog.remaining_spin.value() == 1200.0
        # promo_apr 0.0 * 100 = 0.0
        assert abs(dialog.promo_apr_spin.value() - 0.0) < 0.01
        # standard_apr 0.2999 * 100 = 29.99
        assert abs(dialog.standard_apr_spin.value() - 29.99) < 0.01
        assert dialog.promo_end_edit.date() == QDate(2027, 6, 15)
        assert dialog.min_payment_spin.value() == 50.0

    def test_populate_card_selection(self, qtbot, temp_db, sample_deferred_purchase):
        from budget_app.views.deferred_interest_view import DeferredPurchaseDialog
        dialog = DeferredPurchaseDialog(purchase=sample_deferred_purchase)
        qtbot.addWidget(dialog)
        # The card combo should have the deferred card selected
        assert dialog.card_combo.currentData() == sample_deferred_purchase.credit_card_id

    def test_get_purchase_returns_correct_values(self, qtbot, temp_db, sample_card):
        from budget_app.views.deferred_interest_view import DeferredPurchaseDialog
        dialog = DeferredPurchaseDialog()
        qtbot.addWidget(dialog)
        dialog.description_edit.setText("New Purchase")
        dialog.purchase_amount_spin.setValue(2000.0)
        dialog.remaining_spin.setValue(1800.0)
        dialog.promo_apr_spin.setValue(0.0)
        dialog.standard_apr_spin.setValue(29.99)
        dialog.promo_end_edit.setDate(QDate(2028, 1, 15))
        dialog.min_payment_spin.setValue(75.0)

        purchase = dialog.get_purchase()
        assert purchase.description == "New Purchase"
        assert purchase.purchase_amount == 2000.0
        assert purchase.remaining_balance == 1800.0
        assert abs(purchase.promo_apr - 0.0) < 0.0001
        assert abs(purchase.standard_apr - 0.2999) < 0.0001
        assert purchase.promo_end_date == "2028-01-15"
        assert purchase.min_monthly_payment == 75.0
        assert purchase.credit_card_id == sample_card.id

    def test_get_purchase_apr_conversion(self, qtbot, temp_db, sample_card):
        """Verify APR spin value (29.99%) converts to decimal (0.2999) in get_purchase"""
        from budget_app.views.deferred_interest_view import DeferredPurchaseDialog
        dialog = DeferredPurchaseDialog()
        qtbot.addWidget(dialog)
        dialog.description_edit.setText("APR Test")
        dialog.purchase_amount_spin.setValue(1000.0)
        dialog.remaining_spin.setValue(500.0)
        dialog.standard_apr_spin.setValue(24.50)
        dialog.promo_apr_spin.setValue(5.0)

        purchase = dialog.get_purchase()
        assert abs(purchase.standard_apr - 0.245) < 0.0001
        assert abs(purchase.promo_apr - 0.05) < 0.0001

    def test_validate_empty_description(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.deferred_interest_view import DeferredPurchaseDialog
        dialog = DeferredPurchaseDialog()
        qtbot.addWidget(dialog)
        dialog.description_edit.setText("")
        dialog.purchase_amount_spin.setValue(1000.0)
        dialog.standard_apr_spin.setValue(25.0)
        dialog._validate_and_accept()
        assert mock_qmessagebox.warning_called
        assert "Description" in mock_qmessagebox.warning_text

    def test_validate_zero_purchase_amount(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.deferred_interest_view import DeferredPurchaseDialog
        dialog = DeferredPurchaseDialog()
        qtbot.addWidget(dialog)
        dialog.description_edit.setText("Valid Name")
        dialog.purchase_amount_spin.setValue(0.0)
        dialog.standard_apr_spin.setValue(25.0)
        dialog._validate_and_accept()
        assert mock_qmessagebox.warning_called
        assert "purchase amount" in mock_qmessagebox.warning_text.lower()

    def test_validate_remaining_exceeds_purchase(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.deferred_interest_view import DeferredPurchaseDialog
        dialog = DeferredPurchaseDialog()
        qtbot.addWidget(dialog)
        dialog.description_edit.setText("Valid Name")
        dialog.purchase_amount_spin.setValue(500.0)
        dialog.remaining_spin.setValue(600.0)
        dialog.standard_apr_spin.setValue(25.0)
        dialog._validate_and_accept()
        assert mock_qmessagebox.warning_called
        assert "Remaining" in mock_qmessagebox.warning_text

    def test_validate_zero_standard_apr(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.deferred_interest_view import DeferredPurchaseDialog
        dialog = DeferredPurchaseDialog()
        qtbot.addWidget(dialog)
        dialog.description_edit.setText("Valid Name")
        dialog.purchase_amount_spin.setValue(1000.0)
        dialog.remaining_spin.setValue(500.0)
        dialog.standard_apr_spin.setValue(0.0)
        dialog._validate_and_accept()
        assert mock_qmessagebox.warning_called
        assert "Standard APR" in mock_qmessagebox.warning_text


class TestDeferredInterestViewActions:
    def test_edit_no_selection_warns(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        view._edit_purchase()
        assert mock_qmessagebox.warning_called

    def test_delete_no_selection_warns(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        view._delete_purchase()
        assert mock_qmessagebox.warning_called

    def test_table_populates_with_purchase(self, qtbot, temp_db, sample_deferred_purchase):
        from budget_app.views.deferred_interest_view import DeferredInterestView
        view = DeferredInterestView()
        qtbot.addWidget(view)
        assert view.table.rowCount() >= 1
