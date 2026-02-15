"""Tests for budget_app/views/pdf_import_view.py"""

import pytest
from unittest.mock import patch, MagicMock

from PyQt6.QtGui import QColor

from budget_app.utils.statement_parser import StatementData, TransactionEntry


MODULE = 'budget_app.views.pdf_import_view'


def _make_cc_statement():
    """Create a representative credit card StatementData."""
    return StatementData(
        statement_type='credit_card',
        institution='Chase',
        account_last4='4830',
        statement_date='2026-01-25',
        period_start='2025-12-26',
        period_end='2026-01-25',
        previous_balance=1500.0,
        new_balance=1800.0,
        credit_limit=10000.0,
        minimum_payment=35.0,
        payment_due_date='2026-02-21',
        interest_total=22.50,
        fees_total=5.00,
        transactions=[
            TransactionEntry(
                date='2026-01-02', description='PAYMENT',
                amount=622.0, category='payment',
            ),
            TransactionEntry(
                date='2026-01-05', description='AMAZON',
                amount=-49.99, post_date='2026-01-06', category='purchase',
            ),
            TransactionEntry(
                date='2026-01-10', description='COSTCO',
                amount=-125.30, post_date='2026-01-11', category='purchase',
            ),
        ],
    )


def _make_payslip_statement():
    """Create a representative payslip StatementData."""
    return StatementData(
        statement_type='payslip',
        institution='Elevance Health',
        statement_date='2026-01-20',
        period_end='2026-01-15',
        gross_pay=3500.0,
        net_pay=2500.0,
        new_balance=2500.0,
        transactions=[
            TransactionEntry(
                date='2026-01-20', description='Direct Deposit',
                amount=2500.0, category='deposit',
            ),
        ],
    )


