"""PDF Statement Parser for bank and credit card statements"""

import re
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class TransactionEntry:
    date: str  # YYYY-MM-DD
    description: str
    amount: float  # negative=charge, positive=payment/credit
    post_date: Optional[str] = None  # YYYY-MM-DD
    category: str = 'purchase'  # payment, purchase, fee, interest, deposit, withdrawal


@dataclass
class StatementData:
    statement_type: str = ''  # credit_card, checking, payslip
    institution: str = ''
    account_last4: str = ''
    statement_date: str = ''  # YYYY-MM-DD (closing date)
    period_start: str = ''  # YYYY-MM-DD
    period_end: str = ''  # YYYY-MM-DD
    previous_balance: float = 0.0
    new_balance: float = 0.0
    payments_total: float = 0.0
    purchases_total: float = 0.0
    fees_total: float = 0.0
    interest_total: float = 0.0
    credit_limit: float = 0.0
    minimum_payment: float = 0.0
    payment_due_date: str = ''  # YYYY-MM-DD
    transactions: List[TransactionEntry] = field(default_factory=list)
    # Payslip-specific
    gross_pay: float = 0.0
    net_pay: float = 0.0
    deductions: dict = field(default_factory=dict)
    pay_period_start: str = ''
    pay_period_end: str = ''


def _safe_float(text: str) -> float:
    """Parse a dollar amount string to float, handling commas and signs"""
    if not text:
        return 0.0
    text = text.strip().replace(',', '').replace('$', '')
    # Handle negative markers
    if text.endswith('-'):
        text = '-' + text[:-1]
    if text.startswith('(') and text.endswith(')'):
        text = '-' + text[1:-1]
    text = text.replace('+', '').strip()
    try:
        return float(text)
    except (ValueError, TypeError):
        return 0.0


def _parse_date(text: str, year: int = None) -> str:
    """Parse MM/DD or Mon DD to YYYY-MM-DD"""
    text = text.strip()
    if not year:
        year = datetime.now().year

    # Try MM/DD format
    m = re.match(r'(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?', text)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        if m.group(3):
            y = int(m.group(3))
            year = y if y > 100 else 2000 + y
        return f"{year:04d}-{month:02d}-{day:02d}"

    # Try Mon DD format (e.g. "Dec 25", "Jan 9")
    months = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    m = re.match(r'([A-Za-z]{3})\s+(\d{1,2})', text)
    if m:
        month = months.get(m.group(1).lower(), 0)
        day = int(m.group(2))
        if month:
            return f"{year:04d}-{month:02d}-{day:02d}"

    return ''


def _infer_year(month: int, period_end_str: str) -> int:
    """Infer transaction year from month and statement period end date"""
    if period_end_str:
        try:
            end = datetime.strptime(period_end_str, '%Y-%m-%d')
            # If transaction month is Dec but period ends in Jan, use previous year
            if month == 12 and end.month <= 2:
                return end.year - 1
            return end.year
        except ValueError:
            pass
    return datetime.now().year


def detect_format(text: str) -> str:
    """Detect statement format from first page text.

    Check institution-specific patterns first (most specific),
    then Chase last since 'JPMORGAN CHASE' appears in many statements
    as a payment reference.
    """
    t = text.lower() if text else ''

    # Chase checking has unique *start* markers
    if '*start*summary' in t or '*start*deposits' in t:
        return 'chase_checking'
    # Check specific institutions first (before Chase)
    if 'capital one' in t or 'capitalone.com' in t:
        return 'capital_one'
    if 'barclays' in t:
        return 'barclays'
    if 'wells fargo' in t or 'wellsfargo.com' in t:
        return 'wells_fargo'
    if 'merrick bank' in t or 'merrickbank' in t:
        return 'merrick'
    if 'comenity' in t or 'concora credit' in t:
        return 'comenity'
    if 'gross pay' in t and 'net pay' in t:
        return 'payslip'
    # Chase CC last - check for chase.com or Chase-specific branding
    # The doubled-char headers (e.g. "AACCCCOOUUNNTT") are unique to Chase CC
    if 'chase.com' in t or 'aaccccoouunntt' in t:
        return 'chase_cc'

    return 'unknown'


def parse_statement(file_path: str) -> StatementData:
    """Parse a PDF statement file and return structured data"""
    import pdfplumber

    pdf = pdfplumber.open(file_path)
    pages_text = []
    for page in pdf.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)
    pdf.close()

    if not pages_text:
        raise ValueError(f"Could not extract text from {file_path}")

    full_text = '\n'.join(pages_text)
    fmt = detect_format(pages_text[0])

    parsers = {
        'chase_checking': _parse_chase_checking,
        'chase_cc': _parse_chase_cc,
        'capital_one': _parse_capital_one,
        'barclays': _parse_barclays,
        'wells_fargo': _parse_wells_fargo,
        'merrick': _parse_merrick,
        'comenity': _parse_comenity,
        'payslip': _parse_payslip,
    }

    parser = parsers.get(fmt)
    if not parser:
        raise ValueError(f"Unknown statement format for {file_path}")

    return parser(full_text)


