"""Tests for budget_app/utils/statement_parser.py"""

import sys
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from budget_app.utils.statement_parser import (
    _safe_float,
    _parse_date,
    _infer_year,
    detect_format,
    parse_statement,
    _parse_chase_checking,
    _parse_chase_cc,
    _parse_capital_one,
    _parse_barclays,
    _parse_wells_fargo,
    _parse_merrick,
    _parse_comenity,
    _parse_payslip,
    match_account,
    StatementData,
    TransactionEntry,
)


# ---------------------------------------------------------------------------
# TestSafeFloat
# ---------------------------------------------------------------------------
class TestSafeFloat:
    def test_empty_string(self):
        assert _safe_float('') == 0.0

    def test_none(self):
        assert _safe_float(None) == 0.0

    def test_normal_number(self):
        assert _safe_float('1,234.56') == 1234.56

    def test_dollar_sign(self):
        assert _safe_float('$1,234.56') == 1234.56

    def test_trailing_minus(self):
        assert _safe_float('100.00-') == -100.0

    def test_parentheses_negative(self):
        assert _safe_float('(500.00)') == -500.0

    def test_plus_sign(self):
        assert _safe_float('+250.00') == 250.0

    def test_invalid_text(self):
        assert _safe_float('abc') == 0.0

    def test_whitespace(self):
        assert _safe_float('  42.50  ') == 42.5


# ---------------------------------------------------------------------------
# TestParseDate
# ---------------------------------------------------------------------------
class TestParseDate:
    def test_mm_dd_with_explicit_year(self):
        assert _parse_date('01/15', year=2026) == '2026-01-15'

    def test_mm_dd_yy_short_year(self):
        assert _parse_date('01/25/26') == '2026-01-25'

    def test_mm_dd_yyyy_full_year(self):
        assert _parse_date('03/15/2025') == '2025-03-15'

    def test_mon_dd_format(self):
        assert _parse_date('Dec 25', year=2025) == '2025-12-25'

    def test_mon_dd_single_digit(self):
        assert _parse_date('Jan 9', year=2026) == '2026-01-09'

    def test_invalid_input(self):
        assert _parse_date('not a date') == ''

    def test_empty_string(self):
        assert _parse_date('') == ''

    def test_mm_dd_defaults_to_current_year(self):
        result = _parse_date('06/15')
        year = datetime.now().year
        assert result == f'{year:04d}-06-15'


# ---------------------------------------------------------------------------
# TestInferYear
# ---------------------------------------------------------------------------
class TestInferYear:
    def test_normal_same_year(self):
        assert _infer_year(3, '2026-03-15') == 2026

    def test_december_with_january_period_end(self):
        assert _infer_year(12, '2026-01-25') == 2025

    def test_december_with_february_period_end(self):
        assert _infer_year(12, '2026-02-10') == 2025

    def test_no_period_end_falls_back_to_current_year(self):
        assert _infer_year(5, '') == datetime.now().year

    def test_invalid_period_end(self):
        assert _infer_year(5, 'not-a-date') == datetime.now().year


# ---------------------------------------------------------------------------
# TestDetectFormat
# ---------------------------------------------------------------------------
class TestDetectFormat:
    def test_chase_checking_start_summary(self):
        assert detect_format('blah *start*summary blah') == 'chase_checking'

    def test_chase_checking_start_deposits(self):
        assert detect_format('blah *start*deposits blah') == 'chase_checking'

    def test_chase_cc(self):
        assert detect_format('visit chase.com for more') == 'chase_cc'

    def test_chase_cc_doubled_header(self):
        assert detect_format('AACCCCOOUUNNTT SSUUMMMMAARRYY') == 'chase_cc'

    def test_capital_one(self):
        assert detect_format('Capital One statement') == 'capital_one'

    def test_capital_one_website(self):
        assert detect_format('visit capitalone.com') == 'capital_one'

    def test_barclays(self):
        assert detect_format('Barclays US statement') == 'barclays'

    def test_wells_fargo(self):
        assert detect_format('Wells Fargo credit card') == 'wells_fargo'

    def test_wells_fargo_website(self):
        assert detect_format('visit wellsfargo.com') == 'wells_fargo'

    def test_merrick(self):
        assert detect_format('Merrick Bank statement') == 'merrick'

    def test_merrick_website(self):
        assert detect_format('merrickbank statement') == 'merrick'

    def test_comenity(self):
        assert detect_format('Comenity Bank statement') == 'comenity'

    def test_concora_credit(self):
        assert detect_format('Concora Credit statement') == 'comenity'

    def test_payslip(self):
        assert detect_format('Gross Pay   Net Pay breakdown') == 'payslip'

    def test_unknown(self):
        assert detect_format('random text with no bank name') == 'unknown'

    def test_empty(self):
        assert detect_format('') == 'unknown'

    def test_none(self):
        assert detect_format(None) == 'unknown'

    def test_capital_one_before_chase_cc(self):
        """Capital One should be detected even if text also contains chase.com."""
        text = 'Capital One chase.com payment'
        assert detect_format(text) == 'capital_one'


