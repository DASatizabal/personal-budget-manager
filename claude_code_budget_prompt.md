# Claude Code Prompt: Personal Budget Management System

## Project Overview

Build a comprehensive personal budget management application that replaces my current Excel-based financial tracking system. The application should be a standalone desktop or web application (not Excel-based) that automates financial tracking, forecasting, and analysis.

---

## Current System Structure (Reference)

My Excel workbook has the following sheets that the application should replicate:

### 1. Summary (Dashboard & Transaction Ledger)

**Dashboard Section (Rows 1-17):**
- **Current Balances:**
  - Bank account balance (Chase - manually entered/adjusted)
  - Savings account balance
  - Miscellaneous cash/change
  - Total owed amount

- **Credit Card Summary Table:**
  - Pulls data from Credit Card Info: Pay Type code, Card Name, Available Credit, Current Balance, Credit Line, % Usage
  - Cards tracked: BJs, Quicksilver, Disney, CapOne, Merrick, Milestone, Destiny, Dell, The Home Depot, Zales, Wyndham Card
  - Also includes 401k Loans (Loan 1, Loan 2)

- **90-Day Minimum Balance Alert:**
  - Calculates the minimum Chase balance that will occur in the next 90 days
  - Shows the date when this minimum will occur
  - Uses MINIFS to find lowest projected balance for Chase account transactions

**Transaction Ledger (Row 20+):**
Each row represents a future or past transaction with columns:
| Column | Name | Description |
|--------|------|-------------|
| A | Pay Type | Code indicating payment method (C=Chase, Q=Quicksilver, D=Disney, B=BJs, H=Home Depot, etc.) |
| B | Transaction Name | Name of expense/income (links to Reoccurring Charges for amounts) |
| C | Amount Due | Amount (negative=expense, positive=income). Often uses VLOOKUP to Reoccurring Charges table |
| D | Due Date | Date of transaction |
| E | Chase Balance | Running balance of bank account after this transaction |
| F-P | [Card] Credit | Running available credit for each card after this transaction |
| Q-AA | [Card] Bal | Running balance owed on each card after this transaction |
| AB | Savings | Flag (1/0) for certain transaction types that affect savings |
| AC | % CC Usage | Total credit utilization percentage at this point |

**Key Formulas/Logic:**
- Chase Balance: Starting balance + cumulative sum of all Chase (C) transactions up to current row
- Credit Available: Card's available credit + cumulative charges/payments on that card
- Card Balance: Card's line amount - running credit available
- Amount Due: VLOOKUP from Reoccurring Charges table when transaction name matches

**Special Transactions:**
- "LDBPD" - Likely a paycheck boundary marker (Last Day Before PayDay?)
- "Payday" - Paycheck deposit, amount pulled from PDAY table
- "Lisa" - Payment to spouse, calculated from Lisa payment tables
- "Lisa Club" - Fixed amount to spouse (300)
- Credit card payments where Transaction Name matches a card name

---

### 2. Credit Card Info

Table structure (CCInfo table):
| Column | Field | Description |
|--------|-------|-------------|
| A | Pay Type | Single/double letter code for the card |
| B | List of Credit Cards | Card name |
| C | Balance | Current balance (some are formulas: Line Amount - spent) |
| D | Line Amount | Credit limit |
| E | Available Credit | Line Amount - Balance |
| F | Min Payment | Minimum payment due (some cards = full balance) |
| G | Interest Rate | APR as decimal (e.g., 0.3024 = 30.24%) |
| H | Due Date | Day of month payment is due |
| I | % of Credit Usage | Balance / Line Amount |
| K | Interest on Bal | (Balance × Interest Rate) / 12 (monthly interest) |