def _parse_chase_checking(text: str) -> StatementData:
    """Parse Chase Checking statement"""
    data = StatementData(statement_type='checking', institution='Chase')

    # Account number last 4
    m = re.search(r'(\d{15,16})\b', text)
    if m:
        data.account_last4 = m.group(1)[-4:]

    # Period: "December 13, 2025throughJanuary 15, 2026"
    m = re.search(
        r'(\w+ \d{1,2}, \d{4})\s*through\s*(\w+ \d{1,2}, \d{4})', text
    )
    if m:
        try:
            start = datetime.strptime(m.group(1), '%B %d, %Y')
            end = datetime.strptime(m.group(2), '%B %d, %Y')
            data.period_start = start.strftime('%Y-%m-%d')
            data.period_end = end.strftime('%Y-%m-%d')
            data.statement_date = data.period_end
        except ValueError:
            pass

    # Balances from summary section
    m = re.search(r'Beginning Balance\s+\$?([\d,]+\.\d{2})', text)
    if m:
        data.previous_balance = _safe_float(m.group(1))
    m = re.search(r'Ending Balance\s+\$?([\d,]+\.\d{2})', text)
    if m:
        data.new_balance = _safe_float(m.group(1))

    # Parse deposits section
    deposits_match = re.search(
        r'\*start\*deposits and additions(.*?)\*end\*deposits and additions',
        text, re.DOTALL
    )
    if deposits_match:
        _parse_chase_checking_section(
            deposits_match.group(1), data, 'deposit'
        )

    # Parse ATM/debit withdrawals
    atm_match = re.search(
        r'\*start\*atm debit withdrawal(.*?)\*end\*atm debit withdrawal',
        text, re.DOTALL
    )
    if atm_match:
        _parse_chase_checking_section(
            atm_match.group(1), data, 'withdrawal'
        )

    # Parse electronic withdrawals
    elec_match = re.search(
        r'\*start\*electronic withdrawal(.*?)\*end\*electronic withdrawal',
        text, re.DOTALL
    )
    if elec_match:
        _parse_chase_checking_section(
            elec_match.group(1), data, 'withdrawal'
        )

    # Calculate totals
    data.payments_total = sum(
        t.amount for t in data.transactions if t.amount > 0
    )
    data.purchases_total = sum(
        abs(t.amount) for t in data.transactions if t.amount < 0
    )

    return data


def _parse_chase_checking_section(
    section_text: str, data: StatementData, default_category: str
):
    """Parse a Chase checking transaction section"""
    year = None
    if data.period_end:
        year = int(data.period_end[:4])

    for line in section_text.strip().split('\n'):
        line = line.strip()
        # Match: MM/DD Description $Amount or MM/DD Description Amount
        m = re.match(
            r'(\d{2}/\d{2})\s+(.+?)\s+\$?([\d,]+\.\d{2})$', line
        )
        if m:
            date_str = m.group(1)
            desc = m.group(2).strip()
            amount = _safe_float(m.group(3))

            # Skip totals
            if desc.lower().startswith('total'):
                continue

            month = int(date_str.split('/')[0])
            tx_year = _infer_year(month, data.period_end) if year else year

            if default_category == 'withdrawal':
                amount = -amount

            data.transactions.append(TransactionEntry(
                date=_parse_date(date_str, tx_year),
                description=desc,
                amount=amount,
                category=default_category,
            ))


def _parse_chase_cc(text: str) -> StatementData:
    """Parse Chase Credit Card statement"""
    data = StatementData(statement_type='credit_card', institution='Chase')

    # Account last 4 - look for "XXXX XXXX XXXX 4830"
    m = re.search(r'XXXX\s+XXXX\s+XXXX\s+(\d{4})', text)
    if m:
        data.account_last4 = m.group(1)

    # Period: "Opening/Closing Date 12/26/25 - 01/25/26"
    m = re.search(r'Opening/Closing Date\s+(\d{2}/\d{2}/\d{2})\s*-\s*(\d{2}/\d{2}/\d{2})', text)
    if m:
        data.period_start = _parse_date(m.group(1))
        data.period_end = _parse_date(m.group(2))
        data.statement_date = data.period_end

    # Balances
    m = re.search(r'Previous Balance\s+\$?([\d,]+\.\d{2})', text)
    if m:
        data.previous_balance = _safe_float(m.group(1))
    m = re.search(r'New Balance\s+\$?([\d,]+\.\d{2})', text)
    if m:
        data.new_balance = _safe_float(m.group(1))

    # Credit limit
    m = re.search(r'Credit Access Line\s+\$?([\d,]+)', text)
    if m:
        data.credit_limit = _safe_float(m.group(1))

    # Minimum payment
    m = re.search(r'Minimum Payment Due\s*:?\s*\$?([\d,]+\.\d{2})', text)
    if m:
        data.minimum_payment = _safe_float(m.group(1))

    # Payment due date
    m = re.search(r'Payment Due Date\s*:?\s*(\d{2}/\d{2}/\d{2,4})', text)
    if m:
        data.payment_due_date = _parse_date(m.group(1))

    # Interest
    m = re.search(r'Interest Charged\s+\+?\$?([\d,]+\.\d{2})', text)
    if m:
        data.interest_total = _safe_float(m.group(1))

    # Parse ACCOUNT ACTIVITY section
    # The Chase CC text has doubled characters in headers but normal transaction text
    activity_match = re.search(
        r'ACCOUNT\s+ACTIVITY\s*\n(.*?)(?:INTEREST\s+CHARGES|2026\s+Totals|$)',
        text, re.DOTALL | re.IGNORECASE
    )
    # Also try with doubled chars
    if not activity_match:
        activity_match = re.search(
            r'AACCCCOOUUNNTT\s+AACCTTIIVVIITTYY\s*\n(.*?)(?:IINNTTEERREESSTT|INTEREST|2026\s+Totals|$)',
            text, re.DOTALL
        )

    if activity_match:
        section = activity_match.group(1)
        current_category = 'purchase'

        for line in section.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            # Category headers
            upper = line.upper()
            if 'PAYMENT' in upper and 'CREDIT' in upper:
                current_category = 'payment'
                continue
            if upper == 'PURCHASE' or upper.startswith('PURCHASE'):
                if not re.match(r'\d{2}/\d{2}', line):
                    current_category = 'purchase'
                    continue
            if 'INTEREST CHARGED' in upper and not re.match(r'\d{2}/\d{2}', line):
                current_category = 'interest'
                continue
            if 'TOTAL' in upper:
                continue

            # Transaction line: MM/DD Description Amount
            m = re.match(
                r'(\d{2}/\d{2})\s+(.+?)\s+(-?\$?[\d,]+\.\d{2})$', line
            )
            if m:
                date_str = m.group(1)
                desc = m.group(2).strip()
                amt_str = m.group(3).replace('$', '').replace(',', '')
                amount = float(amt_str)

                month = int(date_str.split('/')[0])
                tx_year = _infer_year(month, data.period_end)

                # Convention: payments positive (credit), purchases/fees/interest negative (expense)
                if current_category == 'payment':
                    # Chase CC shows payments with -, e.g. "-622.00"
                    amount = abs(amount)
                elif current_category in ('purchase', 'interest'):
                    amount = -abs(amount)

                data.transactions.append(TransactionEntry(
                    date=_parse_date(date_str, tx_year),
                    description=desc,
                    amount=amount,
                    category=current_category,
                ))

    data.payments_total = sum(
        t.amount for t in data.transactions if t.category == 'payment'
    )
    data.purchases_total = sum(
        abs(t.amount) for t in data.transactions if t.category == 'purchase'
    )
    data.fees_total = sum(
        abs(t.amount) for t in data.transactions if t.category == 'fee'
    )

    return data


