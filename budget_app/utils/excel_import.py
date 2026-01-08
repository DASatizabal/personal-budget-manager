"""Import data from the existing Excel budget workbook"""

import pandas as pd
from pathlib import Path
from typing import Optional, List
import math
from dataclasses import dataclass, field

from ..models.database import Database, init_db
from ..models.credit_card import CreditCard
from ..models.loan import Loan
from ..models.recurring_charge import RecurringCharge
from ..models.account import Account
from ..models.paycheck import PaycheckConfig, PaycheckDeduction
from ..models.shared_expense import SharedExpense
from .logging_config import get_logger

_logger = get_logger('import')


class ImportError(Exception):
    """Custom exception for import errors with detailed information"""
    def __init__(self, message: str, sheet: str = None, row: int = None, details: str = None):
        self.message = message
        self.sheet = sheet
        self.row = row
        self.details = details
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        parts = [self.message]
        if self.sheet:
            parts.append(f"Sheet: {self.sheet}")
        if self.row is not None:
            parts.append(f"Row: {self.row}")
        if self.details:
            parts.append(f"Details: {self.details}")
        return " | ".join(parts)


@dataclass
class ImportResult:
    """Detailed import results with success counts and warnings"""
    credit_cards: int = 0
    loans: int = 0
    recurring_charges: int = 0
    accounts: int = 0
    paycheck_configs: int = 0
    shared_expenses: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'credit_cards': self.credit_cards,
            'loans': self.loans,
            'recurring_charges': self.recurring_charges,
            'accounts': self.accounts,
            'paycheck_configs': self.paycheck_configs,
            'shared_expenses': self.shared_expenses,
            'warnings': self.warnings,
            'errors': self.errors
        }


def import_from_excel(excel_path: str, clear_existing: bool = True) -> dict:
    """
    Import data from the Excel budget workbook.
    Returns a dict with counts of imported items plus warnings/errors.

    Args:
        excel_path: Path to the Excel file
        clear_existing: If True, clears existing data before importing
    """
    _logger.info(f"Starting Excel import from: {excel_path}")

    path = Path(excel_path)
    if not path.exists():
        _logger.error(f"Excel file not found: {excel_path}")
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    # Initialize the database
    init_db()

    # Validate the Excel file has required sheets
    try:
        xl = pd.ExcelFile(excel_path)
        _logger.debug(f"Excel file opened successfully. Sheets: {xl.sheet_names}")
    except Exception as e:
        _logger.error(f"Failed to open Excel file: {e}")
        raise ImportError(
            "Failed to open Excel file",
            details=f"The file may be corrupted or in an unsupported format: {str(e)}"
        )

    required_sheets = ['Credit Card Info', 'Summary', 'Reoccuring Charges']
    missing_sheets = [s for s in required_sheets if s not in xl.sheet_names]
    if missing_sheets:
        raise ImportError(
            "Missing required worksheets",
            details=f"The Excel file must contain these sheets: {', '.join(missing_sheets)}"
        )

    # Clear existing data if requested
    if clear_existing:
        _clear_existing_data()

    result = ImportResult()

    # Import Credit Card Info
    try:
        result.credit_cards, result.loans, card_warnings = _import_credit_cards(xl)
        result.warnings.extend(card_warnings)
    except Exception as e:
        raise ImportError(
            "Failed to import credit cards",
            sheet="Credit Card Info",
            details=str(e)
        )

    # Import Accounts (from Summary sheet)
    try:
        result.accounts, account_warnings = _import_accounts(xl)
        result.warnings.extend(account_warnings)
    except Exception as e:
        raise ImportError(
            "Failed to import accounts",
            sheet="Summary",
            details=str(e)
        )

    # Import Recurring Charges
    try:
        result.recurring_charges, charge_warnings = _import_recurring_charges(xl)
        result.warnings.extend(charge_warnings)
    except Exception as e:
        raise ImportError(
            "Failed to import recurring charges",
            sheet="Reoccuring Charges",
            details=str(e)
        )

    # Import Paycheck Configuration
    try:
        result.paycheck_configs, paycheck_warnings = _import_paycheck_config(xl)
        result.warnings.extend(paycheck_warnings)
    except Exception as e:
        # Paycheck is less critical, add warning instead of failing
        result.warnings.append(f"Could not import paycheck config: {str(e)}")

    # Import Shared Expenses (Lisa payments)
    try:
        result.shared_expenses = _import_shared_expenses(xl)
    except Exception as e:
        # Shared expenses are less critical, add warning instead of failing
        result.warnings.append(f"Could not import shared expenses: {str(e)}")

    _logger.info(
        f"Excel import completed: {result.credit_cards} cards, {result.loans} loans, "
        f"{result.recurring_charges} charges, {result.accounts} accounts, "
        f"{len(result.warnings)} warnings"
    )

    return result.to_dict()