# ---------------------------------------------------------------------------
# TestParseStatement (integration — mock pdfplumber)
# ---------------------------------------------------------------------------
class TestParseStatement:
    def _mock_pdfplumber(self, pages_text):
        """Create a mock pdfplumber module and PDF object."""
        mock_module = MagicMock()
        pages = []
        for text in pages_text:
            page = MagicMock()
            page.extract_text.return_value = text
            pages.append(page)
        mock_pdf = MagicMock()
        mock_pdf.pages = pages
        mock_module.open.return_value = mock_pdf
        return mock_module

    def test_routes_to_chase_checking(self):
        text = (
            '*start*summary\n'
            'Account 1234567890123456\n'
            'December 13, 2025 through January 15, 2026\n'
            'Beginning Balance $1,000.00\n'
            'Ending Balance $1,200.00\n'
        )
        mock_mod = self._mock_pdfplumber([text])
        with patch.dict(sys.modules, {'pdfplumber': mock_mod}):
            result = parse_statement('fake.pdf')
        assert result.institution == 'Chase'
        assert result.statement_type == 'checking'

    def test_empty_pdf_raises(self):
        mock_mod = self._mock_pdfplumber([None])
        # Pages with None text produce empty pages_text
        mock_page = MagicMock()
        mock_page.extract_text.return_value = None
        mock_mod.open.return_value.pages = [mock_page]
        with patch.dict(sys.modules, {'pdfplumber': mock_mod}):
            with pytest.raises(ValueError, match='Could not extract text'):
                parse_statement('empty.pdf')

    def test_unknown_format_raises(self):
        mock_mod = self._mock_pdfplumber(['random text no bank detected'])
        with patch.dict(sys.modules, {'pdfplumber': mock_mod}):
            with pytest.raises(ValueError, match='Unknown statement format'):
                parse_statement('unknown.pdf')


# ---------------------------------------------------------------------------
# TestParseChaseChecking
# ---------------------------------------------------------------------------
class TestParseChaseChecking:
    CHASE_CHECKING_TEXT = (
        'Statement\n'
        'Account 1234567890123456\n'
        'December 13, 2025 through January 15, 2026\n'
        'Beginning Balance $1,500.00\n'
        'Ending Balance $2,100.00\n'
        '*start*deposits and additions\n'
        '12/20 DIRECT DEPOSIT PAYROLL 2,000.00\n'
        '01/05 ATM DEPOSIT 500.00\n'
        '*end*deposits and additions\n'
        '*start*atm debit withdrawal\n'
        '12/22 ATM WITHDRAWAL 200.00\n'
        '*end*atm debit withdrawal\n'
        '*start*electronic withdrawal\n'
        '01/10 ONLINE PAYMENT TO CHASE CARD 150.00\n'
        '*end*electronic withdrawal\n'
    )

    def test_metadata(self):
        data = _parse_chase_checking(self.CHASE_CHECKING_TEXT)
        assert data.account_last4 == '3456'
        assert data.period_start == '2025-12-13'
        assert data.period_end == '2026-01-15'
        assert data.previous_balance == 1500.0
        assert data.new_balance == 2100.0
        assert data.institution == 'Chase'
        assert data.statement_type == 'checking'

    def test_deposits_are_positive(self):
        data = _parse_chase_checking(self.CHASE_CHECKING_TEXT)
        deposits = [t for t in data.transactions if t.category == 'deposit']
        assert len(deposits) == 2
        assert deposits[0].amount == 2000.0
        assert deposits[0].description == 'DIRECT DEPOSIT PAYROLL'
        assert deposits[1].amount == 500.0

    def test_withdrawals_are_negative(self):
        data = _parse_chase_checking(self.CHASE_CHECKING_TEXT)
        withdrawals = [t for t in data.transactions if t.category == 'withdrawal']
        assert len(withdrawals) == 2
        assert all(t.amount < 0 for t in withdrawals)
        assert withdrawals[0].amount == -200.0
        assert withdrawals[1].amount == -150.0

    def test_totals(self):
        data = _parse_chase_checking(self.CHASE_CHECKING_TEXT)
        assert data.payments_total == 2500.0  # 2000 + 500
        assert data.purchases_total == 350.0  # 200 + 150

    def test_deposit_dates_infer_year(self):
        data = _parse_chase_checking(self.CHASE_CHECKING_TEXT)
        deposits = [t for t in data.transactions if t.category == 'deposit']
        assert deposits[0].date == '2025-12-20'  # Dec → 2025
        assert deposits[1].date == '2026-01-05'  # Jan → 2026

    def test_skips_total_lines(self):
        text = (
            'Account 9999888877776666\n'
            'December 1, 2025 through December 31, 2025\n'
            'Beginning Balance $100.00\n'
            'Ending Balance $200.00\n'
            '*start*deposits and additions\n'
            '12/15 PAYROLL 1,000.00\n'
            'Total Deposits and Additions 1,000.00\n'
            '*end*deposits and additions\n'
        )
        data = _parse_chase_checking(text)
        assert len(data.transactions) == 1