def _parse_capital_one(text: str) -> StatementData:
    """Parse Capital One credit card statement"""
    data = StatementData(statement_type='credit_card', institution='Capital One')

    # Account last 4 - "ending in 8138" or "ending in 4163"
    m = re.search(r'ending in (\d{4})', text)
    if m:
        data.account_last4 = m.group(1)

    # Period: "Dec 26, 2025 - Jan 25, 2026"
    m = re.search(
        r'([A-Z][a-z]{2} \d{1,2}, \d{4})\s*-\s*([A-Z][a-z]{2} \d{1,2}, \d{4})',
        text
    )
    if m:
        try:
            start = datetime.strptime(m.group(1), '%b %d, %Y')
            end = datetime.strptime(m.group(2), '%b %d, %Y')
            data.period_start = start.strftime('%Y-%m-%d')
            data.period_end = end.strftime('%Y-%m-%d')
            data.statement_date = data.period_end
        except ValueError:
            pass

    # Balances
    m = re.search(r'Previous Balance\s+\$?([\d,]+\.\d{2})', text)
    if m:
        data.previous_balance = _safe_float(m.group(1))
    # New Balance after = sign
    m = re.search(r'New Balance\s*=?\s*\$?([\d,]+\.\d{2})', text)
    if m:
        data.new_balance = _safe_float(m.group(1))

    # Credit Limit
    m = re.search(r'Credit Limit\s+\$?([\d,]+\.\d{2})', text)
    if m:
        data.credit_limit = _safe_float(m.group(1))

    # Minimum Payment - on the payment coupon line: "New Balance  Minimum Payment Due  Amount Enclosed"
    # followed by values line: "$7,166.35  $225.00  $___"
    # Use the coupon area which has the values on a separate line
    m = re.search(
        r'New Balance\s+Minimum Payment Due\s+Amount Enclosed.*?\n'
        r'\$?([\d,]+\.\d{2})\s+\$?([\d,]+\.\d{2})',
        text, re.DOTALL
    )
    if m:
        data.minimum_payment = _safe_float(m.group(2))
    else:
        # Fallback: look for "Minimum Payment Due" near smaller numbers
        m = re.search(r'Minimum Payment\s+\d+ Years\s+\$[\d,]+\n\$?([\d,]+)', text)
        if m:
            data.minimum_payment = _safe_float(m.group(1))

    # Payment due date
    m = re.search(r'Payment Due Date.*?([A-Z][a-z]{2} \d{1,2}, \d{4})', text)
    if m:
        try:
            dt = datetime.strptime(m.group(1), '%b %d, %Y')
            data.payment_due_date = dt.strftime('%Y-%m-%d')
        except ValueError:
            pass

    # Interest
    m = re.search(r'Interest Charged\s+\+?\s*\$?([\d,]+\.\d{2})', text)
    if m:
        data.interest_total = _safe_float(m.group(1))

    # Fees
    m = re.search(r'Fees Charged\s+\+?\s*\$?([\d,]+\.\d{2})', text)
    if m:
        data.fees_total = _safe_float(m.group(1))

    # Parse transactions
    # Capital One format: "Trans Date  Post Date  Description  Amount"
    # Sections: "Payments, Credits and Adjustments" and "Transactions"
    current_category = 'purchase'

    # Find all transaction lines across full text
    for line in text.split('\n'):
        line = line.strip()

        # Detect section headers
        if 'Payments, Credits and Adjustments' in line:
            current_category = 'payment'
            continue
        if re.search(r'#\d{4}: Transactions$', line):
            current_category = 'purchase'
            continue
        if line.startswith('Fees') and 'Trans Date' not in line:
            current_category = 'fee'
            continue
        if 'Interest Charge' in line and 'Calculation' not in line:
            # Interest summary lines
            if re.match(r'Interest Charge on', line):
                continue
        if 'Total' in line:
            continue
        if line.startswith('Trans Date'):
            continue

        # Transaction line: "Mon DD  Mon DD  Description  Amount"
        # e.g. "Dec 25 Dec 26 CAPITAL ONE MOBILE PYMT - $300.00"
        m = re.match(
            r'([A-Z][a-z]{2} \d{1,2})\s+([A-Z][a-z]{2} \d{1,2})\s+(.+?)\s+'
            r'(-?\s*\$?\s*[\d,]+\.\d{2})$',
            line
        )
        if m:
            trans_date_str = m.group(1)
            post_date_str = m.group(2)
            desc = m.group(3).strip()
            amt_str = m.group(4).replace('$', '').replace(',', '').replace(' ', '')
            amount = float(amt_str)

            # Infer year
            trans_month_str = trans_date_str[:3].lower()
            months = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            trans_month = months.get(trans_month_str, 1)
            tx_year = _infer_year(trans_month, data.period_end)
            post_month = months.get(post_date_str[:3].lower(), 1)
            post_year = _infer_year(post_month, data.period_end)

            trans_date = _parse_date(trans_date_str, tx_year)
            post_date = _parse_date(post_date_str, post_year)

            # Convention: payments positive (credit), purchases/fees negative (expense)
            if current_category == 'payment':
                amount = abs(amount)  # Payments are credits
            elif current_category in ('purchase', 'fee'):
                amount = -abs(amount)  # Purchases/fees are expenses

            data.transactions.append(TransactionEntry(
                date=trans_date,
                description=desc,
                amount=amount,
                post_date=post_date,
                category=current_category,
            ))

    # Fee transactions from the Fees section
    for line in text.split('\n'):
        line = line.strip()
        m = re.match(
            r'([A-Z][a-z]{2} \d{1,2})\s+([A-Z][a-z]{2} \d{1,2})\s+(PAST DUE FEE|LATE FEE|ANNUAL FEE.*?)\s+'
            r'\$?([\d,]+\.\d{2})$',
            line
        )
        if m:
            trans_date_str = m.group(1)
            post_date_str = m.group(2)
            desc = m.group(3).strip()
            amount = -_safe_float(m.group(4))

            months = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            trans_month = months.get(trans_date_str[:3].lower(), 1)
            tx_year = _infer_year(trans_month, data.period_end)
            post_month = months.get(post_date_str[:3].lower(), 1)
            post_year = _infer_year(post_month, data.period_end)

            # Check for duplicates
            trans_date = _parse_date(trans_date_str, tx_year)
            already_exists = any(
                t.date == trans_date and t.description == desc
                for t in data.transactions
            )
            if not already_exists:
                data.transactions.append(TransactionEntry(
                    date=trans_date,
                    description=desc,
                    amount=amount,
                    post_date=_parse_date(post_date_str, post_year),
                    category='fee',
                ))

    data.payments_total = sum(
        t.amount for t in data.transactions if t.category == 'payment'
    )
    data.purchases_total = sum(
        abs(t.amount) for t in data.transactions if t.category == 'purchase'
    )

    return data


