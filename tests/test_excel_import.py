"""Comprehensive tests for budget_app.utils.excel_import module"""

import pytest
import math
import pandas as pd
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helper: build a mock pd.ExcelFile that returns predetermined DataFrames
# ---------------------------------------------------------------------------

def _make_mock_xl(sheet_data: dict, sheet_names: list = None):
    """Create a mock pd.ExcelFile.

    Args:
        sheet_data: mapping of sheet name -> DataFrame (returned by pd.read_excel)
        sheet_names: explicit sheet_names list; defaults to sheet_data keys
    """
    mock_xl = MagicMock(spec=pd.ExcelFile)
    mock_xl.sheet_names = sheet_names or list(sheet_data.keys())

    def _read_excel_side_effect(xl, sheet_name, **kwargs):
        return sheet_data[sheet_name]

    return mock_xl, _read_excel_side_effect


# ===========================================================================
# 1. _safe_float
# ===========================================================================

class TestSafeFloat:
    """Tests for the _safe_float helper function"""

    def test_none_returns_default(self):
        from budget_app.utils.excel_import import _safe_float
        assert _safe_float(None) == 0.0

    def test_none_returns_custom_default(self):
        from budget_app.utils.excel_import import _safe_float
        assert _safe_float(None, default=5.0) == 5.0

    def test_int_value(self):
        from budget_app.utils.excel_import import _safe_float
        assert _safe_float(10) == 10.0

    def test_float_value(self):
        from budget_app.utils.excel_import import _safe_float
        assert _safe_float(123.45) == 123.45

    def test_nan_returns_default(self):
        from budget_app.utils.excel_import import _safe_float
        assert _safe_float(float('nan')) == 0.0

    def test_nan_returns_custom_default(self):
        from budget_app.utils.excel_import import _safe_float
        assert _safe_float(float('nan'), default=99.0) == 99.0

    def test_valid_string(self):
        from budget_app.utils.excel_import import _safe_float
        assert _safe_float("123.45") == 123.45

    def test_empty_string_returns_default(self):
        from budget_app.utils.excel_import import _safe_float
        assert _safe_float("") == 0.0

    def test_non_numeric_string_returns_default(self):
        from budget_app.utils.excel_import import _safe_float
        assert _safe_float("abc") == 0.0


# ===========================================================================
# 2. _safe_int
# ===========================================================================

class TestSafeInt:
    """Tests for the _safe_int helper function"""

    def test_none_returns_none(self):
        from budget_app.utils.excel_import import _safe_int
        assert _safe_int(None) is None

    def test_none_returns_custom_default(self):
        from budget_app.utils.excel_import import _safe_int
        assert _safe_int(None, default=0) == 0

    def test_float_value(self):
        from budget_app.utils.excel_import import _safe_int
        assert _safe_int(5.0) == 5

    def test_float_nan_returns_default(self):
        from budget_app.utils.excel_import import _safe_int
        assert _safe_int(float('nan')) is None

    def test_int_value(self):
        from budget_app.utils.excel_import import _safe_int
        assert _safe_int(5) == 5

    def test_valid_string(self):
        from budget_app.utils.excel_import import _safe_int
        assert _safe_int("5") == 5

    def test_non_numeric_string_returns_default(self):
        from budget_app.utils.excel_import import _safe_int
        assert _safe_int("abc") is None

    def test_float_string_truncates(self):
        from budget_app.utils.excel_import import _safe_int
        assert _safe_int("7.9") == 7


# ===========================================================================
# 3. ImportError
# ===========================================================================

class TestImportError:
    """Tests for the custom ImportError exception class"""

    def test_basic_message(self):
        from budget_app.utils.excel_import import ImportError
        err = ImportError("Something broke")
        assert str(err) == "Something broke"
        assert err.message == "Something broke"

    def test_with_sheet(self):
        from budget_app.utils.excel_import import ImportError
        err = ImportError("Bad data", sheet="Summary")
        assert "Sheet: Summary" in str(err)

    def test_with_row(self):
        from budget_app.utils.excel_import import ImportError
        err = ImportError("Bad data", row=5)
        assert "Row: 5" in str(err)

    def test_with_details(self):
        from budget_app.utils.excel_import import ImportError
        err = ImportError("Bad data", details="column missing")
        assert "Details: column missing" in str(err)

    def test_format_message_combines_parts(self):
        from budget_app.utils.excel_import import ImportError
        err = ImportError("Fail", sheet="CC", row=3, details="NaN")
        formatted = str(err)
        assert formatted == "Fail | Sheet: CC | Row: 3 | Details: NaN"


