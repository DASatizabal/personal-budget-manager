# Task: Modernize PyQt6 GUI Appearance

## Project Context
This is a Personal Budget Manager desktop application built with Python 3.10+ and PyQt6. It has 7 tabs (dashboard, transactions, accounts, credit cards, loans, recurring charges, paychecks) and already has dark mode support implemented.

## Objective
Update the application's visual appearance from the default PyQt6 look to a modern, polished aesthetic. The current UI looks dated (Windows 2000 era).

## Requirements

### 1. Install and integrate a modern theme library
Choose ONE of these approaches (recommend qt-material or qdarkstyle):
- `qt-material` - Material Design themes
- `qdarkstyle` - Clean dark theme
- `PyQtDarkTheme` - Native-looking modern themes

### 2. Integration points
- Apply the theme in `main.py` before the main window is shown
- Ensure it works with the existing dark mode toggle (if present) or replace it with the library's theme switching
- Test that all 7 tabs render correctly with the new theme

### 3. Additional polish
- Add consistent spacing/margins to layouts
- Ensure tables and lists have good row height and padding
- Verify buttons, inputs, and dropdowns look cohesive

## Constraints
- Do not change application functionality or business logic
- Keep all existing features working
- Minimize changes to individual view files - prefer global theming
- Update `requirements.txt` with any new dependencies

## Verification
After implementation:
1. Run `python main.py` to verify the app launches with the new theme
2. Navigate through all tabs to confirm styling is applied consistently
3. Test the dark/light mode toggle if applicable

## File Structure Reference
```
budget_app/
├── models/      # Don't modify
├── views/       # May need minor tweaks for spacing
├── utils/       # Don't modify
└── controllers/ # Don't modify
main.py          # Primary integration point
```