def _parse_barclays(text: str) -> StatementData:
    """Parse Barclays credit card statement"""
    data = StatementData(statement_type='credit_card', institution='Barclays')

    # Account last 4 - "Account Ending8703"
    m = re.search(r'Account Ending\s*(\d{4})', text)
    if m:
        data.account_last4 = m.group(1)

    # Period: "Statement Period 12/25/25 - 01/24/26"
    m = re.search(
        r'Statement Period\s+(\d{2}/\d{2}/\d{2})\s*-\s*(\d{2}/\d{2}/\d{2})',
        text
    )
    if m:
        data.period_start = _parse_date(m.group(1))
        data.period_end = _parse_date(m.group(2))
        data.statement_date = data.period_end

    # Balances
    m = re.search(r'Previous Balance.*?\$?([\d,]+\.\d{2})', text)
    if m:
        data.previous_balance = _safe_float(m.group(1))
    m = re.search(r'Statement Balance.*?\$?([\d,]+\.\d{2})', text)
    if m:
        data.new_balance = _safe_float(m.group(1))

    # Credit Line
    m = re.search(r'Total Credit Line\s+\$?([\d,]+\.\d{2})', text)
    if m:
        data.credit_limit = _safe_float(m.group(1))

    # Minimum Payment
    m = re.search(r'Minimum Payment Due\s*:?\s*\$?([\d,]+\.\d{2})', text)
    if m:
        data.minimum_payment = _safe_float(m.group(1))

    # Payment due date
    m = re.search(r'Payment Due Date\s*:?\s*(\d{2}/\d{2}/\d{2,4})', text)
    if m:
        data.payment_due_date = _parse_date(m.group(1))

    # Interest / fees
    m = re.search(r'Interest Charged\s+\+?\s*\$?([\d,]+\.\d{2})', text)
    if m:
        data.interest_total = _safe_float(m.group(1))
    m = re.search(r'Fees Charged\s+\+?\s*\$?([\d,]+\.\d{2})', text)
    if m:
        data.fees_total = _safe_float(m.group(1))

    # Parse transactions section
    # Barclays format: "Transaction Date  Posting Date  Description  Points  Amount"
    current_category = 'purchase'

    for line in text.split('\n'):
        line = line.strip()

        if line.startswith('Payments'):
            current_category = 'payment'
            continue
        if 'Purchase Activity' in line:
            current_category = 'purchase'
            continue
        if line.startswith('Fees Charged') or line.startswith('No fees'):
            current_category = 'fee'
            continue
        if line.startswith('Interest Charged') or line.startswith('No interest'):
            current_category = 'interest'
            continue
        if 'Total' in line or line.startswith('Transaction Date'):
            continue

        # Transaction line: "Mon DD  Mon DD  Description  Points  Amount"
        # Payment: "Jan 21 Jan 21 Payment Received JPMORGAN CHAS N/A -$1,013.93"
        # Purchase: "Jan 09 Jan 09 CLUB WYNDHAM PLUS 888-739-4022 NV 462 $231.00"
        m = re.match(
            r'([A-Z][a-z]{2} \d{1,2})\s+([A-Z][a-z]{2} \d{1,2})\s+'
            r'(.+?)\s+(?:N/A|[\d,]+)\s+'
            r'(-?\$?[\d,]+\.\d{2})$',
            line
        )
        if m:
            trans_date_str = m.group(1)
            post_date_str = m.group(2)
            desc = m.group(3).strip()
            amt_str = m.group(4).replace('$', '').replace(',', '')
            amount = float(amt_str)

            months = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            trans_month = months.get(trans_date_str[:3].lower(), 1)
            tx_year = _infer_year(trans_month, data.period_end)
            post_month = months.get(post_date_str[:3].lower(), 1)
            post_year = _infer_year(post_month, data.period_end)

            # Convention: payments positive, purchases negative
            if current_category == 'payment':
                amount = abs(amount)
            elif current_category == 'purchase':
                amount = -abs(amount)

            data.transactions.append(TransactionEntry(
                date=_parse_date(trans_date_str, tx_year),
                description=desc,
                amount=amount,
                post_date=_parse_date(post_date_str, post_year),
                category=current_category,
            ))

    data.payments_total = sum(
        t.amount for t in data.transactions if t.category == 'payment'
    )
    data.purchases_total = sum(
        abs(t.amount) for t in data.transactions if t.category == 'purchase'
    )

    return data