# ---------------------------------------------------------------------------
# TestParseChaseCc
# ---------------------------------------------------------------------------
class TestParseChaseCc:
    CHASE_CC_TEXT = (
        'chase.com\n'
        'XXXX XXXX XXXX 4830\n'
        'Opening/Closing Date 12/26/25 - 01/25/26\n'
        'Previous Balance $1,500.00\n'
        'New Balance $1,800.00\n'
        'Credit Access Line $10,000\n'
        'Minimum Payment Due: $35.00\n'
        'Payment Due Date: 02/21/26\n'
        'Interest Charged $22.50\n'
        'ACCOUNT ACTIVITY\n'
        'Payment and Credits\n'
        '01/02 AUTOMATIC PAYMENT - THANK YOU -622.00\n'
        'PURCHASE\n'
        '01/05 AMAZON MARKETPLACE 49.99\n'
        '01/10 COSTCO WHOLESALE 125.30\n'
        'INTEREST CHARGED\n'
        '01/25 PURCHASE INTEREST CHARGE 22.50\n'
        '2026 Totals\n'
    )

    def test_metadata(self):
        data = _parse_chase_cc(self.CHASE_CC_TEXT)
        assert data.account_last4 == '4830'
        assert data.period_start == '2025-12-26'
        assert data.period_end == '2026-01-25'
        assert data.previous_balance == 1500.0
        assert data.new_balance == 1800.0
        assert data.credit_limit == 10000.0
        assert data.minimum_payment == 35.0
        assert data.payment_due_date == '2026-02-21'
        assert data.interest_total == 22.50

    def test_payment_transactions(self):
        data = _parse_chase_cc(self.CHASE_CC_TEXT)
        payments = [t for t in data.transactions if t.category == 'payment']
        assert len(payments) == 1
        assert payments[0].amount == 622.0  # positive
        assert payments[0].description == 'AUTOMATIC PAYMENT - THANK YOU'

    def test_purchase_transactions(self):
        data = _parse_chase_cc(self.CHASE_CC_TEXT)
        purchases = [t for t in data.transactions if t.category == 'purchase']
        assert len(purchases) == 2
        assert purchases[0].amount == -49.99
        assert purchases[1].amount == -125.30

    def test_interest_transaction(self):
        data = _parse_chase_cc(self.CHASE_CC_TEXT)
        interest = [t for t in data.transactions if t.category == 'interest']
        assert len(interest) == 1
        assert interest[0].amount == -22.50

    def test_doubled_char_header_fallback(self):
        text = (
            'XXXX XXXX XXXX 9999\n'
            'Opening/Closing Date 01/01/26 - 01/31/26\n'
            'Previous Balance $500.00\n'
            'New Balance $600.00\n'
            'AACCCCOOUUNNTT AACCTTIIVVIITTYY\n'
            'Payment and Credits\n'
            '01/15 PAYMENT RECEIVED -100.00\n'
        )
        data = _parse_chase_cc(text)
        payments = [t for t in data.transactions if t.category == 'payment']
        assert len(payments) == 1
        assert payments[0].amount == 100.0

    def test_totals(self):
        data = _parse_chase_cc(self.CHASE_CC_TEXT)
        assert data.payments_total == 622.0
        assert data.purchases_total == pytest.approx(175.29)