**Cards tracked:**
1. BJs (B) - Line: $8,800
2. Quicksilver (Q) - Line: $6,850
3. Disney (D) - Line: $22,000
4. CapOne (C1) - Line: $1,001
5. Merrick (K) - Line: $2,400
6. Milestone (M) - Line: $300
7. Destiny (DE) - Line: $700
8. Dell (DL) - Line: $5,000
9. The Home Depot (H) - Line: $9,800
10. Zales (Z) - Line: $1,300
11. Wyndham Card (W) - Line: $7,000

**Also tracks:**
- 401k Loan 1 (K1) - Original: $6,765.98, Payment: $61.03, Rate: 6.5%
- 401k Loan 2 (K2) - Original: $3,988.01, Payment: $38.60, Rate: 9.5%

---

### 3. Reoccurring Charges

**Main Charges Table (Table7):**
| Column | Field | Description |
|--------|-------|-------------|
| A | Trans Name | Transaction name (matches Summary ledger) |
| B | Amount Due | Amount (negative = expense). Some are formulas pulling from CCInfo |
| C | Due Date | Day of month (1-31) or special codes (991-999 for non-monthly) |
| D | Payment Method | Pay Type code for which account pays this |

**Example recurring charges:**
- HOA: -$117, Day 1, Chase (Q)
- Home Depot payment: pulls from CCInfo balance, Day 2, Chase (C)
- Vivint: -$39.02, Day 2, BJs (B)
- Progressive Insurance: -$490.60, Day 26, Chase (Q)
- Mortgage: -$1,900, Code 991 (special handling)
- SCCU Loan: -$250, Code 993
- Lisa payments: calculated from split tables

**Special Due Date Codes:**
- 991-999: Non-monthly bills (Mortgage, Spaceship, SCCU Loan, Windows, UOAP, Lisa calculations)

---

**Paycheck Table (PDAY, F1:I5):**
Tracks paycheck information across years:
| Year | Net Pay | % Raise | $ Raise |
|------|---------|---------|---------|
| 2023 | [amount] | - | - |
| 2024 | [amount] | 4.5% | [calculated] |
| 2024 Updated | [amount] | [%] | [calculated] |
| 2025 | [amount] | [%] | [calculated] |

Net pay calculated from: Gross Pay - Sum(Deductions)

---

**Pay Stub Deductions Table (Table12, T1:U12):**
Tracks individual paycheck deductions:
| Item | Amount |
|------|--------|
| SS (Social Security) | % of gross (calculated from actual stub) |
| Medicare | % of gross |
| FICA | Combined SS+Medicare |
| Dental | $19.05 |
| Life Insurance | $20.20 |
| Medical | $114.77 |
| Vision | $2.87 |
| 401k | $99.63 (both loan payments) |
| Dependent Life Insurance | $2.08 |
| Child Support | $161.54 |
| ESPP | ~1% of gross |

**Gross Pay Tracking:**
- Tracks gross pay: ~$3,878/pay period for 2025 ($100,793 annual)
- Calculates take-home after all deductions
- Projects annual totals (×26 pay periods)

---

**Lisa Payment Split Tables:**

*2-Paycheck Months (Table11, F21:I26):*
Splits shared household expenses for months with 2 paychecks:
| Item | Monthly | Bi-Weekly | This Week |
|------|---------|-----------|-----------|
| Mortgage | [from Reoccurring] | Monthly/2 | Already Paid or Monthly/2 |
| Spaceship | [from Reoccurring] | Monthly/2 | Monthly/2 |
| Windows | [from Reoccurring] | Monthly/2 | Monthly/2 |
| UOAP | [from Reoccurring] | Monthly/2 | Monthly/2 |
| Total | Sum | Sum | Sum |

*3-Paycheck Months (Table111820, F38:H44):*
Same structure but divides Monthly amounts by 3.

---