def _parse_wells_fargo(text: str) -> StatementData:
    """Parse Wells Fargo credit card statement"""
    data = StatementData(statement_type='credit_card', institution='Wells Fargo')

    # Account last 4 - from "Account Number 5774 4225 4269 9359"
    m = re.search(r'Account Number\s+([\d ]+)', text)
    if m:
        digits = m.group(1).replace(' ', '')
        data.account_last4 = digits[-4:]

    # Period: "Billing Cycle 12/20/2025 to 01/19/2026"
    m = re.search(
        r'Billing Cycle\s+(\d{2}/\d{2}/\d{4})\s+to\s+(\d{2}/\d{2}/\d{4})',
        text
    )
    if m:
        data.period_start = _parse_date(m.group(1))
        data.period_end = _parse_date(m.group(2))
        data.statement_date = data.period_end

    # Balances
    m = re.search(r'Previous Balance\s+\$\s*([\d,]+\.\d{2})', text)
    if m:
        data.previous_balance = _safe_float(m.group(1))
    # New Balance - appears multiple times, get from Summary section
    m = re.search(r'New Balance\s+\$\s*([\d,]+\.\d{2})', text)
    if m:
        data.new_balance = _safe_float(m.group(1))

    # Credit Limit
    m = re.search(r'Credit Limit\s+\$\s*([\d,]+\.\d{2})', text)
    if m:
        data.credit_limit = _safe_float(m.group(1))

    # Minimum payment
    m = re.search(r'Minimum Payment Due\s+\$\s*([\d,]+\.\d{2})', text)
    if m:
        data.minimum_payment = _safe_float(m.group(1))

    # Payment due date
    m = re.search(r'Payment Due Date\s+(\d{2}/\d{2}/\d{4})', text)
    if m:
        data.payment_due_date = _parse_date(m.group(1))

    # Transactions section
    # Format: "RefNumber  TransDate  PostDate  Description  Amount"
    # e.g. "990000069 P938800QX0XSL7694 01/13 01/13 ONLINE ACH PAYMENT THANK YOU $223.00-"
    for line in text.split('\n'):
        line = line.strip()
        if 'TOTAL' in line.upper() or not line:
            continue

        # Match transaction lines with ref number prefix
        m = re.match(
            r'[\d\w]+ [\w\d]+ (\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+'
            r'\$?([\d,]+\.\d{2})(-?)$',
            line
        )
        if not m:
            # Try without the double ref number
            m = re.match(
                r'(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+'
                r'\$?([\d,]+\.\d{2})(-?)$',
                line
            )
        if m:
            trans_date_str = m.group(1)
            post_date_str = m.group(2)
            desc = m.group(3).strip()
            amount = _safe_float(m.group(4))

            # Skip $0 interest/fee lines
            if amount == 0:
                continue

            if m.group(5) == '-':
                # Trailing minus means credit/payment
                category = 'payment'
                amount = abs(amount)  # Payment is positive
            else:
                category = 'purchase'
                amount = -abs(amount)  # Purchase is expense

            month = int(trans_date_str.split('/')[0])
            tx_year = _infer_year(month, data.period_end)
            post_month = int(post_date_str.split('/')[0])
            post_year = _infer_year(post_month, data.period_end)

            data.transactions.append(TransactionEntry(
                date=_parse_date(trans_date_str, tx_year),
                description=desc,
                amount=amount,
                post_date=_parse_date(post_date_str, post_year),
                category=category,
            ))

    # Interest from separate section
    m = re.search(r'INTEREST CHARGE ON PURCHASES\s+\$?([\d,]+\.\d{2})', text, re.IGNORECASE)
    if m:
        data.interest_total = _safe_float(m.group(1))

    data.payments_total = sum(
        t.amount for t in data.transactions if t.category == 'payment'
    )
    data.purchases_total = sum(
        abs(t.amount) for t in data.transactions if t.category == 'purchase'
    )

    return data