# ---------------------------------------------------------------------------
# TestParseCapitalOne
# ---------------------------------------------------------------------------
class TestParseCapitalOne:
    CAPITAL_ONE_TEXT = (
        'Capital One\n'
        'ending in 8138\n'
        'Dec 26, 2025 - Jan 25, 2026\n'
        'Previous Balance $5,000.00\n'
        'New Balance = $5,200.00\n'
        'Credit Limit $7,500.00\n'
        'Payment Due Date Feb 21, 2026\n'
        'Interest Charged + $85.50\n'
        'Fees Charged + $40.00\n'
        'New Balance  Minimum Payment Due  Amount Enclosed\n'
        '$5,200.00  $150.00  $___\n'
        'Payments, Credits and Adjustments\n'
        'Trans Date Post Date Description Amount\n'
        'Dec 28 Dec 29 CAPITAL ONE MOBILE PYMT - $300.00\n'
        '#8138: Transactions\n'
        'Trans Date Post Date Description Amount\n'
        'Jan 05 Jan 06 WALMART SUPERCENTER $52.43\n'
        'Jan 10 Jan 11 SHELL OIL $35.00\n'
    )

    def test_metadata(self):
        data = _parse_capital_one(self.CAPITAL_ONE_TEXT)
        assert data.account_last4 == '8138'
        assert data.period_start == '2025-12-26'
        assert data.period_end == '2026-01-25'
        assert data.previous_balance == 5000.0
        assert data.new_balance == 5200.0
        assert data.credit_limit == 7500.0
        assert data.minimum_payment == 150.0
        assert data.payment_due_date == '2026-02-21'
        assert data.interest_total == 85.5
        assert data.fees_total == 40.0

    def test_payment_transactions(self):
        data = _parse_capital_one(self.CAPITAL_ONE_TEXT)
        payments = [t for t in data.transactions if t.category == 'payment']
        assert len(payments) == 1
        assert payments[0].amount == 300.0
        assert 'CAPITAL ONE MOBILE PYMT' in payments[0].description

    def test_purchase_transactions(self):
        data = _parse_capital_one(self.CAPITAL_ONE_TEXT)
        purchases = [t for t in data.transactions if t.category == 'purchase']
        assert len(purchases) == 2
        assert purchases[0].amount == -52.43
        assert purchases[1].amount == -35.0

    def test_post_dates(self):
        data = _parse_capital_one(self.CAPITAL_ONE_TEXT)
        purchases = [t for t in data.transactions if t.category == 'purchase']
        assert purchases[0].post_date == '2026-01-06'

    def test_fee_deduplication(self):
        """Fee caught by the general transaction loop should not be re-added by
        the dedicated fee-matching second pass."""
        text = (
            'Capital One\n'
            'ending in 1234\n'
            'Jan 01, 2026 - Jan 31, 2026\n'
            'Previous Balance $100.00\n'
            'New Balance = $140.00\n'
            'Fees\n'
            'Jan 15 Jan 15 PAST DUE FEE $40.00\n'
        )
        data = _parse_capital_one(text)
        fees = [t for t in data.transactions if t.category == 'fee']
        # The line is matched by the general loop (as fee category) and the
        # second fee-specific loop checks for duplicates, so only 1 entry.
        assert len(fees) == 1


# ---------------------------------------------------------------------------
# TestParseBarclays
# ---------------------------------------------------------------------------
class TestParseBarclays:
    BARCLAYS_TEXT = (
        'Barclays US\n'
        'Account Ending 8703\n'
        'Statement Period 12/25/25 - 01/24/26\n'
        'Previous Balance $3,200.00\n'
        'Statement Balance $3,500.00\n'
        'Total Credit Line $6,000.00\n'
        'Minimum Payment Due: $90.00\n'
        'Payment Due Date: 02/20/26\n'
        'Interest Charged $55.00\n'
        'Fees Charged $0.00\n'
        'Payments\n'
        'Transaction Date Posting Date Description Points Amount\n'
        'Jan 21 Jan 21 Payment Received JPMORGAN CHAS N/A -$1,013.93\n'
        'Purchase Activity\n'
        'Transaction Date Posting Date Description Points Amount\n'
        'Jan 09 Jan 09 CLUB WYNDHAM PLUS 888-739-4022 NV 462 $231.00\n'
        'Jan 15 Jan 16 COSTCO WHOLESALE 120 $60.00\n'
    )

    def test_metadata(self):
        data = _parse_barclays(self.BARCLAYS_TEXT)
        assert data.account_last4 == '8703'
        assert data.period_start == '2025-12-25'
        assert data.period_end == '2026-01-24'
        assert data.previous_balance == 3200.0
        assert data.new_balance == 3500.0
        assert data.credit_limit == 6000.0
        assert data.minimum_payment == 90.0
        assert data.payment_due_date == '2026-02-20'
        assert data.interest_total == 55.0
        assert data.fees_total == 0.0

    def test_payment_lines_na_points(self):
        data = _parse_barclays(self.BARCLAYS_TEXT)
        payments = [t for t in data.transactions if t.category == 'payment']
        assert len(payments) == 1
        assert payments[0].amount == 1013.93  # positive (abs of -$1,013.93)
        assert 'Payment Received' in payments[0].description

    def test_purchase_lines_numeric_points(self):
        data = _parse_barclays(self.BARCLAYS_TEXT)
        purchases = [t for t in data.transactions if t.category == 'purchase']
        assert len(purchases) == 2
        assert purchases[0].amount == -231.0
        assert purchases[1].amount == -60.0

    def test_totals(self):
        data = _parse_barclays(self.BARCLAYS_TEXT)
        assert data.payments_total == 1013.93
        assert data.purchases_total == 291.0


