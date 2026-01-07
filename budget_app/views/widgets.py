"""Custom widgets with improved UX"""

from PyQt6.QtWidgets import QDoubleSpinBox, QSpinBox
from PyQt6.QtCore import Qt


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
