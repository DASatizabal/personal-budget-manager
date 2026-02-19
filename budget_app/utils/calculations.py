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

    # Build CC payment maps for linked card balance updates
    cc_payment_map = {}
    cc_name_map = {}
    card_id_to_code = {c.id: c for c in CreditCard.get_all()}
    for charge in RecurringCharge.get_all():
        if charge.linked_card_id and charge.linked_card_id in card_id_to_code:
            code = card_id_to_code[charge.linked_card_id].pay_type_code
            cc_payment_map[charge.id] = code
            cc_name_map[charge.name] = code

    # Initialize running balances
    running = starting_balances.copy()

    results = []
    for trans in transactions:
        method = trans.payment_method

        # Update the relevant balance
        if method in running:
            if method in cards:
                running[method] = running[method] - trans.amount  # CC: charges increase owed
            else:
                running[method] = running[method] + trans.amount

            # If this is a CC payment, also update the linked card's balance
            linked_card_code = None
            if trans.recurring_charge_id and trans.recurring_charge_id in cc_payment_map:
                linked_card_code = cc_payment_map[trans.recurring_charge_id]
            elif trans.description in cc_name_map:
                linked_card_code = cc_name_map[trans.description]
            if linked_card_code and linked_card_code in running:
                running[linked_card_code] += trans.amount

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


def find_first_negative_balance(starting_balance: float,
                                 transactions: List[Transaction],
                                 payment_method: str = 'C') -> Tuple[Optional[float], Optional[date]]:
    """
    Find the first (oldest) date where the balance goes negative.

    Args:
        starting_balance: Current balance
        transactions: Future transactions
        payment_method: Account to check (default 'C' for Chase)

    Returns:
        Tuple of (balance_on_that_date, first_negative_date) or (None, None) if never negative
    """
    today = datetime.now().date()

    # Filter transactions for the payment method
    relevant = [
        t for t in transactions
        if t.payment_method == payment_method
        and t.date_obj >= today
    ]

    if not relevant:
        # Check if starting balance is already negative
        if starting_balance < 0:
            return starting_balance, today
        return None, None

    # Calculate running balance and find first negative
    balance = starting_balance

    # Check if already negative
    if balance < 0:
        return balance, today

    for trans in sorted(relevant, key=lambda x: x.date):
        balance += trans.amount
        if balance < 0:
            return balance, trans.date_obj

    return None, None


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
    from ..models.shared_expense import SharedExpense

    if start_date is None:
        start_date = datetime.now().date()

    end_date = start_date + timedelta(days=months_ahead * 30)

    # Get all active recurring charges
    charges = RecurringCharge.get_all(active_only=True)

    # Get IDs of charges linked to shared expenses (Lisa Payments)
    # These are handled in payday generation, not as separate charges
    lisa_linked_ids = SharedExpense.get_linked_recurring_ids()

    # Get paycheck config for payday transactions
    paycheck = PaycheckConfig.get_current()

    # Build set of already-posted transactions to avoid duplicating
    # Key: (recurring_charge_id, date) for recurring charges
    # Key: (description, date) for non-recurring (payday, lisa, etc.)
    posted = Transaction.get_posted()
    posted_recurring = set()
    posted_other = set()
    for p in posted:
        if p.recurring_charge_id:
            posted_recurring.add((p.recurring_charge_id, p.date[:10]))
        else:
            posted_other.add((p.description, p.date[:10]))

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

            # Skip charges linked to Lisa Payments (handled in payday generation)
            if charge.id in lisa_linked_ids:
                continue

            # Check if this charge occurs on this day
            if charge.day_of_month == day:
                date_str = current_date.strftime('%Y-%m-%d')

                # Skip if this charge+date is already posted
                if (charge.id, date_str) in posted_recurring:
                    continue

                trans = Transaction(
                    id=None,
                    date=date_str,
                    description=charge.name,
                    amount=charge.get_actual_amount(),
                    payment_method=charge.payment_method,
                    recurring_charge_id=charge.id,
                    is_posted=False
                )
                transactions.append(trans)

        current_date += timedelta(days=1)

    # Handle special charges (mortgage on specific schedule, etc.)
    # Also skip Lisa-linked charges
    transactions.extend(_generate_special_charges(start_date, end_date, charges, lisa_linked_ids, posted_recurring))

    # Generate payday transactions
    if paycheck:
        transactions.extend(_generate_payday_transactions(start_date, end_date, paycheck, posted_other))

    # Generate credit card interest charges
    transactions = _generate_interest_charges(start_date, end_date, transactions, posted_other)

    # Sort by date
    transactions.sort(key=lambda x: x.date)

    return transactions


