# Budget App - TODO List

## Completed
- [x] Fix crash when deleting credit card (foreign key constraint fix)
- [x] Optimize Transactions tab loading (progress bar, signal blocking, caching)
- [x] Fix Transactions tab re-loading on every tab switch (added dirty flag caching)
- [x] Add .gitignore file
- [x] Create STATUS.md, DECISIONS.md, .claude/HANDOFF.md
- [x] Set up GitHub repository

---

## Phase 1: Quick UI Fixes [COMPLETED]
*Small changes, high impact, no architectural changes*

- [x] 1.1 Change date display format to MM/DD/YYYY (storage stays ISO)
- [x] 1.2 Fix "Update All Balances" dialog - hardcode $ sign left of input, remove from field
- [x] 1.3 Fix input boxes - disable scroll-wheel behavior on spinboxes
- [x] 1.4 Improve spacing/padding across UI for better visuals

## Phase 2: Core Feature Gaps [COMPLETED]
*Essential functionality that's currently stubbed out*

- [x] 2.1 Implement CSV export (File > Export to CSV with table selection and date filtering)
- [x] 2.2 Implement balance recalculation tool (Tools > Recalculate Balances)
- [x] 2.3 Add input validation across all forms (TransactionDialog, CreditCardDialog, RecurringChargeDialog)

## Phase 3: Transactions Tab Enhancements [COMPLETED]
*Most-used view, biggest usability improvements*

- [x] 3.1 Make column widths user-resizable and persist settings (QSettings)
- [x] 3.2 Add show/hide toggle for available balance columns (Columns menu)
- [x] 3.3 Add show/hide toggle for current balance owed columns (Columns menu)
- [x] 3.4 Add multi-select dropdown to filter by specific credit cards (Pay Types filter)
- [x] 3.5 Add summary row showing total available credit across all cards (bottom summary bar)
- [x] 3.6 Show available balance next to amount due for each card (Owed + Avail columns per card)

## Phase 4: Recurring Charges & Generation Fixes [COMPLETED]
*Fix logic issues in transaction generation*

- [x] 4.1 Exclude charges with "Special(###)" due dates from auto-generation
- [x] 4.2 Exclude charges already in "Lisa Payments" tab from duplication (via linked_recurring_id)
- [x] 4.3 Make special transaction generation configurable (uses pay_day_of_week from paycheck config)
- [x] 4.4 Add configurable payday frequency (pay_day_of_week field added to paycheck config)

## Phase 5: Credit Card Management [COMPLETED]
*Better card lifecycle management*

- [x] 5.1 Add "New Credit Card" dialog with all fields (due date, rate, limit, etc.) - already implemented
- [x] 5.2 On card deletion: prompt to reassign linked charges to another card (CardDeletionDialog)
- [x] 5.3 On card deletion: prompt to transfer or delete payment transactions (CardDeletionDialog)

## Phase 6: Dashboard Improvements [COMPLETED]
*Main view enhancements*

- [x] 6.1 Add column sorting to dashboard tables (setSortingEnabled on cards_table and loans_table)
- [x] 6.2 Implement 90-day minimum balance alerts (already implemented)

## Phase 7: Data Safety & Quality [COMPLETED]
*Protect user from mistakes*

- [x] 7.1 Add undo functionality for destructive actions (auto-backup system with Ctrl+Z restore)
- [x] 7.2 Add confirmation dialogs for bulk operations (Excel import, balance updates, generate transactions)
- [x] 7.3 Improve Excel import error handling with detailed feedback (ImportResult with warnings)

## Phase 8: Project Infrastructure [COMPLETED]
*Code quality and maintainability*

- [x] 8.1 Add logging system for debugging (logging_config.py module)
- [x] 8.2 Create unit tests for models and calculations (25 tests in tests/)
- [x] 8.3 Create pyproject.toml for proper packaging

## Phase 8.5: Posted Transactions [COMPLETED]
*Track real vs projected transactions*

