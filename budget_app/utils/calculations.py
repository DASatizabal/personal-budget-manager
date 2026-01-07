"""Calculation utilities for budget projections"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from ..models.transaction import Transaction
from ..models.recurring_charge import RecurringCharge
from ..models.credit_card import CreditCard
from ..models.loan import Loan
from ..models.account import Account
from ..models.paycheck import PaycheckConfig


@dataclass
class BalanceSnapshot:
    """A snapshot of all balances at a point in time"""
    date: date
    chase_balance: float
    savings_balance: float
    card_balances: Dict[str, float]  # pay_type_code -> balance
    card_available: Dict[str, float]  # pay_type_code -> available credit
    total_cc_utilization: float


def calculate_running_balances(transactions: List[Transaction],
                               starting_balances: Dict[str, float]) -> List[Dict]:
    """
    Calculate running balances for all accounts after each transaction.

    Args:
        transactions: List of transactions sorted by date
        starting_balances: Dict of pay_type_code -> starting balance

    Returns:
        List of dicts with transaction and running balances
    """
    # Get all credit cards for calculating available credit
    cards = {c.pay_type_code: c for c in CreditCard.get_all()}

    # Initialize running balances
    running = starting_balances.copy()

    results = []
    for trans in transactions:
        method = trans.payment_method

        # Update the relevant balance
        if method in running:
            running[method] = running[method] + trans.amount

        # Calculate available credit for credit cards
        available = {}
        for code, card in cards.items():
            if code in running:
                # For credit cards, available = limit - balance
                # Note: running balance for CC is the balance owed (positive = debt)
                available[code] = card.credit_limit - running.get(code, 0)

        # Calculate total utilization
        total_balance = sum(running.get(c.pay_type_code, 0) for c in cards.values())
        total_limit = sum(c.credit_limit for c in cards.values())
        utilization = total_balance / total_limit if total_limit > 0 else 0

        results.append({
            'transaction': trans,
            'running_balances': running.copy(),
            'available_credit': available.copy(),
            'total_utilization': utilization
        })

    return results


def calculate_90_day_minimum(starting_balance: float,
                             transactions: List[Transaction],
                             payment_method: str = 'C') -> Tuple[float, Optional[date]]:
    """
    Calculate the minimum balance that will occur in the next 90 days.

    Args:
        starting_balance: Current balance
        transactions: Future transactions
        payment_method: Account to check (default 'C' for Chase)

    Returns:
        Tuple of (minimum_balance, date_of_minimum)
    """
    today = datetime.now().date()
    end_date = today + timedelta(days=90)

    # Filter transactions for the payment method and date range
    relevant = [
        t for t in transactions
        if t.payment_method == payment_method
        and today <= t.date_obj <= end_date
    ]

    if not relevant:
        return starting_balance, None

    # Calculate running balance and find minimum
    balance = starting_balance
    min_balance = balance
    min_date = today

    for trans in sorted(relevant, key=lambda x: x.date):
        balance += trans.amount
        if balance < min_balance:
            min_balance = balance
            min_date = trans.date_obj

    return min_balance, min_date


def generate_future_transactions(months_ahead: int = 12,
                                 start_date: date = None) -> List[Transaction]:
    """
    Generate future transactions based on recurring charges.

    Args:
        months_ahead: Number of months to project
        start_date: Starting date (defaults to today)

    Returns:
        List of generated Transaction objects (not saved)
    """
    if start_date is None:
        start_date = datetime.now().date()

    end_date = start_date + timedelta(days=months_ahead * 30)

    # Get all active recurring charges
    charges = RecurringCharge.get_all(active_only=True)

    # Get paycheck config for payday transactions
    paycheck = PaycheckConfig.get_current()

    transactions = []
    current_date = start_date

    while current_date <= end_date:
        year = current_date.year
        month = current_date.month
        day = current_date.day

        for charge in charges:
            # Skip special frequency charges for now (handled separately)
            if charge.frequency == 'SPECIAL':
                continue

            # Check if this charge occurs on this day
            if charge.day_of_month == day:
                trans = Transaction(
                    id=None,
                    date=current_date.strftime('%Y-%m-%d'),
                    description=charge.name,
                    amount=charge.get_actual_amount(),
                    payment_method=charge.payment_method,
                    recurring_charge_id=charge.id,
                    is_posted=False
                )
                transactions.append(trans)

        current_date += timedelta(days=1)

    # Handle special charges (mortgage on specific schedule, etc.)
    transactions.extend(_generate_special_charges(start_date, end_date, charges))

    # Generate payday transactions
    if paycheck:
        transactions.extend(_generate_payday_transactions(start_date, end_date, paycheck))

    # Sort by date
    transactions.sort(key=lambda x: x.date)

    return transactions


def _generate_special_charges(start_date: date, end_date: date,
                              charges: List[RecurringCharge]) -> List[Transaction]:
    """Generate transactions for special frequency charges"""
    transactions = []

    special_charges = [c for c in charges if c.frequency == 'SPECIAL']

    for charge in special_charges:
        # Special codes:
        # 991 = Mortgage (bi-weekly or specific dates)
        # 992 = Spaceship (monthly on specific date)
        # 993 = SCCU Loan
        # 994 = Windows
        # 995 = UOAP
        # 996 = Lisa (2 paycheck months)
        # 997 = Lisa3 (3 paycheck months)
        # 998 = LisaUOAP
        # 999 = Lisa3UOAP

        if charge.day_of_month == 991:
            # Mortgage - assume bi-weekly on Fridays
            current = start_date
            while current <= end_date:
                # Find next Friday
                days_until_friday = (4 - current.weekday()) % 7
                if days_until_friday == 0:
                    days_until_friday = 7
                current += timedelta(days=days_until_friday)
                if current > end_date:
                    break

                # Every other Friday
                trans = Transaction(
                    id=None,
                    date=current.strftime('%Y-%m-%d'),
                    description=charge.name,
                    amount=charge.amount,
                    payment_method='C',
                    recurring_charge_id=charge.id,
                    is_posted=False
                )
                transactions.append(trans)
                current += timedelta(days=14)

        elif charge.day_of_month in [992, 993, 994, 995]:
            # Monthly special charges - treat as monthly on the 15th
            current = date(start_date.year, start_date.month, 15)
            while current <= end_date:
                if current >= start_date:
                    trans = Transaction(
                        id=None,
                        date=current.strftime('%Y-%m-%d'),
                        description=charge.name,
                        amount=charge.amount,
                        payment_method='C',
                        recurring_charge_id=charge.id,
                        is_posted=False
                    )
                    transactions.append(trans)

                # Move to next month
                if current.month == 12:
                    current = date(current.year + 1, 1, 15)
                else:
                    current = date(current.year, current.month + 1, 15)

    return transactions


def _generate_payday_transactions(start_date: date, end_date: date,
                                  paycheck: PaycheckConfig) -> List[Transaction]:
    """Generate payday transactions based on paycheck configuration"""
    transactions = []

    if paycheck.pay_frequency == 'BIWEEKLY':
        # Assume payday is every other Friday
        # Find the first Friday from start_date
        current = start_date
        days_until_friday = (4 - current.weekday()) % 7
        current += timedelta(days=days_until_friday)

        while current <= end_date:
            trans = Transaction(
                id=None,
                date=current.strftime('%Y-%m-%d'),
                description='Payday',
                amount=paycheck.net_pay,
                payment_method='C',
                recurring_charge_id=None,
                is_posted=False
            )
            transactions.append(trans)

            # Add LDBPD marker (Last Day Before PayDay)
            ldbpd_date = current - timedelta(days=1)
            if ldbpd_date >= start_date:
                ldbpd = Transaction(
                    id=None,
                    date=ldbpd_date.strftime('%Y-%m-%d') + ' 23:59:59',
                    description='LDBPD',
                    amount=0,
                    payment_method='C',
                    recurring_charge_id=None,
                    is_posted=False,
                    notes='Pay period boundary marker'
                )
                transactions.append(ldbpd)

            current += timedelta(days=14)

    return transactions


def get_starting_balances() -> Dict[str, float]:
    """Get the starting balances for all payment methods"""
    balances = {}

    # Get account balances
    for account in Account.get_all():
        if account.pay_type_code:
            balances[account.pay_type_code] = account.current_balance

    # Get credit card balances
    for card in CreditCard.get_all():
        balances[card.pay_type_code] = card.current_balance

    # Get loan balances
    for loan in Loan.get_all():
        balances[loan.pay_type_code] = loan.current_balance

    return balances