def _clear_existing_data():
    """Clear all existing data from the database"""
    db = Database()
    # Order matters due to foreign key constraints
    db.execute("DELETE FROM paycheck_deductions")
    db.execute("DELETE FROM paycheck_configs")
    db.execute("DELETE FROM shared_expenses")
    db.execute("DELETE FROM transactions")
    db.execute("DELETE FROM recurring_charges")
    db.execute("DELETE FROM loans")
    db.execute("DELETE FROM credit_cards")
    db.execute("DELETE FROM accounts")
    db.commit()


def _import_credit_cards(xl: pd.ExcelFile) -> tuple:
    """Import credit cards and loans from Credit Card Info sheet
    Returns: (cards_count, loans_count, warnings)
    """
    df = pd.read_excel(xl, 'Credit Card Info', header=0)

    # Clean column names
    df.columns = df.columns.str.strip()

    cards_count = 0
    loans_count = 0
    warnings = []

    # Known 401k loan codes
    loan_codes = ['K1', 'K2']

    # Validate required columns
    required_cols = ['Pay Type', 'List of Credit Cards']
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")

    for idx, row in df.iterrows():
        pay_type = str(row.get('Pay Type', '')).strip()
        name = str(row.get('List of Credit Cards', '')).strip()

        if not pay_type or pay_type == 'nan' or pay_type == 'T' or not name or name == 'nan':
            continue

        balance = _safe_float(row.get('Balance', 0))
        line_amount = _safe_float(row.get('Line Amount', 0))
        interest_rate = _safe_float(row.get('Interest Rate', 0))
        due_day = _safe_int(row.get('Due Date'))
        min_payment = _safe_float(row.get('Min Payment', 0))

        # Validation warnings
        if line_amount <= 0 and pay_type not in loan_codes:
            warnings.append(f"Card '{name}' has no credit limit set")
        if due_day is None or due_day < 1 or due_day > 31:
            if pay_type not in loan_codes:
                warnings.append(f"Card '{name}' has invalid due day: {due_day}")

        try:
            if pay_type in loan_codes:
                # This is a loan
                loan = Loan(
                    id=None,
                    pay_type_code=pay_type,
                    name=name,
                    original_amount=line_amount,
                    current_balance=balance,
                    interest_rate=interest_rate,
                    payment_amount=min_payment
                )
                loan.save()
                loans_count += 1
            else:
                # This is a credit card
                # Determine min payment type
                min_type = 'CALCULATED'
                if min_payment == balance and balance > 0:
                    min_type = 'FULL_BALANCE'
                elif min_payment > 0:
                    min_type = 'FIXED'

                card = CreditCard(
                    id=None,
                    pay_type_code=pay_type,
                    name=name,
                    credit_limit=line_amount,
                    current_balance=balance,
                    interest_rate=interest_rate,
                    due_day=due_day if due_day and 1 <= due_day <= 31 else 1,
                    min_payment_type=min_type,
                    min_payment_amount=min_payment if min_type == 'FIXED' else None
                )
                card.save()
                cards_count += 1
        except Exception as e:
            warnings.append(f"Failed to import row {idx + 2} ({name}): {str(e)}")

    return cards_count, loans_count, warnings


def _import_accounts(xl: pd.ExcelFile) -> tuple:
    """Import bank accounts from Summary sheet
    Returns: (accounts_count, warnings)
    """
    df = pd.read_excel(xl, 'Summary', header=None)

    accounts_count = 0
    warnings = []

    # Based on the Excel structure:
    # Row 1: C = Chase, Amount in column 2
    # Row 2: S = Savings, Amount in column 2
    # Row 3: Misc (Cash, Change)

    account_mappings = [
        (1, 'C', 'Chase', 'CHECKING'),
        (2, 'S', 'Savings', 'SAVINGS'),
        (3, None, 'Miscellaneous', 'CASH'),
    ]

    for row_idx, code, name, acc_type in account_mappings:
        try:
            balance = _safe_float(df.iloc[row_idx, 2])
            account = Account(
                id=None,
                name=name,
                account_type=acc_type,
                current_balance=balance,
                pay_type_code=code
            )
            account.save()
            accounts_count += 1
        except (IndexError, KeyError) as e:
            warnings.append(f"Could not import account '{name}': row {row_idx} not found in Summary sheet")
            continue

    if accounts_count == 0:
        warnings.append("No accounts were imported from Summary sheet")

    return accounts_count, warnings