- [x] 8.5.1 Add checkbox column to mark transactions as posted
- [x] 8.5.2 Update account/CC balances when marking transaction as posted
- [x] 8.5.3 Add posted_date field to track when transaction was posted
- [x] 8.5.4 Create "Posted" tab showing posted transaction history
- [x] 8.5.5 Add "Clear Posted" button to remove posted items from Transactions view
- [x] 8.5.6 Skip already-posted transactions when regenerating recurring charges
- [x] 8.5.7 Auto-create recurring charge when adding new credit card

## Phase 9: Advanced Features (Future)
*Nice-to-have, significant effort. Ordered by workflow optimization.*

### Quick Wins / Foundational
- [x] 9.1 Auto-select monetary input fields on click
  - All monetary input fields throughout the app should auto-highlight/select on click
  - User can immediately type new amount without manual selection
  - Assume 0 cents until decimal is typed (e.g., typing "150" = $150.00)
  - Remove up/down spinner arrows from monetary fields
  - Apply to: balance fields, amount fields, payment fields, etc.
  - **DONE**: Created `MoneySpinBox` and `PercentSpinBox` widgets in widgets.py
- [x] 9.2 Refresh Recurring Charges tab when Credit Cards tab is updated
  - **DONE**: Added dirty flag pattern to RecurringChargesView, CreditCardsView notifies on changes

### UI Improvements
- [x] 9.3 Dashboard "Quick Update" for balances
  - Enhanced existing UpdateAllBalancesDialog with scroll area
  - Renamed button to "Quick Update" with Ctrl+U shortcut
  - Tab-friendly navigation between fields
  - **DONE**: All balances updatable from single scrollable dialog
- [x] 9.4 Modernize GUI appearance
  - Installed qdarkstyle theme library
  - Applied theme in main.py
  - View > Dark Mode toggle switches between dark/light palettes
  - **DONE**: Clean modern appearance across all tabs

### Core Features
- [x] 9.5 Credit Card Payoff Planner
  - New dedicated "Payoff Planner" tab
  - Five payoff methods implemented:
    - **Avalanche**: Highest APR first (saves most money)
    - **Snowball**: Lowest balance first (psychological wins)
    - **Hybrid**: Weighted score (60% APR, 40% quick wins)
    - **High Utilization**: Highest utilization first (frees credit fastest)
    - **Cash on Hand**: Pay only minimums, maximize bank balance
  - Comparison table showing payoff date, total interest, monthly average
  - Detailed payment schedule breakdown with per-card amounts
  - **DONE**: Full payoff calculator in `budget_app/utils/payoff_calculator.py`

### Parsing Features (Placeholders)
- [x] 9.6 Paycheck/paystub parsing (PDF)
  - "Import from Paystub" button in PaycheckView toolbar
  - Parses gross/net pay, deductions from paystub PDFs via `statement_parser.py`
  - PaystubImportDialog shows comparison with current config, selective import
  - **DONE**: Full implementation with 29 tests
- [x] 9.7 Credit card statement parsing (PDF/CSV upload)
  - PDF statement import UI in `pdf_import_view.py`
  - Supports 8 bank/CC formats via `statement_parser.py`
  - **DONE**: Full implementation with parser and import view

### Advanced Features
- [ ] 9.8 Tax estimation feature - **Skipped per user request**
- [x] 9.9 Deferred interest purchase tracking
  - New "Deferred Interest" tab for tracking 0% APR promos
  - Risk level indicators (Expired, High, Medium, Low)
  - Alerts for expiring promotional periods
  - Calculate potential retroactive interest charges
  - **DONE**: Full implementation with model and view
- [ ] 9.10 Bank API integration (Plaid/Yodlee) - **Placeholder tab created**

---

## Notes

### Date Format Convention
- **Storage**: ISO format `YYYY-MM-DD` (database consistency, sorting)
- **Display**: American format `MM/DD/YYYY` (user-facing)

### Credit Card Deletion Workflow
When deleting a card with linked data:
1. Show list of affected recurring charges
2. Prompt user to select target card for transfer (or delete)
3. Show list of affected transactions
4. Prompt user to transfer or delete
5. Execute deletion only after user confirms all reassignments
