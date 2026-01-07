# Budget App - TODO List

## Phase 1: Bugs & Critical Fixes [COMPLETED]
- [x] Fix crash when deleting credit card (reproduced with 'Destiny' card)
  - Root cause: Foreign key constraint on `recurring_charges.linked_card_id`
  - Fix: Unlink recurring charges before deletion

## Phase 2: Performance [COMPLETED]
- [x] Optimize Transactions tab loading - add progress bar or streamline performance
  - Added progress bar and wait cursor
  - Blocked table signals during population
  - Inlined running balance calculation
  - Cached card data to avoid redundant DB queries

## Phase 3: UI/UX Improvements [IN PROGRESS]
- [ ] Change date format to American Style MM/DD/YYYY
- [ ] Update 'Update all balance' screen - hardcode $ sign left of input box, remove from input field
- [ ] Fix input boxes - disable scroll behavior, improve amount entry UX
- [ ] Update spacing for better visuals across UI
- [ ] Update Dashboard to have sorting functions
- [ ] Credit card deletion: prompt user to reassign charges/payments before deleting

## Phase 4: Core Features (Code TODOs)
- [ ] Implement CSV export functionality (`main_window.py:182`)
- [ ] Implement balance recalculation tool (`main_window.py:272`)
- [ ] Add error handling to Excel import (`excel_import.py`)
- [ ] Add input validation across views

## Phase 5: Configuration & Flexibility
- [ ] Make special transaction generation configurable (remove hardcoded dates)
- [ ] Add configurable payday frequency (currently hardcoded to biweekly Friday)

## Phase 6: Advanced Features
- [ ] Add tax estimation feature
- [ ] Implement optimal payment distribution algorithm
- [ ] Implement deferred interest purchase handling
- [ ] Implement Credit Card Statement Uploads (PDF/CSV parsing)
- [ ] Implement API Updates for account data (Plaid, Yodlee, or direct bank APIs)

## Phase 7: Project Infrastructure
- [x] Add .gitignore file
- [x] Create STATUS.md (project status tracking)
- [x] Create DECISIONS.md (architecture decisions log)
- [x] Create .claude/HANDOFF.md (Claude Code session handoff)
- [ ] Create pyproject.toml for proper packaging
- [ ] Add logging system
- [ ] Create unit tests
- [ ] Set up GitHub repository

---

## Notes

### Date Format Convention
- **Storage**: ISO format `YYYY-MM-DD` (for database consistency and sorting)
- **Display**: American format `MM/DD/YYYY` (user-facing)

### Credit Card Deletion
When deleting a credit card, any linked recurring charges will be automatically unlinked (their `linked_card_id` set to NULL).

**Enhancement Needed:** When deleting a credit card:
- If current charges exist, prompt user to select which card those charges should be transferred to
- If current payments exist, prompt user to either:
  - Transfer payments to another card, OR
  - Delete those payment transactions entirely