def _parse_merrick(text: str) -> StatementData:
    """Parse Merrick Bank credit card statement"""
    data = StatementData(statement_type='credit_card', institution='Merrick Bank')

    # Account last 4
    m = re.search(r'Account Number\s+([\d ]+)', text)
    if m:
        digits = m.group(1).replace(' ', '')
        data.account_last4 = digits[-4:]
    if not data.account_last4:
        m = re.search(r'(\d{4}\s+\d{4}\s+\d{4}\s+\d{4})', text)
        if m:
            data.account_last4 = m.group(1).replace(' ', '')[-4:]

    # Statement date
    m = re.search(r'Statement Date\s*:\s*(\d{2}/\d{2}/\d{2})', text)
    if m:
        data.statement_date = _parse_date(m.group(1))
        data.period_end = data.statement_date

    # Billing cycle closing date
    m = re.search(r'Billing Cycle Closing Date\s+(\d{2}/\d{2}/\d{2})', text)
    if m:
        data.period_end = _parse_date(m.group(1))
        data.statement_date = data.period_end

    # Balances
    m = re.search(r'Previous Balance\s+\$?([\d,]+\.\d{2})', text)
    if m:
        data.previous_balance = _safe_float(m.group(1))
    m = re.search(r'New Balance\s+\$?([\d,]+\.\d{2})', text)
    if m:
        data.new_balance = _safe_float(m.group(1))

    # Credit Limit
    m = re.search(r'Credit Limit\s+\$?([\d,]+\.\d{2})', text)
    if m:
        data.credit_limit = _safe_float(m.group(1))

    # Minimum Payment
    m = re.search(r'Minimum.*?Due\s+\$?([\d,]+\.\d{2})', text)
    if m:
        data.minimum_payment = _safe_float(m.group(1))

    # Payment due date
    m = re.search(r'Payment Due Date\s+(\d{2}/\d{2}/\d{2,4})', text)
    if m:
        data.payment_due_date = _parse_date(m.group(1))

    # Interest
    m = re.search(r'TOTAL INTEREST FOR THIS PERIOD\s+\$?([\d,]+\.\d{2})', text)
    if m:
        data.interest_total = _safe_float(m.group(1))
    # Fees
    m = re.search(r'TOTAL FEES FOR THIS PERIOD\s+\$?([\d,]+\.\d{2})', text)
    if m:
        data.fees_total = _safe_float(m.group(1))

    # Parse transactions
    # Merrick format: "Trans Date  RefID  Description  Amount"
    # e.g. "01/16 8542539D000XTMJGS ONLINE RECURRING PAYMENT 293.52 -"
    in_transactions = False
    in_fees = False

    for line in text.split('\n'):
        line = line.strip()

        if line.startswith('Transactions, Payments and Credits'):
            in_transactions = True
            in_fees = False
            continue
        if line.startswith('Fees'):
            in_transactions = False
            in_fees = True
            continue
        if line.startswith('Interest Charged'):
            in_fees = False
            in_transactions = False
            continue
        if 'TOTAL' in line.upper():
            continue

        if in_transactions or in_fees:
            # Match: MM/DD RefID Description Amount[-]
            m = re.match(
                r'(\d{2}/\d{2})\s+\S+\s+(.+?)\s+([\d,]+\.\d{2})\s*(-?)$',
                line
            )
            if m:
                date_str = m.group(1)
                desc = m.group(2).strip()
                amount = _safe_float(m.group(3))
                is_credit = m.group(4) == '-'

                month = int(date_str.split('/')[0])
                tx_year = _infer_year(month, data.period_end)

                if in_fees:
                    amount = -amount  # Fees are expenses
                    category = 'fee'
                elif is_credit:
                    amount = amount  # Payments/credits are positive
                    category = 'payment'
                else:
                    amount = -amount  # Purchases are expenses
                    category = 'purchase'

                data.transactions.append(TransactionEntry(
                    date=_parse_date(date_str, tx_year),
                    description=desc,
                    amount=amount,
                    category=category,
                ))

    data.payments_total = sum(
        t.amount for t in data.transactions if t.category == 'payment'
    )
    data.purchases_total = sum(
        abs(t.amount) for t in data.transactions if t.category == 'purchase'
    )

    return data