# ---------------------------------------------------------------------------
# TestParseWellsFargo
# ---------------------------------------------------------------------------
class TestParseWellsFargo:
    WELLS_FARGO_TEXT = (
        'Wells Fargo\n'
        'Account Number 5774 4225 4269 9359\n'
        'Billing Cycle 12/20/2025 to 01/19/2026\n'
        'Previous Balance $ 2,500.00\n'
        'New Balance $ 2,800.00\n'
        'Credit Limit $ 5,000.00\n'
        'Minimum Payment Due $ 75.00\n'
        'Payment Due Date 02/15/2026\n'
        'Transaction Detail\n'
        '990000069 P938800QX0XSL7694 01/13 01/13 ONLINE ACH PAYMENT THANK YOU $223.00-\n'
        '01/05 01/06 WALMART SUPERCENTER $85.50\n'
        'INTEREST CHARGE ON PURCHASES $32.15\n'
    )

    def test_metadata(self):
        data = _parse_wells_fargo(self.WELLS_FARGO_TEXT)
        assert data.account_last4 == '9359'
        assert data.period_start == '2025-12-20'
        assert data.period_end == '2026-01-19'
        assert data.previous_balance == 2500.0
        assert data.new_balance == 2800.0
        assert data.credit_limit == 5000.0
        assert data.minimum_payment == 75.0
        assert data.payment_due_date == '2026-02-15'

    def test_trailing_minus_is_payment(self):
        data = _parse_wells_fargo(self.WELLS_FARGO_TEXT)
        payments = [t for t in data.transactions if t.category == 'payment']
        assert len(payments) == 1
        assert payments[0].amount == 223.0  # positive
        assert 'ONLINE ACH PAYMENT' in payments[0].description

    def test_purchase_no_trailing_minus(self):
        data = _parse_wells_fargo(self.WELLS_FARGO_TEXT)
        purchases = [t for t in data.transactions if t.category == 'purchase']
        assert len(purchases) == 1
        assert purchases[0].amount == -85.50

    def test_interest_from_separate_section(self):
        data = _parse_wells_fargo(self.WELLS_FARGO_TEXT)
        assert data.interest_total == 32.15

    def test_ref_number_prefixed_line(self):
        data = _parse_wells_fargo(self.WELLS_FARGO_TEXT)
        payments = [t for t in data.transactions if t.category == 'payment']
        assert payments[0].date == '2026-01-13'
        assert payments[0].post_date == '2026-01-13'

    def test_skips_zero_amount(self):
        text = (
            'Wells Fargo\n'
            'Account Number 1234 5678 9012 3456\n'
            'Billing Cycle 01/01/2026 to 01/31/2026\n'
            '01/15 01/15 SOME ZERO CHARGE $0.00\n'
        )
        data = _parse_wells_fargo(text)
        assert len(data.transactions) == 0


