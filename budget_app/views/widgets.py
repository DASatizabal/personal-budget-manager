"""Custom widgets with improved UX"""

from PyQt6.QtWidgets import QDoubleSpinBox, QSpinBox
from PyQt6.QtCore import Qt, QTimer


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that ignores mouse wheel events to prevent accidental changes"""

    def wheelEvent(self, event):
        # Ignore wheel events - user must click and type or use arrows
        event.ignore()


class NoScrollSpinBox(QSpinBox):
    """QSpinBox that ignores mouse wheel events to prevent accidental changes"""

    def wheelEvent(self, event):
        # Ignore wheel events - user must click and type or use arrows
        event.ignore()


class MoneySpinBox(QDoubleSpinBox):
    """
    Monetary input field with improved UX:
    - Auto-selects all text on click/focus for immediate typing
    - No scroll wheel changes
    - No spinner arrows (cleaner appearance)
    - Pre-configured for currency (2 decimals, $ prefix)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDecimals(2)
        self.setPrefix("$ ")
        self.setMinimum(-1000000)
        self.setMaximum(1000000)
        # Hide spinner arrows
        self.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        # Track if we should select all on focus
        self._select_on_focus = True

    def wheelEvent(self, event):
        # Ignore wheel events - prevents accidental changes
        event.ignore()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        if self._select_on_focus:
            # Use QTimer to select after the focus event completes
            QTimer.singleShot(0, self.selectAll)

    def mousePressEvent(self, event):
        # If not already focused, let focusInEvent handle selection
        if not self.hasFocus():
            self._select_on_focus = True
            super().mousePressEvent(event)
        else:
            # Already focused - still select all on click for easy re-entry
            super().mousePressEvent(event)
            QTimer.singleShot(0, self.selectAll)


class PercentSpinBox(QDoubleSpinBox):
    """
    Percentage input field with improved UX:
    - Auto-selects all text on click/focus for immediate typing
    - No scroll wheel changes
    - No spinner arrows (cleaner appearance)
    - Pre-configured for percentages (% suffix)
    """

    def __init__(self, parent=None, decimals=2):
        super().__init__(parent)
        self.setDecimals(decimals)
        self.setSuffix(" %")
        self.setMinimum(0)
        self.setMaximum(100)
        # Hide spinner arrows
        self.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self._select_on_focus = True

    def wheelEvent(self, event):
        event.ignore()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        if self._select_on_focus:
            QTimer.singleShot(0, self.selectAll)

    def mousePressEvent(self, event):
        if not self.hasFocus():
            self._select_on_focus = True
            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)
            QTimer.singleShot(0, self.selectAll)