# ===========================================================================
# 4. ImportResult
# ===========================================================================

class TestImportResult:
    """Tests for the ImportResult dataclass"""

    def test_default_values(self):
        from budget_app.utils.excel_import import ImportResult
        result = ImportResult()
        assert result.credit_cards == 0
        assert result.loans == 0
        assert result.recurring_charges == 0
        assert result.accounts == 0
        assert result.paycheck_configs == 0
        assert result.shared_expenses == 0
        assert result.warnings == []
        assert result.errors == []

    def test_to_dict(self):
        from budget_app.utils.excel_import import ImportResult
        result = ImportResult(credit_cards=2, loans=1, warnings=["w1"])
        d = result.to_dict()
        assert d['credit_cards'] == 2
        assert d['loans'] == 1
        assert d['recurring_charges'] == 0
        assert d['accounts'] == 0
        assert d['paycheck_configs'] == 0
        assert d['shared_expenses'] == 0
        assert d['warnings'] == ["w1"]
        assert d['errors'] == []


# ===========================================================================
# 5. _clear_existing_data
# ===========================================================================

class TestClearExistingData:
    """Tests for _clear_existing_data - requires temp_db fixture"""

    def test_clears_all_tables(self, temp_db):
        from budget_app.utils.excel_import import _clear_existing_data
        from budget_app.models.database import Database
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.account import Account
        from budget_app.models.recurring_charge import RecurringCharge

        # Insert data into several tables
        Account(id=None, name='Chase', account_type='CHECKING',
                current_balance=5000.0, pay_type_code='C').save()
        CreditCard(id=None, pay_type_code='CH', name='Chase Freedom',
                   credit_limit=10000.0, current_balance=3000.0,
                   interest_rate=0.1899, due_day=15).save()
        RecurringCharge(id=None, name='Netflix', amount=-15.99,
                        day_of_month=15, payment_method='CH',
                        frequency='MONTHLY', amount_type='FIXED').save()

        # Verify data exists
        db = Database()
        assert db.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] > 0
        assert db.execute("SELECT COUNT(*) FROM credit_cards").fetchone()[0] > 0
        assert db.execute("SELECT COUNT(*) FROM recurring_charges").fetchone()[0] > 0

        _clear_existing_data()

        # All tables should be empty
        assert db.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM credit_cards").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM recurring_charges").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM recurring_charges").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM loans").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM shared_expenses").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM paycheck_configs").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM paycheck_deductions").fetchone()[0] == 0


# ===========================================================================
# 6. _import_credit_cards
# ===========================================================================