# ---------------------------------------------------------------------------
# TestPDFImportViewInit
# ---------------------------------------------------------------------------
class TestPDFImportViewInit:
    def test_constructs(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        assert view is not None

    def test_import_button_disabled(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        assert not view.import_btn.isEnabled()

    def test_file_label_default(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        assert view.file_label.text() == 'No file selected'

    def test_table_columns(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        assert view.table.columnCount() == 5
        headers = [
            view.table.horizontalHeaderItem(i).text()
            for i in range(5)
        ]
        assert headers == ['Date', 'Post Date', 'Description', 'Amount', 'Category']


# ---------------------------------------------------------------------------
# TestLoadAccounts
# ---------------------------------------------------------------------------
class TestLoadAccounts:
    def test_populates_combo(self, qtbot, temp_db, sample_account, sample_card):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._load_accounts()
        # placeholder + 1 account + 1 card = 3
        assert view.account_combo.count() == 3
        assert view.account_combo.itemData(0) is None  # placeholder
        assert view.account_combo.itemData(1) == sample_account.pay_type_code
        assert view.account_combo.itemData(2) == sample_card.pay_type_code

    def test_empty_db(self, qtbot, temp_db):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._load_accounts()
        assert view.account_combo.count() == 1  # placeholder only


# ---------------------------------------------------------------------------
# TestUpdateSummary
# ---------------------------------------------------------------------------
class TestUpdateSummary:
    def test_credit_card_labels(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._statement = _make_cc_statement()
        view._update_summary()

        assert 'Chase' in view.institution_label.text()
        assert 'credit_card' in view.type_label.text()
        assert '4830' in view.last4_label.text()
        assert '2025-12-26' in view.period_label.text()
        assert '2026-01-25' in view.period_label.text()
        assert '1,500.00' in view.prev_balance_label.text()
        assert '1,800.00' in view.new_balance_label.text()
        assert '10,000.00' in view.limit_label.text()
        assert '22.50' in view.interest_label.text()
        assert '5.00' in view.fees_label.text()
        assert '35.00' in view.min_payment_label.text()
        assert '2026-02-21' in view.due_date_label.text()
        assert view.payslip_label.text() == ''

    def test_payslip_labels(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._statement = _make_payslip_statement()
        view._update_summary()

        assert 'Gross' in view.payslip_label.text()
        assert '3,500.00' in view.payslip_label.text()
        assert 'Net' in view.payslip_label.text()
        assert '2,500.00' in view.payslip_label.text()

    def test_closing_date_only(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        stmt = StatementData(period_end='2026-01-25')
        view._statement = stmt
        view._update_summary()
        assert 'Closing' in view.period_label.text()

    def test_no_period(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._statement = StatementData()
        view._update_summary()
        assert view.period_label.text() == 'Period: —'

    def test_no_credit_limit(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._statement = StatementData(credit_limit=0)
        view._update_summary()
        assert view.limit_label.text() == 'Credit Limit: —'

    def test_no_min_payment(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._statement = StatementData(minimum_payment=0)
        view._update_summary()
        assert view.min_payment_label.text() == 'Min Payment: —'

    def test_no_due_date(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._statement = StatementData(payment_due_date='')
        view._update_summary()
        assert view.due_date_label.text() == 'Due Date: —'

    def test_no_statement_noop(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._statement = None
        view._update_summary()  # should not crash
        assert view.institution_label.text() == 'Institution: —'


# ---------------------------------------------------------------------------
# TestAutoMatchAccount
# ---------------------------------------------------------------------------
class TestAutoMatchAccount:
    def test_match_found(self, qtbot, temp_db, sample_account, sample_card):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._statement = _make_cc_statement()
        view._load_accounts()

        with patch(f'{MODULE}.match_account', return_value=sample_card.pay_type_code):
            view._auto_match_account()

        assert view.account_combo.currentData() == sample_card.pay_type_code
        assert 'auto-matched' in view.auto_match_label.text()

    def test_no_match(self, qtbot, temp_db, sample_account):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._statement = _make_cc_statement()
        view._load_accounts()

        with patch(f'{MODULE}.match_account', return_value=None):
            view._auto_match_account()

        assert 'no match found' in view.auto_match_label.text()

    def test_no_statement_noop(self, qtbot, temp_db):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._statement = None
        view._auto_match_account()  # should not crash
        assert view.auto_match_label.text() == ''


# ---------------------------------------------------------------------------
# TestPopulateTable
# ---------------------------------------------------------------------------
class TestPopulateTable:
    def test_rows_populated(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._statement = _make_cc_statement()
        view._populate_table()

        assert view.table.rowCount() == 3

    def test_cell_values(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._statement = _make_cc_statement()
        view._populate_table()

        # First row (payment)
        assert view.table.item(0, 0).text() == '2026-01-02'
        assert view.table.item(0, 1).text() == ''  # no post_date
        assert view.table.item(0, 2).text() == 'PAYMENT'
        assert '622.00' in view.table.item(0, 3).text()
        assert view.table.item(0, 4).text() == 'payment'

        # Second row (purchase with post date)
        assert view.table.item(1, 1).text() == '2026-01-06'

    def test_negative_amount_red(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._statement = _make_cc_statement()
        view._populate_table()

        # Row 1 is a purchase (negative)
        assert view.table.item(1, 3).foreground().color() == QColor('#f44336')

    def test_positive_amount_green(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._statement = _make_cc_statement()
        view._populate_table()

        # Row 0 is a payment (positive)
        assert view.table.item(0, 3).foreground().color() == QColor('#4caf50')

    def test_status_label(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._statement = _make_cc_statement()
        view._populate_table()

        assert '3 transaction(s) found' in view.status_label.text()

    def test_no_statement_clears_table(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        # First populate
        view._statement = _make_cc_statement()
        view._populate_table()
        assert view.table.rowCount() == 3
        # Then clear
        view._statement = None
        view._populate_table()
        assert view.table.rowCount() == 0


# ---------------------------------------------------------------------------
# TestSelectPdf
# ---------------------------------------------------------------------------
class TestSelectPdf:
    def test_successful_parse(self, qtbot, temp_db, sample_account):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)

        stmt = _make_cc_statement()
        with patch(f'{MODULE}.QFileDialog.getOpenFileName', return_value=('/tmp/test.pdf', 'PDF Files')), \
             patch(f'{MODULE}.parse_statement', return_value=stmt), \
             patch(f'{MODULE}.match_account', return_value=None):
            view._select_pdf()

        assert view.file_label.text() == 'test.pdf'
        assert 'Chase' in view.institution_label.text()
        assert view.table.rowCount() == 3
        assert view.import_btn.isEnabled()

    def test_cancelled_dialog(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)

        with patch(f'{MODULE}.QFileDialog.getOpenFileName', return_value=('', '')):
            view._select_pdf()

        assert view.file_label.text() == 'No file selected'
        assert view._statement is None

    def test_parse_error(self, qtbot, mock_qmessagebox):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)

        with patch(f'{MODULE}.QFileDialog.getOpenFileName', return_value=('/tmp/bad.pdf', 'PDF Files')), \
             patch(f'{MODULE}.parse_statement', side_effect=ValueError('bad format')):
            view._select_pdf()

        assert mock_qmessagebox.warning_called
        assert 'bad format' in mock_qmessagebox.warning_text
        assert view._statement is None

    def test_no_transactions_button_disabled(self, qtbot, temp_db):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)

        stmt = StatementData(institution='Test', statement_type='checking')
        with patch(f'{MODULE}.QFileDialog.getOpenFileName', return_value=('/tmp/empty.pdf', 'PDF Files')), \
             patch(f'{MODULE}.parse_statement', return_value=stmt), \
             patch(f'{MODULE}.match_account', return_value=None):
            view._select_pdf()

        assert not view.import_btn.isEnabled()


# ---------------------------------------------------------------------------
# TestImportTransactions
# ---------------------------------------------------------------------------
class TestImportTransactions:
    def test_successful_import(self, qtbot, temp_db, sample_account, mock_qmessagebox):
        from budget_app.views.pdf_import_view import PDFImportView
        from budget_app.models.transaction import Transaction
        view = PDFImportView()
        qtbot.addWidget(view)

        view._statement = _make_cc_statement()
        view._load_accounts()
        # Select the account (index 1 = first real account)
        view.account_combo.setCurrentIndex(1)
        view.import_btn.setEnabled(True)

        view._import_transactions()

        # Transactions saved
        all_txns = Transaction.get_all()
        assert len(all_txns) == 3
        assert mock_qmessagebox.info_called
        assert 'Imported 3' in view.status_label.text()
        assert not view.import_btn.isEnabled()

    def test_mark_posted_checked(self, qtbot, temp_db, sample_account, mock_qmessagebox):
        from budget_app.views.pdf_import_view import PDFImportView
        from budget_app.models.transaction import Transaction
        view = PDFImportView()
        qtbot.addWidget(view)

        view._statement = _make_cc_statement()
        view._load_accounts()
        view.account_combo.setCurrentIndex(1)
        view.mark_posted_check.setChecked(True)

        view._import_transactions()

        all_txns = Transaction.get_all()
        assert all(t.is_posted for t in all_txns)

    def test_mark_posted_unchecked(self, qtbot, temp_db, sample_account, mock_qmessagebox):
        from budget_app.views.pdf_import_view import PDFImportView
        from budget_app.models.transaction import Transaction
        view = PDFImportView()
        qtbot.addWidget(view)

        view._statement = _make_cc_statement()
        view._load_accounts()
        view.account_combo.setCurrentIndex(1)
        view.mark_posted_check.setChecked(False)

        view._import_transactions()

        all_txns = Transaction.get_all()
        assert all(not t.is_posted for t in all_txns)

    def test_no_account_selected_warns(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)

        view._statement = _make_cc_statement()
        view._load_accounts()
        # Keep placeholder selected (index 0, data=None)
        view.account_combo.setCurrentIndex(0)

        view._import_transactions()

        assert mock_qmessagebox.warning_called
        assert 'select an account' in mock_qmessagebox.warning_text.lower()

    def test_user_declines_confirmation(self, qtbot, temp_db, sample_account, mock_qmessagebox):
        from budget_app.views.pdf_import_view import PDFImportView
        from budget_app.models.transaction import Transaction
        from PyQt6.QtWidgets import QMessageBox
        view = PDFImportView()
        qtbot.addWidget(view)

        view._statement = _make_cc_statement()
        view._load_accounts()
        view.account_combo.setCurrentIndex(1)

        mock_qmessagebox.last_return = QMessageBox.StandardButton.No
        view._import_transactions()

        assert len(Transaction.get_all()) == 0

    def test_no_statement_noop(self, qtbot, temp_db):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._statement = None
        view._import_transactions()  # should not crash

    def test_empty_transactions_noop(self, qtbot, temp_db):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view._statement = StatementData()  # no transactions
        view._import_transactions()  # should not crash


# ---------------------------------------------------------------------------
# TestUpdateAccountBalance
# ---------------------------------------------------------------------------
class TestUpdateAccountBalance:
    def test_updates_card_balance(self, qtbot, temp_db, sample_card, mock_qmessagebox):
        from budget_app.views.pdf_import_view import PDFImportView
        from budget_app.models.credit_card import CreditCard
        view = PDFImportView()
        qtbot.addWidget(view)

        view._statement = _make_cc_statement()
        view._load_accounts()
        # Select the card
        for i in range(view.account_combo.count()):
            if view.account_combo.itemData(i) == sample_card.pay_type_code:
                view.account_combo.setCurrentIndex(i)
                break
        view.update_balance_check.setChecked(True)

        view._import_transactions()

        updated_card = CreditCard.get_by_code(sample_card.pay_type_code)
        assert updated_card.current_balance == 1800.0

    def test_updates_account_balance(self, qtbot, temp_db, sample_account, mock_qmessagebox):
        from budget_app.views.pdf_import_view import PDFImportView
        from budget_app.models.account import Account
        view = PDFImportView()
        qtbot.addWidget(view)

        view._statement = _make_cc_statement()
        view._load_accounts()
        view.account_combo.setCurrentIndex(1)  # sample_account
        view.update_balance_check.setChecked(True)

        view._import_transactions()

        updated_acct = Account.get_by_code(sample_account.pay_type_code)
        assert updated_acct.current_balance == 1800.0

    def test_balance_update_skipped_when_unchecked(self, qtbot, temp_db, sample_card, mock_qmessagebox):
        from budget_app.views.pdf_import_view import PDFImportView
        from budget_app.models.credit_card import CreditCard
        view = PDFImportView()
        qtbot.addWidget(view)

        view._statement = _make_cc_statement()
        view._load_accounts()
        for i in range(view.account_combo.count()):
            if view.account_combo.itemData(i) == sample_card.pay_type_code:
                view.account_combo.setCurrentIndex(i)
                break
        view.update_balance_check.setChecked(False)

        view._import_transactions()

        unchanged = CreditCard.get_by_code(sample_card.pay_type_code)
        assert unchanged.current_balance == sample_card.current_balance


# ---------------------------------------------------------------------------
# TestClear
# ---------------------------------------------------------------------------
class TestClear:
    def test_resets_all_state(self, qtbot, temp_db, sample_account):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)

        # Load statement first
        view._statement = _make_cc_statement()
        view._update_summary()
        view._load_accounts()
        view._populate_table()
        view.import_btn.setEnabled(True)
        view.file_label.setText('test.pdf')

        # Now clear
        view._clear()

        assert view._statement is None
        assert view.file_label.text() == 'No file selected'
        assert view.institution_label.text() == 'Institution: —'
        assert view.type_label.text() == 'Type: —'
        assert view.last4_label.text() == 'Account: —'
        assert view.period_label.text() == 'Period: —'
        assert view.prev_balance_label.text() == 'Prev Balance: —'
        assert view.new_balance_label.text() == 'New Balance: —'
        assert view.limit_label.text() == 'Credit Limit: —'
        assert view.interest_label.text() == 'Interest: —'
        assert view.fees_label.text() == 'Fees: —'
        assert view.min_payment_label.text() == 'Min Payment: —'
        assert view.due_date_label.text() == 'Due Date: —'
        assert view.payslip_label.text() == ''
        assert view.auto_match_label.text() == ''
        assert view.account_combo.count() == 0
        assert view.table.rowCount() == 0
        assert not view.import_btn.isEnabled()
        assert view.status_label.text() == ''


# ---------------------------------------------------------------------------
# TestRefresh
# ---------------------------------------------------------------------------
class TestRefresh:
    def test_noop(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        view.refresh()  # should not raise
