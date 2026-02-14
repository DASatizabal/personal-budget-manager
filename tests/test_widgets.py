"""Unit tests for custom widgets"""

import pytest
from PyQt6.QtWidgets import QDoubleSpinBox
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QWheelEvent


def _make_wheel_event():
    """Create a synthetic wheel event"""
    return QWheelEvent(
        QPointF(0, 0), QPointF(0, 0),
        QPointF(0, 120).toPoint(), QPointF(0, 120).toPoint(),
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase, False
    )


class TestMoneySpinBox:
    """Tests for MoneySpinBox widget"""

    def test_default_decimals(self, qtbot):
        from budget_app.views.widgets import MoneySpinBox
        w = MoneySpinBox()
        qtbot.addWidget(w)
        assert w.decimals() == 2

    def test_prefix_is_dollar(self, qtbot):
        from budget_app.views.widgets import MoneySpinBox
        w = MoneySpinBox()
        qtbot.addWidget(w)
        assert w.prefix() == "$ "

    def test_range(self, qtbot):
        from budget_app.views.widgets import MoneySpinBox
        w = MoneySpinBox()
        qtbot.addWidget(w)
        assert w.minimum() == -1000000
        assert w.maximum() == 1000000

    def test_no_buttons(self, qtbot):
        from budget_app.views.widgets import MoneySpinBox
        w = MoneySpinBox()
        qtbot.addWidget(w)
        assert w.buttonSymbols() == QDoubleSpinBox.ButtonSymbols.NoButtons

    def test_set_and_get_value(self, qtbot):
        from budget_app.views.widgets import MoneySpinBox
        w = MoneySpinBox()
        qtbot.addWidget(w)
        w.setValue(1234.56)
        assert w.value() == 1234.56

    def test_negative_value(self, qtbot):
        from budget_app.views.widgets import MoneySpinBox
        w = MoneySpinBox()
        qtbot.addWidget(w)
        w.setValue(-500.25)
        assert w.value() == -500.25

    def test_wheel_ignored(self, qtbot):
        from budget_app.views.widgets import MoneySpinBox
        w = MoneySpinBox()
        qtbot.addWidget(w)
        w.setValue(100.0)
        event = _make_wheel_event()
        w.wheelEvent(event)
        assert w.value() == 100.0


class TestPercentSpinBox:
    """Tests for PercentSpinBox widget"""

    def test_default_decimals(self, qtbot):
        from budget_app.views.widgets import PercentSpinBox
        w = PercentSpinBox()
        qtbot.addWidget(w)
        assert w.decimals() == 2

    def test_custom_decimals(self, qtbot):
        from budget_app.views.widgets import PercentSpinBox
        w = PercentSpinBox(decimals=4)
        qtbot.addWidget(w)
        assert w.decimals() == 4

    def test_suffix_is_percent(self, qtbot):
        from budget_app.views.widgets import PercentSpinBox
        w = PercentSpinBox()
        qtbot.addWidget(w)
        assert w.suffix() == " %"

    def test_range(self, qtbot):
        from budget_app.views.widgets import PercentSpinBox
        w = PercentSpinBox()
        qtbot.addWidget(w)
        assert w.minimum() == 0
        assert w.maximum() == 100

    def test_no_buttons(self, qtbot):
        from budget_app.views.widgets import PercentSpinBox
        w = PercentSpinBox()
        qtbot.addWidget(w)
        assert w.buttonSymbols() == QDoubleSpinBox.ButtonSymbols.NoButtons

    def test_set_and_get_value(self, qtbot):
        from budget_app.views.widgets import PercentSpinBox
        w = PercentSpinBox()
        qtbot.addWidget(w)
        w.setValue(18.99)
        assert w.value() == 18.99

    def test_wheel_ignored(self, qtbot):
        from budget_app.views.widgets import PercentSpinBox
        w = PercentSpinBox()
        qtbot.addWidget(w)
        w.setValue(50.0)
        event = _make_wheel_event()
        w.wheelEvent(event)
        assert w.value() == 50.0


class TestNoScrollSpinBoxes:
    """Tests for NoScrollDoubleSpinBox and NoScrollSpinBox"""

    def test_double_spin_wheel_ignored(self, qtbot):
        from budget_app.views.widgets import NoScrollDoubleSpinBox
        w = NoScrollDoubleSpinBox()
        qtbot.addWidget(w)
        w.setValue(42.0)
        event = _make_wheel_event()
        w.wheelEvent(event)
        assert w.value() == 42.0

    def test_spin_wheel_ignored(self, qtbot):
        from budget_app.views.widgets import NoScrollSpinBox
        w = NoScrollSpinBox()
        qtbot.addWidget(w)
        w.setValue(42)
        event = _make_wheel_event()
        w.wheelEvent(event)
        assert w.value() == 42


class TestFocusAndMouseEvents:
    """Tests for focusInEvent and mousePressEvent overrides that trigger selectAll()"""

    def test_money_spinbox_focus_in_triggers_select(self, qtbot):
        from PyQt6.QtGui import QFocusEvent
        from budget_app.views.widgets import MoneySpinBox

        w = MoneySpinBox()
        qtbot.addWidget(w)
        w.setValue(100.00)

        focus_event = QFocusEvent(QFocusEvent.Type.FocusIn)
        w.focusInEvent(focus_event)
        qtbot.wait(10)

        assert w.value() == 100.00

    def test_money_spinbox_mouse_press_when_focused(self, qtbot):
        from PyQt6.QtGui import QFocusEvent, QMouseEvent
        from budget_app.views.widgets import MoneySpinBox

        w = MoneySpinBox()
        qtbot.addWidget(w)
        w.setValue(100.00)

        # Give focus first
        focus_event = QFocusEvent(QFocusEvent.Type.FocusIn)
        w.focusInEvent(focus_event)
        qtbot.wait(10)

        # Now simulate mouse press while already focused
        mouse_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(5, 5),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        w.mousePressEvent(mouse_event)
        qtbot.wait(10)

        assert w.value() == 100.00

    def test_percent_spinbox_focus_in_triggers_select(self, qtbot):
        from PyQt6.QtGui import QFocusEvent
        from budget_app.views.widgets import PercentSpinBox

        w = PercentSpinBox()
        qtbot.addWidget(w)
        w.setValue(25.50)

        focus_event = QFocusEvent(QFocusEvent.Type.FocusIn)
        w.focusInEvent(focus_event)
        qtbot.wait(10)

        assert w.value() == 25.50

    def test_percent_spinbox_mouse_press_when_focused(self, qtbot):
        from PyQt6.QtGui import QFocusEvent, QMouseEvent
        from budget_app.views.widgets import PercentSpinBox

        w = PercentSpinBox()
        qtbot.addWidget(w)
        w.setValue(25.50)

        # Give focus first
        focus_event = QFocusEvent(QFocusEvent.Type.FocusIn)
        w.focusInEvent(focus_event)
        qtbot.wait(10)

        # Now simulate mouse press while already focused
        mouse_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(5, 5),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        w.mousePressEvent(mouse_event)
        qtbot.wait(10)

        assert w.value() == 25.50