def _generate_special_charges(start_date: date, end_date: date,
                              charges: List[RecurringCharge],
                              lisa_linked_ids: set = None,
                              posted_recurring: set = None) -> List[Transaction]:
    """Generate transactions for special frequency charges"""
    transactions = []

    if lisa_linked_ids is None:
        lisa_linked_ids = set()
    if posted_recurring is None:
        posted_recurring = set()

    special_charges = [c for c in charges if c.frequency == 'SPECIAL']

    for charge in special_charges:
        # Skip charges linked to Lisa Payments
        if charge.id in lisa_linked_ids:
            continue
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

                date_str = current.strftime('%Y-%m-%d')
                # Skip if already posted
                if (charge.id, date_str) not in posted_recurring:
                    trans = Transaction(
                        id=None,
                        date=date_str,
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
                    date_str = current.strftime('%Y-%m-%d')
                    # Skip if already posted
                    if (charge.id, date_str) not in posted_recurring:
                        trans = Transaction(
                            id=None,
                            date=date_str,
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
                                  paycheck: PaycheckConfig,
                                  posted_other: set = None) -> List[Transaction]:
    """Generate payday transactions based on paycheck configuration"""
    from ..models.shared_expense import SharedExpense
    import calendar

    transactions = []

    if posted_other is None:
        posted_other = set()

    if paycheck.pay_frequency == 'BIWEEKLY':
        # Use effective_date as the anchor for the biweekly schedule.
        # This is a known real payday — we step forward/backward by 14 days.
        if paycheck.effective_date:
            anchor = date.fromisoformat(paycheck.effective_date)
        else:
            # Fallback: find the first pay-day-of-week on or after start_date
            anchor = start_date
            pay_dow = paycheck.pay_day_of_week  # 0=Mon, 4=Fri
            days_ahead = (pay_dow - anchor.weekday()) % 7
            anchor += timedelta(days=days_ahead)

        # Walk backward from anchor to cover the start of start_date's month
        # (needed for accurate payday-per-month counting)
        month_start = date(start_date.year, start_date.month, 1)
        current = anchor
        while current - timedelta(days=14) >= month_start:
            current -= timedelta(days=14)

        # Collect ALL paydays (from month start to end_date) for counting
        all_paydays = []
        while current <= end_date:
            all_paydays.append(current)
            current += timedelta(days=14)

        # Count paydays per month (using all paydays, including past ones in current month)
        paydays_per_month = {}
        for payday in all_paydays:
            month_key = (payday.year, payday.month)
            paydays_per_month[month_key] = paydays_per_month.get(month_key, 0) + 1

        # Filter to only paydays >= start_date for transaction generation
        paydays = [p for p in all_paydays if p >= start_date]

        # Generate transactions for each payday
        for payday in paydays:
            date_str = payday.strftime('%Y-%m-%d')

            # Payday transaction - skip if already posted
            if ('Payday', date_str) not in posted_other:
                trans = Transaction(
                    id=None,
                    date=date_str,
                    description='Payday',
                    amount=paycheck.net_pay,
                    payment_method='C',
                    recurring_charge_id=None,
                    is_posted=False
                )
                transactions.append(trans)

            # Lisa payment - based on number of paydays in this month
            month_key = (payday.year, payday.month)
            paycheck_count = paydays_per_month.get(month_key, 2)
            lisa_amount = SharedExpense.calculate_lisa_payment(paycheck_count)

            if lisa_amount > 0 and ('Lisa Payment', date_str) not in posted_other:
                lisa_trans = Transaction(
                    id=None,
                    date=date_str,
                    description='Lisa Payment',
                    amount=-lisa_amount,  # Negative because it's an expense
                    payment_method='C',
                    recurring_charge_id=None,
                    is_posted=False
                )
                transactions.append(lisa_trans)

            # Add LDBPD marker (Last Day Before PayDay)
            ldbpd_date = payday - timedelta(days=1)
            ldbpd_date_str = ldbpd_date.strftime('%Y-%m-%d')
            if ldbpd_date >= start_date and ('LDBPD', ldbpd_date_str) not in posted_other:
                ldbpd = Transaction(
                    id=None,
                    date=ldbpd_date_str + ' 23:59:59',
                    description='LDBPD',
                    amount=0,
                    payment_method='C',
                    recurring_charge_id=None,
                    is_posted=False,
                    notes='Pay period boundary marker'
                )
                transactions.append(ldbpd)

    return transactions


def _generate_interest_charges(start_date: date, end_date: date,
                                transactions: List[Transaction],
                                posted_other: set = None) -> List[Transaction]:
    """
    Generate interest charges for credit cards.
    Interest is charged 3 days after due date, based on previous day's balance.
    """
    import calendar

    if posted_other is None:
        posted_other = set()

    # Get credit cards with interest rate and due day
    cards = [c for c in CreditCard.get_all() if c.interest_rate > 0 and c.due_day]
    if not cards:
        return transactions

    # Get starting balances
    starting_balances = get_starting_balances()

    # Build map of recurring_charge_id -> pay_type_code for CC payments
    cc_payment_map = {}
    cc_name_map = {}
    card_id_to_code = {c.id: c.pay_type_code for c in CreditCard.get_all()}
    for charge in RecurringCharge.get_all():
        if charge.linked_card_id and charge.linked_card_id in card_id_to_code:
            cc_payment_map[charge.id] = card_id_to_code[charge.linked_card_id]
            cc_name_map[charge.name] = card_id_to_code[charge.linked_card_id]

    # Sort transactions by date for processing
    sorted_trans = sorted(transactions, key=lambda x: x.date)

    # Track running balances for each card
    running = {c.pay_type_code: starting_balances.get(c.pay_type_code, 0) for c in cards}

    # Generate interest dates for each card for each month
    interest_charges = []
    current_month = date(start_date.year, start_date.month, 1)

    while current_month <= end_date:
        year = current_month.year
        month = current_month.month
        days_in_month = calendar.monthrange(year, month)[1]

        for card in cards:
            # Calculate interest charge date (due_day + 3)
            interest_day = card.due_day + 3

            # Handle month rollover
            if interest_day > days_in_month:
                # Roll to next month
                if month == 12:
                    interest_date = date(year + 1, 1, interest_day - days_in_month)
                else:
                    interest_date = date(year, month + 1, interest_day - days_in_month)
            else:
                interest_date = date(year, month, interest_day)

            # Skip if outside our date range
            if interest_date < start_date or interest_date > end_date:
                continue

            # Calculate balance on the day before interest date
            balance_date = interest_date - timedelta(days=1)
            balance_date_str = balance_date.strftime('%Y-%m-%d')

            # Calculate running balance up to balance_date
            card_balance = starting_balances.get(card.pay_type_code, 0)
            for trans in sorted_trans:
                if trans.date > balance_date_str:
                    break

                # Direct transactions to this card (charges are negative, increase owed)
                if trans.payment_method == card.pay_type_code:
                    card_balance -= trans.amount

                # Credit card payments reduce the balance
                linked_code = None
                if trans.recurring_charge_id and trans.recurring_charge_id in cc_payment_map:
                    linked_code = cc_payment_map[trans.recurring_charge_id]
                elif trans.description in cc_name_map:
                    linked_code = cc_name_map[trans.description]
                if linked_code == card.pay_type_code:
                    card_balance += trans.amount  # trans.amount is negative

            # Also include any interest charges we've already generated
            for ic in interest_charges:
                if ic.date <= balance_date_str and ic.payment_method == card.pay_type_code:
                    card_balance -= ic.amount  # interest is negative, increases owed

            # Only charge interest if there's a balance owed
            if card_balance > 0:
                # Monthly interest = balance * (APR / 12)
                monthly_rate = card.interest_rate / 12
                interest_amount = round(card_balance * monthly_rate, 2)
                interest_date_str = interest_date.strftime('%Y-%m-%d')
                interest_desc = f"{card.name} Interest"

                # Skip if already posted
                if interest_amount > 0 and (interest_desc, interest_date_str) not in posted_other:
                    interest_trans = Transaction(
                        id=None,
                        date=interest_date_str,
                        description=interest_desc,
                        amount=-interest_amount,  # Negative: interest is a charge
                        payment_method=card.pay_type_code,
                        recurring_charge_id=None,
                        is_posted=False
                    )
                    interest_charges.append(interest_trans)

        # Move to next month
        if current_month.month == 12:
            current_month = date(current_month.year + 1, 1, 1)
        else:
            current_month = date(current_month.year, current_month.month + 1, 1)

    # Add interest charges to transactions
    transactions.extend(interest_charges)

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