**Future Payment Projection (Table3, A47:J282):**
Projects future cash flow and credit card balances:
| Column | Field | Description |
|--------|-------|-------------|
| A | Name | Card name (BJs, Quicksilver, Disney, LDBPD marker) |
| B | Amount | Payment amount (if applicable) |
| C | Date | Transaction date |
| D | Total | Running total balance |
| E | Adj MIN | Adjusted minimum balance calculation |
| F | Rem Bal. | Remaining balance |
| G | Quicksilver Bal | Projected Quicksilver balance |
| H | Disney Bal | Projected Disney balance |
| I | BJs Bal | Projected BJs balance |
| J | PayAmount | Calculated payment amount based on proportional distribution |

**Payment Distribution Logic:**
- Distributes available funds proportionally across cards based on their balance ratios
- Rows 284-289 contain the distribution percentages and payment amounts

---

**Federal Tax Bracket Calculations (Columns T-Z, rows 19-27):**
Calculates estimated federal tax using 2025 brackets:
- 10%: $0 - $11,925 (Single) / $0 - $23,850 (MFJ)
- 12%: $11,926 - $48,475
- 22%: $48,476 - $103,350
- 24%: $103,351 - $197,300
- 32%: $197,301 - $250,525
- 35%: $250,526 - $626,350
- 37%: $626,351+

Calculates for both Single and MFJ, with and without additional deductions.

---

## Application Requirements

### Core Features

1. **Dashboard View**
   - Display current bank account balance (editable)
   - Display savings account balance
   - Show all credit cards with: balance, limit, available credit, % utilization, min payment, interest rate, due date
   - Calculate and display overall credit utilization
   - Show 90-day minimum balance forecast with date
   - Visual alerts when utilization exceeds thresholds (e.g., >30%, >50%)

2. **Transaction Ledger**
   - Add/edit/delete transactions
   - Each transaction has: date, description, amount, payment method
   - Support for recurring transactions that auto-populate
   - Running balances calculated automatically for:
     - Bank account
     - Each credit card (both available credit and balance)
   - Filter/sort by date range, payment method, category
   - Import transactions from CSV/bank exports

3. **Credit Card Management**
   - Add/edit/delete credit cards
   - Track: name, pay type code, credit limit, current balance, interest rate, due date
   - Calculate: available credit, utilization %, monthly interest
   - Support for 401k loans with payment tracking

4. **Recurring Charges Management**
   - Define recurring expenses with: name, amount, day of month, payment method
   - Support for variable amounts (pull from credit card balance for payments)
   - Support for non-monthly expenses (mortgage, etc.)
   - Auto-generate future transactions in ledger
   - Easy bulk update when amounts change

5. **Paycheck Tracking**
   - Enter gross pay amount
   - Define all deductions (taxes, insurance, 401k, etc.)
   - Calculate net pay automatically
   - Track year-over-year changes and raises
   - Auto-generate payday transactions

6. **Household Expense Splitting (Lisa Tables)**
   - Define shared expenses
   - Calculate splits for 2-paycheck and 3-paycheck months
   - Track what's paid vs. owed each pay period

7. **Future Cash Flow Projection**
   - Project balances forward 90+ days
   - Show when minimum balances occur
   - Calculate optimal credit card payment distribution
   - Visual timeline/chart of projected balances

8. **Tax Estimation**
   - Calculate estimated federal tax based on annual income
   - Support single and married filing jointly
   - Show effective tax rate

### Technical Requirements

1. **Data Persistence**
   - Local database (SQLite recommended) or cloud sync option
   - Auto-save functionality
   - Backup/restore capability
   - Export to CSV/Excel for backup

2. **User Interface**
   - Clean, modern interface
   - Dark mode option
   - Mobile-responsive if web-based
   - Keyboard shortcuts for common actions

3. **Calculations**
   - All calculations should be dynamic (like Excel formulas)
   - Changes to recurring charges should cascade to future transactions
   - Changes to credit card info should update all related views

4. **Performance**
   - Handle 1000+ transactions smoothly
   - Fast recalculation when data changes

### Suggested Technology Stack

