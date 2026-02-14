"""Unit tests for Dashboard view and dialogs"""

import pytest
from PyQt6.QtGui import QColor


class TestDashboardView:
    """Tests for DashboardView"""

    def test_renders_on_empty_db(self, qtbot, temp_db):
        from budget_app.views.dashboard_view import DashboardView
        view = DashboardView()
        qtbot.addWidget(view)
        assert view.cards_table.rowCount() == 0
        assert view.loans_table.rowCount() == 0

    def test_mark_dirty(self, qtbot, temp_db):
        from budget_app.views.dashboard_view import DashboardView
        view = DashboardView()
        qtbot.addWidget(view)
        assert view._data_dirty is False  # refresh() clears it
        view.mark_dirty()
        assert view._data_dirty is True

    def test_cards_table_populates_with_sample_card(self, qtbot, temp_db, sample_card):
        from budget_app.views.dashboard_view import DashboardView
        view = DashboardView()
        qtbot.addWidget(view)
        assert view.cards_table.rowCount() == 1
        assert view.cards_table.columnCount() == 8
        assert view.cards_table.item(0, 0).text() == 'Chase Freedom'
        assert '$3,000.00' in view.cards_table.item(0, 1).text()
        assert '$10,000.00' in view.cards_table.item(0, 2).text()
        assert '$7,000.00' in view.cards_table.item(0, 3).text()
        assert '30.0%' in view.cards_table.item(0, 4).text()
        assert '18.99%' in view.cards_table.item(0, 6).text()
        assert view.cards_table.item(0, 7).text() == '15'

    def test_cards_table_utilization_red_above_80(self, qtbot, temp_db, multiple_cards):
        from budget_app.views.dashboard_view import DashboardView
        view = DashboardView()
        qtbot.addWidget(view)
        # Amex Blue: 4500/5000 = 90% -> red
        # Find the Amex Blue row
        for row in range(view.cards_table.rowCount()):
            if view.cards_table.item(row, 0).text() == 'Amex Blue':
                util_item = view.cards_table.item(row, 4)
                assert util_item.foreground().color() == QColor("#f44336")
                break
        else:
            pytest.fail("Amex Blue card not found in table")

    def test_cards_table_utilization_orange_above_50(self, qtbot, temp_db):
        from budget_app.models.credit_card import CreditCard
        from budget_app.views.dashboard_view import DashboardView
        CreditCard(id=None, pay_type_code='OR', name='Orange Card',
                   credit_limit=10000, current_balance=6000,
                   interest_rate=0.20, due_day=10).save()
        view = DashboardView()
        qtbot.addWidget(view)
        util_item = view.cards_table.item(0, 4)
        assert util_item.foreground().color() == QColor("#ff9800")

    def test_cards_table_utilization_yellow_above_30(self, qtbot, temp_db, multiple_cards):
        from budget_app.views.dashboard_view import DashboardView
        view = DashboardView()
        qtbot.addWidget(view)
        # Discover: 3200/8000 = 40% -> yellow
        for row in range(view.cards_table.rowCount()):
            if view.cards_table.item(row, 0).text() == 'Discover':
                util_item = view.cards_table.item(row, 4)
                assert util_item.foreground().color() == QColor("#ffeb3b")
                break
        else:
            pytest.fail("Discover card not found in table")

    def test_cards_table_utilization_green_at_or_below_30(self, qtbot, temp_db, multiple_cards):
        from budget_app.views.dashboard_view import DashboardView
        view = DashboardView()
        qtbot.addWidget(view)
        # Citi: 0/15000 = 0% -> green
        for row in range(view.cards_table.rowCount()):
            if view.cards_table.item(row, 0).text() == 'Citi':
                util_item = view.cards_table.item(row, 4)
                assert util_item.foreground().color() == QColor("#4caf50")
                break
        else:
            pytest.fail("Citi card not found in table")

    def test_loans_table_populates_with_sample_loan(self, qtbot, temp_db, sample_loan):
        from budget_app.views.dashboard_view import DashboardView
        view = DashboardView()
        qtbot.addWidget(view)
        assert view.loans_table.rowCount() == 1
        assert view.loans_table.columnCount() == 5
        assert view.loans_table.item(0, 0).text() == '401k Loan 1'
        assert '$7,500.00' in view.loans_table.item(0, 1).text()
        assert '$10,000.00' in view.loans_table.item(0, 2).text()
        assert '$200.00' in view.loans_table.item(0, 3).text()
        assert '4.50%' in view.loans_table.item(0, 4).text()

    def test_90_day_alert_no_checking_shows_na(self, qtbot, temp_db):
        from budget_app.views.dashboard_view import DashboardView
        view = DashboardView()
        qtbot.addWidget(view)
        assert view.min_balance_label.text() == "N/A"
        assert "No checking account" in view.min_date_label.text()

    def test_90_day_alert_positive_balance_shows_green(self, qtbot, temp_db, sample_account):
        from budget_app.views.dashboard_view import DashboardView
        view = DashboardView()
        qtbot.addWidget(view)
        assert "No negative balance" in view.min_balance_label.text()
        assert "color: #4caf50" in view.min_balance_label.styleSheet()

    def test_utilization_bar_empty_db(self, qtbot, temp_db):
        from budget_app.views.dashboard_view import DashboardView
        view = DashboardView()
        qtbot.addWidget(view)
        assert view.total_util_bar.value() == 0
        assert '$0.00' in view.total_util_label.text()

    def test_utilization_bar_with_card(self, qtbot, temp_db, sample_card):
        from budget_app.views.dashboard_view import DashboardView
        view = DashboardView()
        qtbot.addWidget(view)
        # 3000/10000 = 30%
        assert view.total_util_bar.value() == 30
        assert '$3,000.00' in view.total_util_label.text()
        assert '$10,000.00' in view.total_util_label.text()
        assert '30.0%' in view.total_util_label.text()

    def test_utilization_bar_color_green(self, qtbot, temp_db, sample_card):
        from budget_app.views.dashboard_view import DashboardView
        view = DashboardView()
        qtbot.addWidget(view)
        # 30% -> green
        assert "#4caf50" in view.total_util_bar.styleSheet()

    def test_account_balance_color_negative_red(self, qtbot, temp_db):
        from budget_app.models.account import Account
        from budget_app.views.dashboard_view import DashboardView
        Account(id=None, name='Overdrawn', account_type='CHECKING',
                current_balance=-500.0, pay_type_code='OD').save()
        view = DashboardView()
        qtbot.addWidget(view)
        # Find the balance button in accounts layout
        container = view.accounts_layout.itemAt(0).widget()
        btn = container.layout().itemAt(2).widget()  # name_label, stretch, balance_btn
        assert "#f44336" in btn.styleSheet()

    def test_account_balance_color_positive_green(self, qtbot, temp_db, sample_account):
        from budget_app.views.dashboard_view import DashboardView
        view = DashboardView()
        qtbot.addWidget(view)
        # sample_account has $5000 (>$1000) -> green
        container = view.accounts_layout.itemAt(0).widget()
        btn = container.layout().itemAt(2).widget()
        assert "#4caf50" in btn.styleSheet()

    def test_account_balance_low_no_color(self, qtbot, temp_db):
        """Balance between 0 and 1000 gets no color, just text-align: right"""
        from budget_app.models.account import Account
        from budget_app.views.dashboard_view import DashboardView
        Account(id=None, name='Low Balance', account_type='CHECKING',
                current_balance=500.0, pay_type_code='LB').save()
        view = DashboardView()
        qtbot.addWidget(view)
        container = view.accounts_layout.itemAt(0).widget()
        btn = container.layout().itemAt(2).widget()
        assert "text-align: right" in btn.styleSheet()
        assert "#f44336" not in btn.styleSheet()
        assert "#4caf50" not in btn.styleSheet()

    def test_account_balance_zero_no_color(self, qtbot, temp_db):
        """Balance of exactly 0 gets no color, just text-align: right"""
        from budget_app.models.account import Account
        from budget_app.views.dashboard_view import DashboardView
        Account(id=None, name='Zero Balance', account_type='SAVINGS',
                current_balance=0.0, pay_type_code='ZB').save()
        view = DashboardView()
        qtbot.addWidget(view)
        container = view.accounts_layout.itemAt(0).widget()
        btn = container.layout().itemAt(2).widget()
        assert "text-align: right" in btn.styleSheet()
        assert "#f44336" not in btn.styleSheet()
        assert "#4caf50" not in btn.styleSheet()

    def test_refresh_twice_clears_and_rebuilds(self, qtbot, temp_db, sample_account, sample_card):
        """Calling refresh twice should clear old widgets via deleteLater and rebuild"""
        from budget_app.views.dashboard_view import DashboardView
        view = DashboardView()
        qtbot.addWidget(view)
        # Constructor already called refresh() once with account data present.
        # Count widgets before second refresh (excluding the stretch spacer).
        initial_count = view.accounts_layout.count()
        assert initial_count > 0
        # Second refresh triggers the while-loop clearing branch (line 149)
        view.refresh()
        # Cards table should still have exactly 1 row, not duplicated
        assert view.cards_table.rowCount() == 1
        # Accounts layout should have the same count (rebuilt, not doubled)
        assert view.accounts_layout.count() == initial_count

    def test_utilization_bar_color_red_above_80(self, qtbot, temp_db):
        """When overall utilization > 80%, progress bar should use red color"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.views.dashboard_view import DashboardView
        CreditCard(id=None, pay_type_code='HI', name='High Util',
                   credit_limit=1000, current_balance=900,
                   interest_rate=0.20, due_day=15).save()
        view = DashboardView()
        qtbot.addWidget(view)
        # 900/1000 = 90% -> red
        assert view.total_util_bar.value() == 90
        assert "#f44336" in view.total_util_bar.styleSheet()

    def test_utilization_bar_color_orange_above_50(self, qtbot, temp_db):
        """When overall utilization > 50%, progress bar should use orange color"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.views.dashboard_view import DashboardView
        CreditCard(id=None, pay_type_code='MD', name='Med Util',
                   credit_limit=1000, current_balance=600,
                   interest_rate=0.20, due_day=15).save()
        view = DashboardView()
        qtbot.addWidget(view)
        # 600/1000 = 60% -> orange
        assert view.total_util_bar.value() == 60
        assert "#ff9800" in view.total_util_bar.styleSheet()

    def test_utilization_bar_color_yellow_above_30(self, qtbot, temp_db):
        """When overall utilization > 30% and <= 50%, progress bar should use yellow color"""
        from budget_app.models.credit_card import CreditCard
        from budget_app.views.dashboard_view import DashboardView
        CreditCard(id=None, pay_type_code='YL', name='Yellow Util',
                   credit_limit=1000, current_balance=400,
                   interest_rate=0.20, due_day=15).save()
        view = DashboardView()
        qtbot.addWidget(view)
        # 400/1000 = 40% -> yellow
        assert view.total_util_bar.value() == 40
        assert "#ffeb3b" in view.total_util_bar.styleSheet()

    def test_90_day_alert_stays_positive_label_text(self, qtbot, temp_db, sample_account):
        """With checking account and no future transactions, date label shows stays positive"""
        from budget_app.views.dashboard_view import DashboardView
        view = DashboardView()
        qtbot.addWidget(view)
        assert "stays positive" in view.min_date_label.text()

    def test_multiple_accounts_all_displayed(self, qtbot, temp_db):
        """Multiple accounts should each get their own row in accounts layout"""
        from budget_app.models.account import Account
        from budget_app.views.dashboard_view import DashboardView
        Account(id=None, name='Checking', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()
        Account(id=None, name='Savings', account_type='SAVINGS',
                current_balance=200.0, pay_type_code='S').save()
        view = DashboardView()
        qtbot.addWidget(view)
        # Layout should have 2 account containers + 1 stretch = 3 items
        # But we just check at least 2 widget containers exist
        widget_count = 0
        for i in range(view.accounts_layout.count()):
            item = view.accounts_layout.itemAt(i)
            if item.widget():
                widget_count += 1
        assert widget_count == 2


class TestEditBalanceDialog:
    """Tests for EditBalanceDialog"""

    def test_title_includes_name(self, qtbot, temp_db):
        from budget_app.views.dashboard_view import EditBalanceDialog
        dialog = EditBalanceDialog(None, "Chase Freedom", 3000.0)
        qtbot.addWidget(dialog)
        assert "Edit Chase Freedom Balance" == dialog.windowTitle()

    def test_get_balance_returns_value(self, qtbot, temp_db):
        from budget_app.views.dashboard_view import EditBalanceDialog
        dialog = EditBalanceDialog(None, "Test", 1234.56)
        qtbot.addWidget(dialog)
        assert dialog.get_balance() == 1234.56

    def test_credit_card_mode_label(self, qtbot, temp_db):
        from budget_app.views.dashboard_view import EditBalanceDialog
        dialog = EditBalanceDialog(None, "Visa", 500.0, is_credit_card=True)
        qtbot.addWidget(dialog)
        assert dialog.is_credit_card is True
        # Check that "amount owed" text appears in the form
        layout = dialog.layout()
        found_owed_label = False
        for i in range(layout.rowCount()):
            label_item = layout.itemAt(i, layout.ItemRole.LabelRole)
            if label_item and label_item.widget():
                text = label_item.widget().text()
                if "amount owed" in text:
                    found_owed_label = True
                    break
        assert found_owed_label, "Credit card dialog should show 'amount owed' label"

    def test_non_credit_card_mode_no_owed_label(self, qtbot, temp_db):
        from budget_app.views.dashboard_view import EditBalanceDialog
        dialog = EditBalanceDialog(None, "Savings", 2000.0, is_credit_card=False)
        qtbot.addWidget(dialog)
        layout = dialog.layout()
        for i in range(layout.rowCount()):
            label_item = layout.itemAt(i, layout.ItemRole.LabelRole)
            if label_item and label_item.widget():
                text = label_item.widget().text()
                assert "amount owed" not in text


class TestUpdateAllBalancesDialog:
    """Tests for UpdateAllBalancesDialog"""

    def test_creates_spinboxes_for_accounts(self, qtbot, temp_db, sample_account):
        from budget_app.views.dashboard_view import UpdateAllBalancesDialog
        dialog = UpdateAllBalancesDialog()
        qtbot.addWidget(dialog)
        assert len(dialog.account_spins) == 1
        assert sample_account.id in dialog.account_spins
        assert dialog.account_spins[sample_account.id].value() == 5000.0

    def test_creates_spinboxes_for_cards(self, qtbot, temp_db, sample_card):
        from budget_app.views.dashboard_view import UpdateAllBalancesDialog
        dialog = UpdateAllBalancesDialog()
        qtbot.addWidget(dialog)
        assert len(dialog.card_spins) == 1
        assert sample_card.id in dialog.card_spins
        assert dialog.card_spins[sample_card.id].value() == 3000.0

    def test_creates_spinboxes_for_loans(self, qtbot, temp_db, sample_loan):
        from budget_app.views.dashboard_view import UpdateAllBalancesDialog
        dialog = UpdateAllBalancesDialog()
        qtbot.addWidget(dialog)
        assert len(dialog.loan_spins) == 1
        assert sample_loan.id in dialog.loan_spins
        assert dialog.loan_spins[sample_loan.id].value() == 7500.0

    def test_save_all_updates_balances(self, qtbot, temp_db, sample_account,
                                       sample_card, sample_loan, mock_qmessagebox):
        from budget_app.models.account import Account
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.loan import Loan
        from budget_app.views.dashboard_view import UpdateAllBalancesDialog
        dialog = UpdateAllBalancesDialog()
        qtbot.addWidget(dialog)

        # Change spin values
        dialog.account_spins[sample_account.id].setValue(6000.0)
        dialog.card_spins[sample_card.id].setValue(2500.0)
        dialog.loan_spins[sample_loan.id].setValue(7000.0)

        dialog._save_all()

        # Verify DB was updated
        updated_account = Account.get_by_id(sample_account.id)
        assert updated_account.current_balance == 6000.0
        updated_card = CreditCard.get_by_id(sample_card.id)
        assert updated_card.current_balance == 2500.0
        updated_loan = Loan.get_by_id(sample_loan.id)
        assert updated_loan.current_balance == 7000.0

    def test_empty_db_no_spinboxes(self, qtbot, temp_db):
        from budget_app.views.dashboard_view import UpdateAllBalancesDialog
        dialog = UpdateAllBalancesDialog()
        qtbot.addWidget(dialog)
        assert len(dialog.account_spins) == 0
        assert len(dialog.card_spins) == 0
        assert len(dialog.loan_spins) == 0