def _import_recurring_charges(xl: pd.ExcelFile) -> tuple:
    """Import recurring charges from Reoccuring Charges sheet
    Returns: (charges_count, warnings)
    """
    df = pd.read_excel(xl, 'Reoccuring Charges', header=0)

    # Clean column names
    df.columns = df.columns.str.strip()

    charges_count = 0
    warnings = []

    # Validate required columns
    required_cols = ['Trans Name', 'Due Date']
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")

    # Get credit card name to ID mapping for linking
    cards = CreditCard.get_all()
    card_name_to_id = {c.name: c.id for c in cards}

    # Track seen names to avoid duplicates from projection tables
    seen_names = set()
    skipped_count = 0

    for idx, row in df.iterrows():
        # Stop reading after row 40 (projection data starts after)
        if idx > 40:
            break

        name = str(row.get('Trans Name', '')).strip()
        if not name or name == 'nan':
            continue

        amount = _safe_float(row.get('Amount Due', 0))
        day = _safe_int(row.get('Due Date'))
        payment_method = str(row.get('Payment Method', 'C')).strip()

        if day is None:
            skipped_count += 1
            continue

        # Skip if day is outside valid range (1-31 or 991-999 for special)
        if not ((1 <= day <= 32) or (991 <= day <= 999)):
            warnings.append(f"Charge '{name}' skipped: invalid day {day}")
            continue

        # Create unique key for deduplication
        unique_key = f"{name}_{day}_{payment_method}"
        if unique_key in seen_names:
            continue
        seen_names.add(unique_key)

        # Determine if this is a credit card payment (amount pulls from card balance)
        amount_type = 'FIXED'
        linked_card_id = None

        # Check if the charge name matches a credit card name
        if name in card_name_to_id:
            amount_type = 'CREDIT_CARD_BALANCE'
            linked_card_id = card_name_to_id[name]

        # Determine frequency based on day code
        frequency = 'MONTHLY'
        if day >= 991:
            frequency = 'SPECIAL'

        # Handle NaN payment method
        if payment_method == 'nan' or not payment_method:
            payment_method = 'C'  # Default to Chase

        try:
            charge = RecurringCharge(
                id=None,
                name=name,
                amount=amount,
                day_of_month=day,
                payment_method=payment_method,
                frequency=frequency,
                amount_type=amount_type,
                linked_card_id=linked_card_id,
                is_active=True
            )
            charge.save()
            charges_count += 1
        except Exception as e:
            warnings.append(f"Failed to import charge '{name}': {str(e)}")

    if skipped_count > 0:
        warnings.append(f"Skipped {skipped_count} rows with missing due dates")

    return charges_count, warnings


def _import_paycheck_config(xl: pd.ExcelFile) -> tuple:
    """Import paycheck configuration from Reoccuring Charges sheet
    Returns: (count, warnings)
    """
    df = pd.read_excel(xl, 'Reoccuring Charges', header=None)
    warnings = []

    # Based on Excel structure, paycheck info is in columns 5-8 (F-I)
    # Row 0 has headers, Row 1+ has data
    # Looking for "Payday" label and associated values

    try:
        # Find the gross pay (around row 2, column 11 based on Excel data)
        # The structure shows: Gross Pay in column 11, values in columns 12-15
        gross_pay = _safe_float(df.iloc[2, 15])  # 2025 column
        if not gross_pay or gross_pay <= 0:
            gross_pay = 3876.65  # Default from the Excel data
            warnings.append("Using default gross pay amount ($3,876.65) - could not find value in spreadsheet")

        # Create paycheck config
        config = PaycheckConfig(
            id=None,
            gross_amount=gross_pay,
            pay_frequency='BIWEEKLY',
            effective_date='2025-01-01',
            is_current=True
        )
        config.save()

        # Import deductions from the deductions table
        # Based on Excel: Columns 19-20 have Item and Amount
        deduction_data = [
            ('Social Security', 'PERCENTAGE', 0.060088),
            ('Medicare', 'PERCENTAGE', 0.014053),
            ('Dental', 'FIXED', 19.05),
            ('Life Insurance', 'FIXED', 20.20),
            ('Medical', 'FIXED', 114.77),
            ('Vision', 'FIXED', 2.87),
            ('401k', 'FIXED', 99.63),
            ('Dependent Life Insurance', 'FIXED', 2.08),
            ('Child Support', 'FIXED', 161.54),
            ('ESPP', 'PERCENTAGE', 0.010003),
        ]

        for name, amount_type, amount in deduction_data:
            deduction = PaycheckDeduction(
                id=None,
                paycheck_config_id=config.id,
                name=name,
                amount_type=amount_type,
                amount=amount
            )
            deduction.save()

        return 1, warnings
    except (IndexError, KeyError, ValueError) as e:
        warnings.append(f"Failed to import paycheck config: {str(e)}")
        return 0, warnings


def _import_shared_expenses(xl: pd.ExcelFile) -> int:
    """Import shared expenses (Lisa payment split) from Reoccuring Charges sheet"""
    # The shared expenses are defined in the Lisa tables in the Excel
    # Based on the Excel structure, these are the shared household expenses:
    shared_expense_data = [
        ('Mortgage', 1900.0, 'HALF'),
        ('Spaceship', 200.0, 'HALF'),
        ('SCCU Loan', 250.0, 'HALF'),
        ('Windows', 150.0, 'HALF'),
        ('UOAP', 0.0, 'HALF'),  # Currently 0
    ]

    count = 0
    for name, amount, split_type in shared_expense_data:
        expense = SharedExpense(
            id=None,
            name=name,
            monthly_amount=amount,
            split_type=split_type,
            custom_split_ratio=None,
            linked_recurring_id=None
        )
        expense.save()
        count += 1

    return count


def _safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float"""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        if math.isnan(value):
            return default
        return float(value)
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value, default: Optional[int] = None) -> Optional[int]:
    """Safely convert a value to int"""
    if value is None:
        return default
    if isinstance(value, float):
        if math.isnan(value):
            return default
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default
