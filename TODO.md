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

## Phase 2: Core Feature Gaps
*Essential functionality that's currently stubbed out*

- [ ] 2.1 Implement CSV export (`main_window.py:182` - currently shows "not implemented")
- [ ] 2.2 Implement balance recalculation tool (`main_window.py:272`)
- [ ] 2.3 Add input validation across all forms (prevent invalid data entry)

## Phase 3: Transactions Tab Enhancements
*Most-used view, biggest usability improvements*

- [ ] 3.1 Make column widths user-resizable and persist settings
- [ ] 3.2 Add show/hide toggle for available balance columns
- [ ] 3.3 Add show/hide toggle for current balance owed columns
- [ ] 3.4 Add multi-select dropdown to filter by specific credit cards
- [ ] 3.5 Add summary row showing total available credit across all cards
- [ ] 3.6 Show available balance next to amount due for each card

## Phase 4: Recurring Charges & Generation Fixes
*Fix logic issues in transaction generation*

- [ ] 4.1 Exclude charges with "Special(###)" due dates from auto-generation
- [ ] 4.2 Exclude charges already in "Lisa Payments" tab from duplication
- [ ] 4.3 Make special transaction generation configurable (remove hardcoded dates)
- [ ] 4.4 Add configurable payday frequency (currently hardcoded to biweekly Friday)

## Phase 5: Credit Card Management
*Better card lifecycle management*

- [ ] 5.1 Add "New Credit Card" dialog with all fields (due date, rate, limit, etc.)
- [ ] 5.2 On card deletion: prompt to reassign linked charges to another card
- [ ] 5.3 On card deletion: prompt to transfer or delete payment transactions

## Phase 6: Dashboard Improvements
*Main view enhancements*

- [ ] 6.1 Add column sorting to dashboard tables
- [ ] 6.2 Implement 90-day minimum balance alerts (from HANDOFF.md priority list)

## Phase 7: Data Safety & Quality
*Protect user from mistakes*

- [ ] 7.1 Add undo functionality for destructive actions
- [ ] 7.2 Add confirmation dialogs for bulk operations
- [ ] 7.3 Improve Excel import error handling with detailed feedback

## Phase 8: Project Infrastructure
*Code quality and maintainability*

- [ ] 8.1 Add logging system for debugging
- [ ] 8.2 Create unit tests for models and calculations
- [ ] 8.3 Create pyproject.toml for proper packaging

## Phase 9: Advanced Features (Future)
*Nice-to-have, significant effort*

- [ ] 9.1 Tax estimation feature
- [ ] 9.2 Optimal payment distribution algorithm
- [ ] 9.3 Deferred interest purchase tracking
- [ ] 9.4 Credit card statement parsing (PDF/CSV upload)
- [ ] 9.5 Bank API integration (Plaid/Yodlee) for auto-import

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