# ---------------------------------------------------------------------------
# TestParseMerrick
# ---------------------------------------------------------------------------
class TestParseMerrick:
    MERRICK_TEXT = (
        'Merrick Bank\n'
        'Account Number 5432 1098 7654 3210\n'
        'Statement Date: 01/25/26\n'
        'Billing Cycle Closing Date 01/25/26\n'
        'Previous Balance $1,200.00\n'
        'New Balance $1,350.00\n'
        'Credit Limit $3,000.00\n'
        'Minimum Payment Due $35.00\n'
        'Payment Due Date 02/20/26\n'
        'TOTAL INTEREST FOR THIS PERIOD $18.75\n'
        'TOTAL FEES FOR THIS PERIOD $0.00\n'
        'Transactions, Payments and Credits\n'
        '01/16 8542539D000XTMJGS ONLINE RECURRING PAYMENT 293.52 -\n'
        '01/18 TX12345678 AMAZON.COM 55.00\n'
        'Fees\n'
        '01/20 FEE123 LATE FEE 25.00\n'
        'Interest Charged\n'
        'Interest on purchases 18.75\n'
    )

    def test_metadata(self):
        data = _parse_merrick(self.MERRICK_TEXT)
        assert data.account_last4 == '3210'
        assert data.period_end == '2026-01-25'
        assert data.previous_balance == 1200.0
        assert data.new_balance == 1350.0
        assert data.credit_limit == 3000.0
        assert data.minimum_payment == 35.0
        assert data.payment_due_date == '2026-02-20'
        assert data.interest_total == 18.75
        assert data.fees_total == 0.0

    def test_payment_trailing_minus(self):
        data = _parse_merrick(self.MERRICK_TEXT)
        payments = [t for t in data.transactions if t.category == 'payment']
        assert len(payments) == 1
        assert payments[0].amount == 293.52  # positive
        assert 'ONLINE RECURRING PAYMENT' in payments[0].description

    def test_purchase(self):
        data = _parse_merrick(self.MERRICK_TEXT)
        purchases = [t for t in data.transactions if t.category == 'purchase']
        assert len(purchases) == 1
        assert purchases[0].amount == -55.0

    def test_fees_section(self):
        data = _parse_merrick(self.MERRICK_TEXT)
        fees = [t for t in data.transactions if t.category == 'fee']
        assert len(fees) == 1
        assert fees[0].amount == -25.0

    def test_section_transitions(self):
        """Interest Charged header stops fee/transaction parsing."""
        data = _parse_merrick(self.MERRICK_TEXT)
        assert len(data.transactions) == 3  # 1 payment + 1 purchase + 1 fee

    def test_statement_date_fallback(self):
        """Statement Date is used when Billing Cycle Closing Date is absent."""
        text = (
            'Merrick Bank\n'
            'Account Number 1111 2222 3333 4444\n'
            'Statement Date: 02/15/26\n'
            'Previous Balance $100.00\n'
            'New Balance $110.00\n'
        )
        data = _parse_merrick(text)
        assert data.statement_date == '2026-02-15'
        assert data.period_end == '2026-02-15'


