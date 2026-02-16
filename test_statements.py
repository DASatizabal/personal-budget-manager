"""Test script to parse all Statement Files and display results"""
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

from budget_app.utils.statement_parser import parse_statement, match_account
from budget_app.models.credit_card import CreditCard
from budget_app.models.account import Account

cards = CreditCard.get_all()
accounts = Account.get_all()

print('=' * 100)
print('PDF STATEMENT PARSER TEST - All Files in Statement Files/')
print('=' * 100)

total_txns = 0

for f in sorted(os.listdir('Statement Files')):
    if not f.endswith('.pdf'):
        continue
    print()
    print(f'--- {f} ---')
    try:
        result = parse_statement(f'Statement Files/{f}')
        code = match_account(result, cards, accounts)

        print(f'  Institution: {result.institution} | Type: {result.statement_type} | Last4: {result.account_last4}')
        print(f'  Period: {result.period_start or "?"} to {result.period_end or "?"}')
        print(f'  Prev Balance: ${result.previous_balance:,.2f} | New Balance: ${result.new_balance:,.2f}')
        if result.credit_limit:
            print(f'  Credit Limit: ${result.credit_limit:,.2f} | Min Payment: ${result.minimum_payment:,.2f} | Due: {result.payment_due_date}')
        if result.interest_total or result.fees_total:
            print(f'  Interest: ${result.interest_total:,.2f} | Fees: ${result.fees_total:,.2f}')
        if result.statement_type == 'payslip':
            print(f'  Gross Pay: ${result.gross_pay:,.2f} | Net Pay: ${result.net_pay:,.2f}')
            print(f'  Pay Period: {result.pay_period_start} to {result.pay_period_end} | Check Date: {result.statement_date}')

        print(f'  Auto-match: {code or "NO MATCH"}')
        print(f'  Transactions ({len(result.transactions)}):')
        total_txns += len(result.transactions)
        for t in result.transactions:
            sign = '+' if t.amount >= 0 else ''
            post = f' (posted {t.post_date})' if t.post_date else ''
            print(f'    {t.date} | {sign}${t.amount:,.2f} | {t.category:10s} | {t.description}{post}')

    except Exception as e:
        print(f'  ERROR: {e}')
        import traceback
        traceback.print_exc()

print()
print('=' * 100)
print(f'TEST COMPLETE - 10 statements parsed, {total_txns} total transactions extracted')
print('=' * 100)
