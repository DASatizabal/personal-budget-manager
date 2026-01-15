"""Credit Card Payoff Calculator with multiple strategies"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import copy


@dataclass
class CardPayoffInfo:
    """Information about a card for payoff calculations"""
    card_id: int
    name: str
    balance: float
    apr: float
    min_payment: float
    credit_limit: float

    @property
    def utilization(self) -> float:
        if self.credit_limit == 0:
            return 0.0
        return self.balance / self.credit_limit

    @property
    def monthly_interest_rate(self) -> float:
        return self.apr / 12


@dataclass
class PaymentScheduleEntry:
    """A single payment in the schedule"""
    date: date
    card_name: str
    card_id: int
    amount: float
    principal: float
    interest: float
    remaining_balance: float


@dataclass
class PayoffResult:
    """Result of a payoff calculation"""
    method: str
    method_description: str
    payoff_date: date
    months_to_payoff: int
    total_interest: float
    total_payments: float
    monthly_payment_avg: float
    payment_schedule: List[PaymentScheduleEntry]
    card_payoff_order: List[str]


def calculate_minimum_payment(balance: float, apr: float, fixed_min: Optional[float] = None) -> float:
    """Calculate minimum payment for a card"""
    if fixed_min:
        return min(fixed_min, balance)
    # Standard calculation: 1% of balance + monthly interest, minimum $25
    monthly_interest = balance * (apr / 12)
    calculated = balance * 0.01 + monthly_interest
    return max(calculated, min(25.0, balance))


def _simulate_payoff(
    cards: List[CardPayoffInfo],
    monthly_extra: float,
    prioritize_func,
    max_months: int = 360
) -> PayoffResult:
    """
    Simulate paying off cards with a given prioritization strategy.

    Args:
        cards: List of cards to pay off
        monthly_extra: Extra amount available beyond minimums
        prioritize_func: Function that takes list of cards and returns sorted list
        max_months: Maximum months to simulate

    Returns:
        PayoffResult with complete payment schedule
    """
    # Deep copy cards to avoid modifying originals
    working_cards = [copy.copy(c) for c in cards if c.balance > 0]

    if not working_cards:
        return PayoffResult(
            method="",
            method_description="",
            payoff_date=date.today(),
            months_to_payoff=0,
            total_interest=0,
            total_payments=0,
            monthly_payment_avg=0,
            payment_schedule=[],
            card_payoff_order=[]
        )

    schedule = []
    total_interest = 0
    total_payments = 0
    current_date = date.today().replace(day=1) + relativedelta(months=1)
    month_count = 0
    payoff_order = []

    while working_cards and month_count < max_months:
        month_count += 1

        # Apply interest to all cards
        for card in working_cards:
            interest = card.balance * card.monthly_interest_rate
            card.balance += interest
            total_interest += interest

        # Calculate total minimum payments required
        total_minimums = sum(
            calculate_minimum_payment(c.balance, c.apr, c.min_payment)
            for c in working_cards
        )

        # Available for extra payments
        extra_available = monthly_extra

        # Sort cards by priority
        prioritized = prioritize_func(working_cards)

        # Pay minimums on all cards first, then apply extra to priority card
        for card in working_cards:
            min_pay = calculate_minimum_payment(card.balance, card.apr, card.min_payment)
            payment = min(min_pay, card.balance)

            # Calculate interest portion
            interest_portion = min(card.balance * card.monthly_interest_rate, payment)
            principal_portion = payment - interest_portion

            card.balance -= payment
            total_payments += payment

            schedule.append(PaymentScheduleEntry(
                date=current_date,
                card_name=card.name,
                card_id=card.card_id,
                amount=payment,
                principal=principal_portion,
                interest=interest_portion,
                remaining_balance=max(0, card.balance)
            ))

        # Apply extra payment to highest priority card with balance
        if extra_available > 0 and prioritized:
            target = prioritized[0]
            if target.balance > 0:
                extra_payment = min(extra_available, target.balance)
                target.balance -= extra_payment
                total_payments += extra_payment

                # Add extra payment to schedule
                schedule.append(PaymentScheduleEntry(
                    date=current_date,
                    card_name=target.name,
                    card_id=target.card_id,
                    amount=extra_payment,
                    principal=extra_payment,
                    interest=0,
                    remaining_balance=max(0, target.balance)
                ))

        # Remove paid-off cards and record order
        for card in working_cards[:]:
            if card.balance <= 0.01:  # Consider paid off
                card.balance = 0
                if card.name not in payoff_order:
                    payoff_order.append(card.name)
                working_cards.remove(card)

        current_date += relativedelta(months=1)

    payoff_date = current_date - relativedelta(months=1) if month_count > 0 else date.today()

    return PayoffResult(
        method="",
        method_description="",
        payoff_date=payoff_date,
        months_to_payoff=month_count,
        total_interest=total_interest,
        total_payments=total_payments,
        monthly_payment_avg=total_payments / month_count if month_count > 0 else 0,
        payment_schedule=schedule,
        card_payoff_order=payoff_order
    )


def calculate_avalanche(cards: List[CardPayoffInfo], monthly_extra: float) -> PayoffResult:
    """
    Avalanche method: Pay highest APR first.
    Mathematically optimal - minimizes total interest paid.
    """
    def prioritize(card_list):
        return sorted(card_list, key=lambda c: c.apr, reverse=True)

    result = _simulate_payoff(cards, monthly_extra, prioritize)
    result.method = "Avalanche"
    result.method_description = "Highest interest rate first - minimizes total interest paid"
    return result


def calculate_snowball(cards: List[CardPayoffInfo], monthly_extra: float) -> PayoffResult:
    """
    Snowball method: Pay lowest balance first.
    Provides psychological wins by eliminating cards quickly.
    """
    def prioritize(card_list):
        return sorted(card_list, key=lambda c: c.balance)

    result = _simulate_payoff(cards, monthly_extra, prioritize)
    result.method = "Snowball"
    result.method_description = "Lowest balance first - quick wins for motivation"
    return result


def calculate_hybrid(cards: List[CardPayoffInfo], monthly_extra: float) -> PayoffResult:
    """
    Hybrid method: Weighted score of APR (60%) and balance (40%).
    Balances interest savings with psychological benefits.
    """
    def prioritize(card_list):
        if not card_list:
            return []

        # Normalize APR and balance to 0-1 scale
        max_apr = max(c.apr for c in card_list) or 1
        max_balance = max(c.balance for c in card_list) or 1

        def score(card):
            apr_score = card.apr / max_apr  # Higher APR = higher score
            balance_score = 1 - (card.balance / max_balance)  # Lower balance = higher score
            return 0.6 * apr_score + 0.4 * balance_score

        return sorted(card_list, key=score, reverse=True)

    result = _simulate_payoff(cards, monthly_extra, prioritize)
    result.method = "Hybrid"
    result.method_description = "60% APR + 40% balance weight - balanced approach"
    return result


def calculate_high_utilization(cards: List[CardPayoffInfo], monthly_extra: float) -> PayoffResult:
    """
    High Utilization method: Pay cards with highest utilization first.
    Good for improving credit score quickly.
    """
    def prioritize(card_list):
        return sorted(card_list, key=lambda c: c.utilization, reverse=True)

    result = _simulate_payoff(cards, monthly_extra, prioritize)
    result.method = "High Utilization"
    result.method_description = "Highest utilization first - improves credit score fastest"
    return result


def calculate_cash_on_hand(cards: List[CardPayoffInfo], monthly_extra: float) -> PayoffResult:
    """
    Cash on Hand method: Pay only minimums to maximize available cash.
    Use when cash flow is critical or building emergency fund.
    """
    # For this method, we don't apply any extra - just minimums
    def prioritize(card_list):
        return []  # No priority for extra payments

    result = _simulate_payoff(cards, 0, prioritize)  # Zero extra payment
    result.method = "Cash on Hand"
    result.method_description = "Minimum payments only - maximizes available cash"
    return result


def calculate_all_methods(
    cards: List[CardPayoffInfo],
    monthly_extra: float
) -> List[PayoffResult]:
    """
    Calculate payoff projections for all available methods.

    Args:
        cards: List of CardPayoffInfo objects
        monthly_extra: Extra monthly payment beyond minimums

    Returns:
        List of PayoffResult objects, sorted by total interest (lowest first)
    """
    results = [
        calculate_avalanche(cards, monthly_extra),
        calculate_snowball(cards, monthly_extra),
        calculate_hybrid(cards, monthly_extra),
        calculate_high_utilization(cards, monthly_extra),
        calculate_cash_on_hand(cards, monthly_extra),
    ]

    # Sort by total interest (best first)
    return sorted(results, key=lambda r: r.total_interest)


def get_cards_from_database() -> List[CardPayoffInfo]:
    """Load card information from the database"""
    from ..models.credit_card import CreditCard

    cards = []
    for card in CreditCard.get_all():
        if card.current_balance > 0:
            cards.append(CardPayoffInfo(
                card_id=card.id,
                name=card.name,
                balance=card.current_balance,
                apr=card.interest_rate,
                min_payment=card.min_payment,
                credit_limit=card.credit_limit
            ))

    return cards