# ---------------------------------------------------------------------------
# TestParseComenity
# ---------------------------------------------------------------------------
class TestParseComenity:
    def test_ending_in_pattern(self):
        text = (
            'Comenity Bank\n'
            'Account number ending in 5678\n'
            'Statement Closing Date January 31, 2026\n'
            'Previous Balance $800.00\n'
            'New Balance $900.00\n'
        )
        data = _parse_comenity(text)
        assert data.account_last4 == '5678'
        assert data.statement_date == '2026-01-31'
        assert data.previous_balance == 800.0
        assert data.new_balance == 900.0

    def test_star_pattern(self):
        text = (
            'Comenity\n'
            '****-****-****-9012\n'
            'Statement Closing Date February 15, 2026\n'
        )
        data = _parse_comenity(text)
        assert data.account_last4 == '9012'

    def test_format_a_transactions(self):
        text = (
            'Comenity Bank\n'
            'ending in 1234\n'
            'Statement Closing Date January 31, 2026\n'
            'Previous Balance $500.00\n'
            'New Balance $450.00\n'
            'TRANSACTIONS\n'
            '01/10 01/10 REF123 ONLINE PAYMENT 100.00 -\n'
            '01/15 01/16 REF456 STORE PURCHASE 50.00\n'
        )
        data = _parse_comenity(text)
        payments = [t for t in data.transactions if t.category == 'payment']
        purchases = [t for t in data.transactions if t.category == 'purchase']
        assert len(payments) == 1
        assert payments[0].amount == 100.0  # credit → positive
        assert len(purchases) == 1
        assert purchases[0].amount == -50.0  # purchase → negative

    def test_format_b_transactions(self):
        text = (
            'Comenity Bank\n'
            'ending in 5555\n'
            'Statement Closing Date January 31, 2026\n'
            'Previous Balance $200.00\n'
            'New Balance $250.00\n'
            'TRANSACTIONS\n'
            '01/15/2026 STORE PURCHASE 75.00\n'
            '01/20/2026 ONLINE PAYMENT -50.00\n'
        )
        data = _parse_comenity(text)
        purchases = [t for t in data.transactions if t.category == 'purchase']
        payments = [t for t in data.transactions if t.category == 'payment']
        assert len(purchases) == 1
        assert purchases[0].amount == -75.0
        assert len(payments) == 1
        assert payments[0].amount == 50.0

    def test_fee_section_format_a(self):
        text = (
            'Comenity Bank\n'
            'ending in 7777\n'
            'Statement Closing Date January 31, 2026\n'
            'FEES\n'
            '01/20 01/20 FEE789 LATE FEE 29.00\n'
            'INTEREST CHARGED\n'
        )
        data = _parse_comenity(text)
        fees = [t for t in data.transactions if t.category == 'fee']
        assert len(fees) == 1
        assert fees[0].amount == -29.0

    def test_fee_section_no_ref_number(self):
        text = (
            'Comenity Bank\n'
            'ending in 8888\n'
            'Statement Closing Date January 31, 2026\n'
            'FEES\n'
            '01/20 01/20 ANNUAL FEE 99.00\n'
            'INTEREST CHARGED\n'
        )
        data = _parse_comenity(text)
        fees = [t for t in data.transactions if t.category == 'fee']
        assert len(fees) == 1
        assert fees[0].amount == -99.0

    def test_fee_section_format_b(self):
        text = (
            'Comenity Bank\n'
            'ending in 6666\n'
            'Statement Closing Date January 31, 2026\n'
            'FEES\n'
            '01/25/2026 LATE FEE 35.00\n'
            'INTEREST CHARGED\n'
        )
        data = _parse_comenity(text)
        fees = [t for t in data.transactions if t.category == 'fee']
        assert len(fees) == 1
        assert fees[0].amount == -35.0

    def test_payment_due_date_word_format(self):
        text = (
            'Comenity Bank\n'
            'ending in 4444\n'
            'Statement Closing Date January 31, 2026\n'
            'Payment Due Date February 25, 2026\n'
        )
        data = _parse_comenity(text)
        assert data.payment_due_date == '2026-02-25'

    def test_payment_due_date_numeric_fallback(self):
        text = (
            'Comenity Bank\n'
            'ending in 4444\n'
            'Statement Closing Date January 31, 2026\n'
            'Payment due date 02/25/2026\n'
        )
        data = _parse_comenity(text)
        assert data.payment_due_date == '2026-02-25'

    def test_interest_totals(self):
        text = (
            'Comenity Bank\n'
            'ending in 3333\n'
            'Statement Closing Date January 31, 2026\n'
            'TOTAL INTEREST FOR THIS PERIOD $12.50\n'
            'TOTAL FEES FOR THIS PERIOD $29.00\n'
        )
        data = _parse_comenity(text)
        assert data.interest_total == 12.5
        assert data.fees_total == 29.0

    def test_interest_totals_mixed_case(self):
        text = (
            'Comenity Bank\n'
            'ending in 2222\n'
            'Statement Closing Date January 31, 2026\n'
            'Total Interest For This Period $8.00\n'
        )
        data = _parse_comenity(text)
        assert data.interest_total == 8.0