class TestImportCreditCards:
    """Tests for _import_credit_cards"""

    def _make_cc_dataframe(self, rows):
        """Build a DataFrame mimicking the Credit Card Info sheet."""
        return pd.DataFrame(rows, columns=[
            'Pay Type', 'List of Credit Cards', 'Balance',
            'Line Amount', 'Interest Rate', 'Due Date', 'Min Payment'
        ])

    def test_imports_credit_cards(self, temp_db):
        from budget_app.utils.excel_import import _import_credit_cards
        from budget_app.models.credit_card import CreditCard

        df = self._make_cc_dataframe([
            ['CH', 'Chase Freedom', 3000, 10000, 0.1899, 15, 50],
            ['AM', 'Amex Blue', 1500, 5000, 0.2199, 20, 35],
        ])
        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            cards_count, loans_count, warnings = _import_credit_cards(mock_xl)

        assert cards_count == 2
        assert loans_count == 0
        all_cards = CreditCard.get_all()
        assert len(all_cards) == 2
        names = {c.name for c in all_cards}
        assert 'Chase Freedom' in names
        assert 'Amex Blue' in names

    def test_imports_loans(self, temp_db):
        from budget_app.utils.excel_import import _import_credit_cards
        from budget_app.models.loan import Loan

        df = self._make_cc_dataframe([
            ['K1', '401k Loan 1', 7500, 10000, 0.045, None, 200],
            ['K2', '401k Loan 2', 3000, 5000, 0.05, None, 100],
        ])
        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            cards_count, loans_count, warnings = _import_credit_cards(mock_xl)

        assert cards_count == 0
        assert loans_count == 2
        all_loans = Loan.get_all()
        assert len(all_loans) == 2

    def test_skips_empty_pay_type(self, temp_db):
        from budget_app.utils.excel_import import _import_credit_cards

        df = self._make_cc_dataframe([
            ['', 'Empty Row', 0, 0, 0, 1, 0],
            [float('nan'), 'NaN Row', 0, 0, 0, 1, 0],
            ['T', 'Total Row', 0, 0, 0, 1, 0],
            ['CH', 'Valid Card', 100, 5000, 0.15, 10, 25],
        ])
        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            cards_count, loans_count, warnings = _import_credit_cards(mock_xl)

        assert cards_count == 1
        assert loans_count == 0

    def test_min_payment_type_calculated(self, temp_db):
        """Zero min payment -> CALCULATED"""
        from budget_app.utils.excel_import import _import_credit_cards
        from budget_app.models.credit_card import CreditCard

        df = self._make_cc_dataframe([
            ['CH', 'Calc Card', 500, 5000, 0.15, 10, 0],
        ])
        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            _import_credit_cards(mock_xl)

        card = CreditCard.get_all()[0]
        assert card.min_payment_type == 'CALCULATED'

    def test_min_payment_type_fixed(self, temp_db):
        """Positive min payment that != balance -> FIXED"""
        from budget_app.utils.excel_import import _import_credit_cards
        from budget_app.models.credit_card import CreditCard

        df = self._make_cc_dataframe([
            ['CH', 'Fixed Card', 1000, 5000, 0.15, 10, 50],
        ])
        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            _import_credit_cards(mock_xl)

        card = CreditCard.get_all()[0]
        assert card.min_payment_type == 'FIXED'
        assert card.min_payment_amount == 50

    def test_min_payment_type_full_balance(self, temp_db):
        """Min payment == balance (>0) -> FULL_BALANCE"""
        from budget_app.utils.excel_import import _import_credit_cards
        from budget_app.models.credit_card import CreditCard

        df = self._make_cc_dataframe([
            ['CH', 'Full Card', 200, 5000, 0.15, 10, 200],
        ])
        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            _import_credit_cards(mock_xl)

        card = CreditCard.get_all()[0]
        assert card.min_payment_type == 'FULL_BALANCE'

    def test_validation_warning_zero_limit(self, temp_db):
        from budget_app.utils.excel_import import _import_credit_cards

        df = self._make_cc_dataframe([
            ['CH', 'No Limit Card', 100, 0, 0.15, 10, 25],
        ])
        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            _, _, warnings = _import_credit_cards(mock_xl)

        assert any("no credit limit" in w for w in warnings)

    def test_validation_warning_invalid_due_day(self, temp_db):
        from budget_app.utils.excel_import import _import_credit_cards

        df = self._make_cc_dataframe([
            ['CH', 'Bad Due Card', 100, 5000, 0.15, 50, 25],
        ])
        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            _, _, warnings = _import_credit_cards(mock_xl)

        assert any("invalid due day" in w for w in warnings)


# ===========================================================================
# 7. _import_accounts
# ===========================================================================

class TestImportAccounts:
    """Tests for _import_accounts"""

    def _make_summary_df(self, rows):
        """Build a DataFrame mimicking the Summary sheet (no header)."""
        return pd.DataFrame(rows)

    def test_imports_three_accounts(self, temp_db):
        from budget_app.utils.excel_import import _import_accounts
        from budget_app.models.account import Account

        # Rows: index 0 is header row, 1=Chase, 2=Savings, 3=Misc
        df = self._make_summary_df([
            ['Header', 'X', 'Balance'],
            ['C', 'Chase', 5000.0],
            ['S', 'Savings', 12000.0],
            ['M', 'Misc', 250.0],
        ])
        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            count, warnings = _import_accounts(mock_xl)

        assert count == 3
        assert len(warnings) == 0
        all_accounts = Account.get_all()
        assert len(all_accounts) == 3
        names = {a.name for a in all_accounts}
        assert names == {'Chase', 'Savings', 'Miscellaneous'}

    def test_missing_rows_generates_warnings(self, temp_db):
        from budget_app.utils.excel_import import _import_accounts

        # Only 2 rows -> row index 2 and 3 will be out of bounds
        df = self._make_summary_df([
            ['Header', 'X', 'Balance'],
        ])
        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            count, warnings = _import_accounts(mock_xl)

        # All 3 accounts fail, plus "No accounts" warning
        assert count == 0
        assert any("No accounts" in w for w in warnings)