def _parse_comenity(text: str) -> StatementData:
    """Parse Comenity/Concora credit card statement"""
    data = StatementData(statement_type='credit_card', institution='Comenity')

    # Account last 4
    m = re.search(r'(?:ending in|Account number ending in)\s+(\d{4})', text)
    if m:
        data.account_last4 = m.group(1)
    if not data.account_last4:
        m = re.search(r'\*{4}-\*{4}-\*{4}-(\d{4})', text)
        if m:
            data.account_last4 = m.group(1)

    # Statement closing date
    m = re.search(r'Statement Closing Date\s+(\w+ \d{1,2}, \d{4})', text)
    if m:
        try:
            dt = datetime.strptime(m.group(1), '%B %d, %Y')
            data.statement_date = dt.strftime('%Y-%m-%d')
            data.period_end = data.statement_date
        except ValueError:
            pass
    if not data.statement_date:
        m = re.search(r'Statement [Cc]losing [Dd]ate\s+(\w+ \d{1,2}, \d{4})', text)
        if m:
            try:
                dt = datetime.strptime(m.group(1), '%B %d, %Y')
                data.statement_date = dt.strftime('%Y-%m-%d')
                data.period_end = data.statement_date
            except ValueError:
                pass

    # Balances
    m = re.search(r'Previous [Bb]alance\s+\+?\$?([\d,]+\.\d{2})', text)
    if m:
        data.previous_balance = _safe_float(m.group(1))
    m = re.search(r'New [Bb]alance\s+\+?\$?([\d,]+\.\d{2})', text)
    if m:
        data.new_balance = _safe_float(m.group(1))

    # Credit Limit
    m = re.search(r'Credit [Ll]imit\s+\$?([\d,]+\.\d{2})', text)
    if m:
        data.credit_limit = _safe_float(m.group(1))

    # Minimum payment
    m = re.search(r'Minimum [Pp]ayment [Dd]ue\s+\$?([\d,]+\.\d{2})', text)
    if m:
        data.minimum_payment = _safe_float(m.group(1))

    # Payment due date
    m = re.search(r'Payment [Dd]ue [Dd]ate\s+(\w+ \d{1,2}, \d{4})', text)
    if m:
        try:
            dt = datetime.strptime(m.group(1), '%B %d, %Y')
            data.payment_due_date = dt.strftime('%Y-%m-%d')
        except ValueError:
            pass
    if not data.payment_due_date:
        m = re.search(r'Payment [Dd]ue [Dd]ate\s+(\d{2}/\d{2}/\d{4})', text)
        if m:
            data.payment_due_date = _parse_date(m.group(1))

    # Interest / fees totals
    m = re.search(r'TOTAL INTEREST FOR THIS PERIOD\s+\$?([\d,]+\.\d{2})', text)
    if not m:
        m = re.search(r'Total Interest For This Period\s+\$?([\d,]+\.\d{2})', text)
    if m:
        data.interest_total = _safe_float(m.group(1))

    m = re.search(r'TOTAL FEES FOR THIS PERIOD\s+\$?([\d,]+\.\d{2})', text)
    if m:
        data.fees_total = _safe_float(m.group(1))

    # Parse transactions
    # Comenity has two formats:
    # Format A (Milestone/Concora): "MM/DD  MM/DD  RefNumber  Description  Amount"
    # Format B (Zales): "MM/DD/YYYY  Description  Amount"
    in_transactions = False
    in_fees = False

    for line in text.split('\n'):
        line = line.strip()

        if line == 'TRANSACTIONS' or line.startswith('Details of your transactions'):
            in_transactions = True
            in_fees = False
            continue
        if line.startswith('FEES') or line.startswith('Fees'):
            in_transactions = False
            in_fees = True
            continue
        if 'INTEREST CHARGED' in line.upper() or 'Interest charged' in line:
            in_fees = False
            in_transactions = False
            continue
        if 'TOTAL' in line.upper() and ('FEES' in line.upper() or 'INTEREST' in line.upper()):
            continue
        if line.startswith('Tran') or line.startswith('TRANS DATE'):
            continue

        if in_transactions or in_fees:
            # Format A: MM/DD MM/DD RefNumber Description Amount[-]
            m = re.match(
                r'(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+\S+\s+(.+?)\s+'
                r'([\d,]+\.\d{2})\s*(-?)$',
                line
            )
            if m:
                trans_date_str = m.group(1)
                post_date_str = m.group(2)
                desc = m.group(3).strip()
                amount = _safe_float(m.group(4))
                is_credit = m.group(5) == '-'

                month = int(trans_date_str.split('/')[0])
                tx_year = _infer_year(month, data.period_end)
                post_month = int(post_date_str.split('/')[0])
                post_year = _infer_year(post_month, data.period_end)

                if in_fees:
                    amount = -amount
                    category = 'fee'
                elif is_credit or 'PAYMENT' in desc.upper():
                    category = 'payment'
                else:
                    amount = -amount
                    category = 'purchase'

                data.transactions.append(TransactionEntry(
                    date=_parse_date(trans_date_str, tx_year),
                    description=desc,
                    amount=amount,
                    post_date=_parse_date(post_date_str, post_year),
                    category=category,
                ))
                continue

            # Format B (Zales): MM/DD/YYYY  Description  -Amount or Amount
            m = re.match(
                r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?[\d,]+\.\d{2})$',
                line
            )
            if m:
                date_str = m.group(1)
                desc = m.group(2).strip()
                amount = _safe_float(m.group(3))

                if in_fees:
                    category = 'fee'
                    if amount > 0:
                        amount = -amount
                elif amount < 0 or 'PAYMENT' in desc.upper():
                    category = 'payment'
                    amount = abs(amount)  # Payments as positive
                else:
                    category = 'purchase'
                    amount = -amount

                data.transactions.append(TransactionEntry(
                    date=_parse_date(date_str),
                    description=desc,
                    amount=amount,
                    category=category,
                ))
                continue

            # Fees section: MM/DD MM/DD Description Amount
            if in_fees:
                m = re.match(
                    r'(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+'
                    r'([\d,]+\.\d{2})$',
                    line
                )
                if m:
                    trans_date_str = m.group(1)
                    desc = m.group(3).strip()
                    amount = -_safe_float(m.group(4))

                    month = int(trans_date_str.split('/')[0])
                    tx_year = _infer_year(month, data.period_end)

                    data.transactions.append(TransactionEntry(
                        date=_parse_date(trans_date_str, tx_year),
                        description=desc,
                        amount=amount,
                        category='fee',
                    ))
                    continue

            # Fees section (Zales): MM/DD/YYYY Description Amount
            if in_fees:
                m = re.match(
                    r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})$',
                    line
                )
                if m:
                    date_str = m.group(1)
                    desc = m.group(2).strip()
                    amount = -_safe_float(m.group(3))

                    data.transactions.append(TransactionEntry(
                        date=_parse_date(date_str),
                        description=desc,
                        amount=amount,
                        category='fee',
                    ))

    data.payments_total = sum(
        t.amount for t in data.transactions if t.category == 'payment'
    )
    data.purchases_total = sum(
        abs(t.amount) for t in data.transactions if t.category == 'purchase'
    )

    return data