**Desktop Application:**
- Python with PyQt6 or PySide6 for GUI
- SQLite for database
- Pandas for data manipulation

**Web Application:**
- React or Vue.js frontend
- FastAPI or Flask backend
- PostgreSQL or SQLite database

**Hybrid/Electron:**
- Electron with React
- Local SQLite database

---

## Data Model Suggestion

```
CreditCard:
  - id (PK)
  - pay_type_code (e.g., "Q", "D", "B")
  - name (e.g., "Quicksilver")
  - credit_limit
  - current_balance
  - interest_rate (APR decimal)
  - due_day (1-31)
  - min_payment_type (enum: FIXED, FULL_BALANCE, CALCULATED)
  - min_payment_amount (if FIXED)

Loan:
  - id (PK)
  - name
  - original_amount
  - current_balance
  - interest_rate
  - payment_amount
  - start_date
  - end_date

RecurringCharge:
  - id (PK)
  - name
  - amount (negative = expense, positive = income)
  - day_of_month (1-31 or special codes)
  - payment_method_id (FK to CreditCard or "BANK")
  - frequency (MONTHLY, BIWEEKLY, etc.)
  - amount_type (FIXED, CREDIT_CARD_BALANCE, CALCULATED)
  - linked_card_id (FK, if amount pulls from card balance)

Transaction:
  - id (PK)
  - date
  - description
  - amount
  - payment_method_id
  - recurring_charge_id (FK, null if one-time)
  - is_posted (boolean)

PaycheckConfig:
  - id (PK)
  - gross_amount
  - pay_frequency (BIWEEKLY)
  - effective_date

PaycheckDeduction:
  - id (PK)
  - paycheck_config_id (FK)
  - name
  - amount_type (FIXED, PERCENTAGE)
  - amount

SharedExpense:
  - id (PK)
  - name
  - linked_recurring_charge_id (FK)
  - split_type (HALF, THIRD)

Account:
  - id (PK)
  - name (e.g., "Chase Checking", "Savings")
  - account_type (CHECKING, SAVINGS)
  - current_balance
```

---

## Workflow Examples

### Adding a New Recurring Expense
1. User adds "Netflix" to Recurring Charges: $15.99, Day 15, Quicksilver
2. System auto-generates future transactions for next 12 months
3. Dashboard updates to show impact on credit utilization projections

### Payday Processing
1. User confirms payday arrived
2. System creates income transaction (net pay)
3. System triggers any scheduled payments for Lisa
4. Running balances update throughout ledger

### Credit Card Payment
1. User schedules payment: "Quicksilver" payment on Day 19
2. System calculates optimal amount based on available cash and distribution rules
3. Both bank balance and card balance/available credit update
4. Utilization percentages recalculate

### Editing a Recurring Amount
1. User updates "Progressive Insurance" from $490.60 to $520.00
2. All future occurrences of Progressive in the ledger update automatically
3. Cash flow projections recalculate
4. 90-day minimum balance alert updates if affected

---

## File Reference

The attached Excel file `Budget_v2_Claude.xlsx` contains the complete working system with:
- All formulas and calculations
- Current data and projections
- Table relationships and naming conventions

Use this as the definitive reference for business logic and calculation methods.

---

## Priority Order for Development

1. **Phase 1 - Core Data Entry**
   - Credit card management
   - Recurring charges table
   - Basic transaction entry

2. **Phase 2 - Calculations**
   - Running balance calculations
   - Credit utilization calculations
   - Auto-generation of recurring transactions

3. **Phase 3 - Dashboard**
   - Summary view of all accounts
   - 90-day minimum balance projection
   - Visual indicators and alerts

4. **Phase 4 - Advanced Features**
   - Paycheck configuration and tracking
   - Lisa payment splitting
   - Tax estimation
   - Optimal payment distribution

5. **Phase 5 - Polish**
   - Import/Export functionality
   - Backup/restore
   - Mobile responsiveness (if web)
   - Dark mode