# ===========================================================================
# 8. _import_recurring_charges
# ===========================================================================

class TestImportRecurringCharges:
    """Tests for _import_recurring_charges"""

    def _make_charges_df(self, rows):
        return pd.DataFrame(rows, columns=[
            'Trans Name', 'Amount Due', 'Due Date', 'Payment Method'
        ])

    def test_imports_charges(self, temp_db):
        from budget_app.utils.excel_import import _import_recurring_charges

        df = self._make_charges_df([
            ['Netflix', 15.99, 15, 'CH'],
            ['Spotify', 9.99, 1, 'C'],
        ])
        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            count, warnings = _import_recurring_charges(mock_xl)

        assert count == 2

    def test_skips_rows_with_missing_due_date(self, temp_db):
        from budget_app.utils.excel_import import _import_recurring_charges

        df = self._make_charges_df([
            ['Netflix', 15.99, 15, 'CH'],
            ['No Date', 5.00, None, 'C'],
        ])
        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            count, warnings = _import_recurring_charges(mock_xl)

        assert count == 1
        assert any("missing due dates" in w for w in warnings)

    def test_deduplication(self, temp_db):
        from budget_app.utils.excel_import import _import_recurring_charges

        df = self._make_charges_df([
            ['Netflix', 15.99, 15, 'CH'],
            ['Netflix', 15.99, 15, 'CH'],  # duplicate
        ])
        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            count, warnings = _import_recurring_charges(mock_xl)

        assert count == 1

    def test_stops_after_row_40(self, temp_db):
        from budget_app.utils.excel_import import _import_recurring_charges

        rows = [[f'Charge {i}', 10.0, 15, 'C'] for i in range(50)]
        df = self._make_charges_df(rows)
        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            count, warnings = _import_recurring_charges(mock_xl)

        # idx 0..40 inclusive = 41 rows processed, idx > 40 stops
        assert count == 41

    def test_links_to_credit_card_by_name(self, temp_db):
        from budget_app.utils.excel_import import _import_recurring_charges
        from budget_app.models.credit_card import CreditCard
        from budget_app.models.recurring_charge import RecurringCharge
        from budget_app.models.database import Database

        # Insert a credit card directly via SQL to avoid the auto-creation
        # side effect in CreditCard.save() which creates a linked recurring charge
        db = Database()
        cursor = db.execute("""
            INSERT INTO credit_cards
            (pay_type_code, name, credit_limit, current_balance, interest_rate,
             due_day, min_payment_type, min_payment_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('CH', 'Chase Freedom', 10000.0, 3000.0, 0.1899, 15, 'CALCULATED', None))
        card_id = cursor.lastrowid
        db.commit()

        df = self._make_charges_df([
            ['Chase Freedom', 50.0, 15, 'C'],
        ])
        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            count, warnings = _import_recurring_charges(mock_xl)

        assert count == 1
        charges = RecurringCharge.get_all()
        assert len(charges) == 1
        assert charges[0].amount_type == 'CREDIT_CARD_BALANCE'
        assert charges[0].linked_card_id == card_id

    def test_special_frequency_for_high_day(self, temp_db):
        from budget_app.utils.excel_import import _import_recurring_charges
        from budget_app.models.recurring_charge import RecurringCharge

        df = self._make_charges_df([
            ['Special Charge', 100.0, 995, 'C'],
        ])
        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            count, warnings = _import_recurring_charges(mock_xl)

        assert count == 1
        charges = RecurringCharge.get_all()
        assert charges[0].frequency == 'SPECIAL'

    def test_invalid_day_skipped_with_warning(self, temp_db):
        from budget_app.utils.excel_import import _import_recurring_charges

        df = self._make_charges_df([
            ['Bad Day', 10.0, 500, 'C'],  # 500 is not 1-32 or 991-999
        ])
        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            count, warnings = _import_recurring_charges(mock_xl)

        assert count == 0
        assert any("invalid day" in w for w in warnings)


# ===========================================================================
# 9. _import_shared_expenses
# ===========================================================================

class TestImportSharedExpenses:
    """Tests for _import_shared_expenses - uses hardcoded data, no mocking needed"""

    def test_returns_five_expenses(self, temp_db):
        from budget_app.utils.excel_import import _import_shared_expenses
        from budget_app.models.shared_expense import SharedExpense

        mock_xl = MagicMock()
        count = _import_shared_expenses(mock_xl)

        assert count == 5
        all_expenses = SharedExpense.get_all()
        assert len(all_expenses) == 5

    def test_expense_names(self, temp_db):
        from budget_app.utils.excel_import import _import_shared_expenses
        from budget_app.models.shared_expense import SharedExpense

        mock_xl = MagicMock()
        _import_shared_expenses(mock_xl)

        names = {e.name for e in SharedExpense.get_all()}
        expected = {'Mortgage', 'Spaceship', 'SCCU Loan', 'Windows', 'UOAP'}
        assert names == expected

    def test_all_half_split(self, temp_db):
        from budget_app.utils.excel_import import _import_shared_expenses
        from budget_app.models.shared_expense import SharedExpense

        mock_xl = MagicMock()
        _import_shared_expenses(mock_xl)

        for e in SharedExpense.get_all():
            assert e.split_type == 'HALF'


# ===========================================================================
# 10. _import_paycheck_config
# ===========================================================================

class TestImportPaycheckConfig:
    """Tests for _import_paycheck_config"""

    def test_creates_config_and_deductions(self, temp_db):
        from budget_app.utils.excel_import import _import_paycheck_config
        from budget_app.models.paycheck import PaycheckConfig

        # Build a DataFrame large enough so iloc[2, 15] is accessible
        data = [[0] * 20 for _ in range(5)]
        data[2][15] = 4000.0  # gross pay
        df = pd.DataFrame(data)

        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            count, warnings = _import_paycheck_config(mock_xl)

        assert count == 1
        configs = PaycheckConfig.get_all()
        assert len(configs) == 1
        assert configs[0].gross_amount == 4000.0
        assert configs[0].pay_frequency == 'BIWEEKLY'

    def test_uses_default_gross_when_zero(self, temp_db):
        from budget_app.utils.excel_import import _import_paycheck_config
        from budget_app.models.paycheck import PaycheckConfig

        data = [[0] * 20 for _ in range(5)]
        data[2][15] = 0  # zero gross => fallback default
        df = pd.DataFrame(data)

        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            count, warnings = _import_paycheck_config(mock_xl)

        assert count == 1
        configs = PaycheckConfig.get_all()
        assert configs[0].gross_amount == 3876.65
        assert any("default gross pay" in w.lower() for w in warnings)

    def test_creates_ten_deductions(self, temp_db):
        from budget_app.utils.excel_import import _import_paycheck_config
        from budget_app.models.paycheck import PaycheckConfig, PaycheckDeduction
        from budget_app.models.database import Database

        data = [[0] * 20 for _ in range(5)]
        data[2][15] = 4000.0
        df = pd.DataFrame(data)

        mock_xl = MagicMock()
        with patch('pandas.read_excel', return_value=df):
            _import_paycheck_config(mock_xl)

        db = Database()
        deduction_count = db.execute(
            "SELECT COUNT(*) FROM paycheck_deductions"
        ).fetchone()[0]
        assert deduction_count == 10


# ===========================================================================
# 11. import_from_excel (integration-style tests)
# ===========================================================================

class TestImportFromExcel:
    """Integration tests for the top-level import_from_excel function"""

    def test_file_not_found(self, temp_db):
        from budget_app.utils.excel_import import import_from_excel
        with pytest.raises(FileNotFoundError, match="not found"):
            import_from_excel("/nonexistent/path/budget.xlsx")

    def test_missing_required_sheets(self, temp_db, tmp_path):
        from budget_app.utils.excel_import import import_from_excel
        from budget_app.utils.excel_import import ImportError as IE

        # Create a real file so path.exists() passes
        fake_file = tmp_path / "budget.xlsx"
        fake_file.touch()

        mock_xl = MagicMock(spec=pd.ExcelFile)
        mock_xl.sheet_names = ['Summary']  # missing Credit Card Info, Reoccuring Charges

        with patch('pandas.ExcelFile', return_value=mock_xl):
            with pytest.raises(IE, match="Missing required worksheets"):
                import_from_excel(str(fake_file))