def _parse_payslip(text: str) -> StatementData:
    """Parse payslip/paystub"""
    data = StatementData(statement_type='payslip', institution='Elevance Health')

    # Gross pay and net pay from "Current" row
    m = re.search(
        r'Current\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)',
        text
    )
    if m:
        data.gross_pay = _safe_float(m.group(2))
        data.net_pay = _safe_float(m.group(6))

    # Pay period
    m = re.search(r'Pay Period Begin\s+Pay Period End\s+Check Date', text)
    # Look for the date line after name/company
    m = re.search(
        r'(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})',
        text
    )
    if m:
        data.pay_period_start = _parse_date(m.group(1))
        data.pay_period_end = _parse_date(m.group(2))
        data.statement_date = _parse_date(m.group(3))

    # Deductions
    deductions = {}

    # Pre-tax deductions
    pretax_match = re.search(
        r'Pre Tax Deductions\s*\n(.*?)Pre Tax Deductions\s+[\d,]+\.\d{2}',
        text, re.DOTALL
    )
    if pretax_match:
        for line in pretax_match.group(1).strip().split('\n'):
            m = re.match(r'(\w[\w\s]+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})', line)
            if m:
                deductions[m.group(1).strip()] = _safe_float(m.group(2))

    # Post-tax deductions
    posttax_match = re.search(
        r'Post Tax Deductions\s*\n(.*?)Post Tax Deductions\s+[\d,]+\.\d{2}',
        text, re.DOTALL
    )
    if posttax_match:
        for line in posttax_match.group(1).strip().split('\n'):
            m = re.match(r'(\w[\w\s()]+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})', line)
            if m:
                deductions[m.group(1).strip()] = _safe_float(m.group(2))

    # Taxes
    taxes = {}
    tax_match = re.search(
        r'Associate Taxes\s*\n(.*?)Associate Taxes\s+[\d,]+\.\d{2}',
        text, re.DOTALL
    )
    if tax_match:
        for line in tax_match.group(1).strip().split('\n'):
            m = re.match(r'(\w[\w\s]+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})', line)
            if m:
                taxes[m.group(1).strip()] = _safe_float(m.group(2))

    data.deductions = {**deductions, **taxes}

    # Net pay deposits as transactions
    # The payslip has doubled text: "JPMORGAN CHASE JPMORGAN CHASE ******0117 ******0117 1,280.94 USD"
    payment_section = re.search(
        r'Payment Information\s*\n(.*?)$', text, re.DOTALL
    )
    if payment_section:
        for m in re.finditer(
            r'\*{6}(\d{4})\s+\*{6}\d{4}\s+([\d,]+\.\d{2})\s+USD',
            payment_section.group(1)
        ):
            last4 = m.group(1)
            amount = _safe_float(m.group(2))
            # Extract bank name from before the asterisks
            prefix = payment_section.group(1)[:m.start()].strip().split('\n')[-1].strip()
            # Remove header line artifacts and deduplicate
            bank_name = prefix if prefix else f"Account ***{last4}"
            # The bank name is doubled (e.g., "JPMORGAN CHASE JPMORGAN CHASE")
            # Try to deduplicate
            words = bank_name.split()
            half = len(words) // 2
            if half > 0 and words[:half] == words[half:]:
                bank_name = ' '.join(words[:half])
            data.transactions.append(TransactionEntry(
                date=data.statement_date,
                description=f"Direct Deposit - {bank_name} (***{last4})",
                amount=amount,
                category='deposit',
            ))

    data.new_balance = data.net_pay
    data.previous_balance = 0.0

    return data


def match_account(statement: StatementData, cards, accounts) -> Optional[str]:
    """Match a parsed statement to a card/account pay_type_code.

    Args:
        statement: Parsed statement data
        cards: List of CreditCard objects
        accounts: List of Account objects

    Returns:
        pay_type_code string or None
    """
    last4 = statement.account_last4

    # Try matching by last 4 digits
    if last4:
        for card in cards:
            if card.pay_type_code and last4 in (card.pay_type_code, ''):
                # Direct code match unlikely, check other identifiers
                pass

        # Match checking account by last4
        for acct in accounts:
            if acct.pay_type_code and last4:
                # The Chase checking account deposits to ******0117
                # We need to match this somehow
                pass

    # Match by institution + balance/limit
    if statement.statement_type == 'checking':
        for acct in accounts:
            if acct.account_type == 'CHECKING':
                return acct.pay_type_code

    if statement.statement_type == 'credit_card':
        # Try matching by credit limit (most unique identifier)
        for card in cards:
            if (statement.credit_limit > 0 and
                    abs(card.credit_limit - statement.credit_limit) < 1.0):
                return card.pay_type_code

        # Try matching by institution + approximate balance
        for card in cards:
            if (statement.new_balance > 0 and
                    abs(card.current_balance - statement.new_balance) < 50.0):
                return card.pay_type_code

    if statement.statement_type == 'payslip':
        # Payslip deposits go to checking
        for acct in accounts:
            if acct.account_type == 'CHECKING':
                return acct.pay_type_code

    return None