# ---------------------------------------------------------------------------
# TestParsePayslip
# ---------------------------------------------------------------------------
class TestParsePayslip:
    PAYSLIP_TEXT = (
        'Elevance Health\n'
        'Gross Pay   Net Pay\n'
        'Pay Period Begin Pay Period End Check Date\n'
        '01/01/2026 01/15/2026 01/20/2026\n'
        'Hours Rate Current Gross Taxes Deductions Net\n'
        'Current 80.00 3,500.00 3,500.00 700.00 300.00 2,500.00\n'
        'Pre Tax Deductions\n'
        '401K 175.00 350.00\n'
        'Health 125.00 250.00\n'
        'Pre Tax Deductions 300.00\n'
        'Post Tax Deductions\n'
        'Roth 50.00 100.00\n'
        'Post Tax Deductions 50.00\n'
        'Associate Taxes\n'
        'Federal Tax 500.00 1,000.00\n'
        'State Tax 200.00 400.00\n'
        'Associate Taxes 700.00\n'
        'Payment Information\n'
        'JPMORGAN CHASE JPMORGAN CHASE ******0117 ******0117 2,500.00 USD\n'
    )

    def test_gross_and_net_pay(self):
        data = _parse_payslip(self.PAYSLIP_TEXT)
        assert data.gross_pay == 3500.0
        assert data.net_pay == 2500.0

    def test_pay_period_dates(self):
        data = _parse_payslip(self.PAYSLIP_TEXT)
        assert data.pay_period_start == '2026-01-01'
        assert data.pay_period_end == '2026-01-15'
        assert data.statement_date == '2026-01-20'

    def test_pre_tax_deductions(self):
        data = _parse_payslip(self.PAYSLIP_TEXT)
        assert '401K' in data.deductions
        assert data.deductions['401K'] == 175.0
        assert 'Health' in data.deductions
        assert data.deductions['Health'] == 125.0

    def test_post_tax_deductions(self):
        data = _parse_payslip(self.PAYSLIP_TEXT)
        assert 'Roth' in data.deductions
        assert data.deductions['Roth'] == 50.0

    def test_taxes(self):
        data = _parse_payslip(self.PAYSLIP_TEXT)
        assert 'Federal Tax' in data.deductions
        assert data.deductions['Federal Tax'] == 500.0
        assert 'State Tax' in data.deductions
        assert data.deductions['State Tax'] == 200.0

    def test_direct_deposit_transaction(self):
        data = _parse_payslip(self.PAYSLIP_TEXT)
        assert len(data.transactions) == 1
        tx = data.transactions[0]
        assert tx.amount == 2500.0
        assert tx.category == 'deposit'
        assert '0117' in tx.description

    def test_bank_name_deduplication(self):
        data = _parse_payslip(self.PAYSLIP_TEXT)
        tx = data.transactions[0]
        # "JPMORGAN CHASE JPMORGAN CHASE" should be deduplicated to "JPMORGAN CHASE"
        assert 'JPMORGAN CHASE' in tx.description
        assert 'JPMORGAN CHASE JPMORGAN CHASE' not in tx.description

    def test_balances(self):
        data = _parse_payslip(self.PAYSLIP_TEXT)
        assert data.new_balance == 2500.0
        assert data.previous_balance == 0.0

    def test_statement_type(self):
        data = _parse_payslip(self.PAYSLIP_TEXT)
        assert data.statement_type == 'payslip'
        assert data.institution == 'Elevance Health'


# ---------------------------------------------------------------------------
# TestMatchAccount
# ---------------------------------------------------------------------------
class TestMatchAccount:
    def _make_account(self, pay_type_code, account_type='CHECKING'):
        acct = MagicMock()
        acct.pay_type_code = pay_type_code
        acct.account_type = account_type
        return acct

    def _make_card(self, pay_type_code, credit_limit, current_balance):
        card = MagicMock()
        card.pay_type_code = pay_type_code
        card.credit_limit = credit_limit
        card.current_balance = current_balance
        return card

    def test_checking_matches_checking_account(self):
        stmt = StatementData(statement_type='checking')
        acct = self._make_account('C', 'CHECKING')
        result = match_account(stmt, [], [acct])
        assert result == 'C'

    def test_credit_card_matches_by_credit_limit(self):
        stmt = StatementData(
            statement_type='credit_card', credit_limit=10000.0, new_balance=3000.0
        )
        card = self._make_card('CH', 10000.0, 5000.0)
        result = match_account(stmt, [card], [])
        assert result == 'CH'

    def test_credit_card_matches_by_approximate_balance(self):
        stmt = StatementData(
            statement_type='credit_card', credit_limit=0, new_balance=3000.0
        )
        card = self._make_card('WF', 5000.0, 3020.0)  # within $50
        result = match_account(stmt, [card], [])
        assert result == 'WF'

    def test_credit_card_no_match_returns_none(self):
        stmt = StatementData(
            statement_type='credit_card', credit_limit=10000.0, new_balance=3000.0
        )
        card = self._make_card('CH', 5000.0, 8000.0)
        result = match_account(stmt, [card], [])
        assert result is None

    def test_payslip_routes_to_checking(self):
        stmt = StatementData(statement_type='payslip')
        acct = self._make_account('C', 'CHECKING')
        result = match_account(stmt, [], [acct])
        assert result == 'C'

    def test_unknown_type_returns_none(self):
        stmt = StatementData(statement_type='other')
        result = match_account(stmt, [], [])
        assert result is None

    def test_balance_outside_tolerance_no_match(self):
        stmt = StatementData(
            statement_type='credit_card', credit_limit=0, new_balance=3000.0
        )
        card = self._make_card('X', 0, 3100.0)  # >$50 difference
        result = match_account(stmt, [card], [])
        assert result is None
