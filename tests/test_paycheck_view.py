"""Unit tests for Paycheck view and dialogs"""

import pytest
from PyQt6.QtCore import Qt


class TestPaycheckViewNoConfig:
    """Tests for PaycheckView when no config exists"""

    def test_no_config_gross_label(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        assert view.gross_label.text() == "$0.00"

    def test_no_config_deductions_label(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        assert view.deductions_label.text() == "$0.00"

    def test_no_config_net_label(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        assert view.net_label.text() == "$0.00"

    def test_no_config_frequency_label(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        assert view.frequency_label.text() == "N/A"

    def test_no_config_pay_day_label(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        assert view.pay_day_label.text() == "N/A"

    def test_no_config_annual_labels(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        assert view.annual_gross_label.text() == "$0.00"
        assert view.annual_net_label.text() == "$0.00"

    def test_no_config_empty_table(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        assert view.table.rowCount() == 0


class TestPaycheckViewWithConfig:
    """Tests for PaycheckView when a config exists"""

    def test_gross_label(self, qtbot, sample_paycheck_config):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        assert view.gross_label.text() == "$3,500.00"

    def test_net_label(self, qtbot, sample_paycheck_config):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        # Net = 3500 - (3500*0.22 + 250) = 3500 - (770 + 250) = 3500 - 1020 = 2480
        assert view.net_label.text() == "$2,480.00"

    def test_deductions_label(self, qtbot, sample_paycheck_config):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        # Total deductions = 3500*0.22 + 250 = 770 + 250 = 1020
        assert view.deductions_label.text() == "$1,020.00"

    def test_frequency_label(self, qtbot, sample_paycheck_config):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        assert view.frequency_label.text() == "BIWEEKLY"

    def test_pay_day_label_friday(self, qtbot, sample_paycheck_config):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        assert view.pay_day_label.text() == "Friday"

    def test_annual_gross_label(self, qtbot, sample_paycheck_config):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        # BIWEEKLY: 3500 * 26 = 91000
        assert view.annual_gross_label.text() == "$91,000.00"

    def test_annual_net_label(self, qtbot, sample_paycheck_config):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        # BIWEEKLY: 2480 * 26 = 64480
        assert view.annual_net_label.text() == "$64,480.00"

    def test_deductions_table_row_count(self, qtbot, sample_paycheck_config):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        assert view.table.rowCount() == 2

    def test_deductions_table_percentage_format(self, qtbot, sample_paycheck_config):
        """PERCENTAGE deduction shows '22.0000%' in Amount/Rate column"""
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        # Find the Federal Tax row (PERCENTAGE type)
        for row in range(view.table.rowCount()):
            if view.table.item(row, 0).text() == "Federal Tax":
                assert view.table.item(row, 2).text() == "22.0000%"
                break
        else:
            pytest.fail("Federal Tax deduction not found in table")

    def test_deductions_table_fixed_format(self, qtbot, sample_paycheck_config):
        """FIXED deduction shows '$250.00' in Amount/Rate column"""
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        # Find the Health Insurance row (FIXED type)
        for row in range(view.table.rowCount()):
            if view.table.item(row, 0).text() == "Health Insurance":
                assert view.table.item(row, 2).text() == "$250.00"
                break
        else:
            pytest.fail("Health Insurance deduction not found in table")

    def test_deductions_table_calculated_amounts(self, qtbot, sample_paycheck_config):
        """Calculated Amount column shows correct values"""
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        for row in range(view.table.rowCount()):
            name = view.table.item(row, 0).text()
            calc_text = view.table.item(row, 3).text()
            if name == "Federal Tax":
                # 3500 * 0.22 = 770
                assert calc_text == "$770.00"
            elif name == "Health Insurance":
                assert calc_text == "$250.00"

    def test_deductions_table_type_column(self, qtbot, sample_paycheck_config):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        types_found = set()
        for row in range(view.table.rowCount()):
            types_found.add(view.table.item(row, 1).text())
        assert "PERCENTAGE" in types_found
        assert "FIXED" in types_found

    def test_deduction_id_stored_in_user_role(self, qtbot, sample_paycheck_config):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        stored_id = view.table.item(0, 0).data(Qt.ItemDataRole.UserRole)
        assert stored_id is not None


class TestPaycheckViewActions:
    """Tests for PaycheckView button actions"""

    def test_add_deduction_without_config_warns(self, qtbot, temp_db, mock_qmessagebox):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        view._add_deduction()
        assert mock_qmessagebox.warning_called
        assert "configuration first" in mock_qmessagebox.warning_text

    def test_edit_deduction_no_selection_warns(self, qtbot, sample_paycheck_config, mock_qmessagebox):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        view._edit_deduction()
        assert mock_qmessagebox.warning_called
        assert "select" in mock_qmessagebox.warning_text.lower()

    def test_delete_deduction_no_selection_warns(self, qtbot, sample_paycheck_config, mock_qmessagebox):
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        view._delete_deduction()
        assert mock_qmessagebox.warning_called
        assert "select" in mock_qmessagebox.warning_text.lower()


class TestPaycheckConfigDialog:
    """Tests for PaycheckConfigDialog"""

    def test_default_friday(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaycheckConfigDialog
        dialog = PaycheckConfigDialog()
        qtbot.addWidget(dialog)
        assert dialog.pay_day_combo.currentIndex() == 4
        assert dialog.pay_day_combo.currentText() == "Friday"

    def test_populate_fields(self, qtbot, sample_paycheck_config):
        from budget_app.views.paycheck_view import PaycheckConfigDialog
        dialog = PaycheckConfigDialog(config=sample_paycheck_config)
        qtbot.addWidget(dialog)
        assert dialog.gross_spin.value() == 3500.0
        assert dialog.frequency_combo.currentText() == "BIWEEKLY"
        assert dialog.pay_day_combo.currentText() == "Friday"

    def test_get_config_returns_correct_values(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaycheckConfigDialog
        dialog = PaycheckConfigDialog()
        qtbot.addWidget(dialog)
        dialog.gross_spin.setValue(5000.0)
        dialog.frequency_combo.setCurrentIndex(
            dialog.frequency_combo.findText("MONTHLY")
        )
        dialog.pay_day_combo.setCurrentIndex(0)  # Monday

        config = dialog.get_config()
        assert config.gross_amount == 5000.0
        assert config.pay_frequency == "MONTHLY"
        assert config.pay_day_of_week == 0
        assert config.is_current is True
        assert config.id is None

    def test_frequency_options(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaycheckConfigDialog
        dialog = PaycheckConfigDialog()
        qtbot.addWidget(dialog)
        options = [dialog.frequency_combo.itemText(i)
                   for i in range(dialog.frequency_combo.count())]
        assert options == ["BIWEEKLY", "WEEKLY", "SEMIMONTHLY", "MONTHLY"]

    def test_window_title(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaycheckConfigDialog
        dialog = PaycheckConfigDialog()
        qtbot.addWidget(dialog)
        assert "Edit Paycheck Configuration" in dialog.windowTitle()


class TestDeductionDialog:
    """Tests for DeductionDialog"""

    def test_title_add(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import DeductionDialog
        dialog = DeductionDialog(gross_pay=3500.0)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Add Deduction"

    def test_title_edit(self, qtbot, temp_db):
        from budget_app.models.paycheck import PaycheckDeduction
        from budget_app.views.paycheck_view import DeductionDialog
        deduction = PaycheckDeduction(
            id=1, paycheck_config_id=1,
            name="Test", amount_type="FIXED", amount=100.0
        )
        dialog = DeductionDialog(gross_pay=3500.0, deduction=deduction)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Edit Deduction"

    def test_type_toggle_shows_percent_spin(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import DeductionDialog
        dialog = DeductionDialog(gross_pay=3500.0)
        qtbot.addWidget(dialog)
        # Initially FIXED: amount_spin not hidden, percent_spin hidden
        assert not dialog.amount_spin.isHidden()
        assert dialog.percent_spin.isHidden()
        # Switch to PERCENTAGE
        dialog.type_combo.setCurrentIndex(1)
        assert dialog.amount_spin.isHidden()
        assert not dialog.percent_spin.isHidden()

    def test_type_toggle_shows_amount_spin(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import DeductionDialog
        dialog = DeductionDialog(gross_pay=3500.0)
        qtbot.addWidget(dialog)
        # Switch to PERCENTAGE then back to FIXED
        dialog.type_combo.setCurrentIndex(1)
        dialog.type_combo.setCurrentIndex(0)
        assert not dialog.amount_spin.isHidden()
        assert dialog.percent_spin.isHidden()

    def test_calculated_label_fixed(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import DeductionDialog
        dialog = DeductionDialog(gross_pay=3500.0)
        qtbot.addWidget(dialog)
        dialog.type_combo.setCurrentIndex(0)  # FIXED
        dialog.amount_spin.setValue(250.0)
        assert dialog.calc_label.text() == "$250.00"

    def test_calculated_label_percentage(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import DeductionDialog
        dialog = DeductionDialog(gross_pay=3500.0)
        qtbot.addWidget(dialog)
        dialog.type_combo.setCurrentIndex(1)  # PERCENTAGE
        dialog.percent_spin.setValue(22.0)
        # 3500 * (22 / 100) = 770
        assert dialog.calc_label.text() == "$770.00"

    def test_populate_fields_percentage(self, qtbot, temp_db):
        from budget_app.models.paycheck import PaycheckDeduction
        from budget_app.views.paycheck_view import DeductionDialog
        deduction = PaycheckDeduction(
            id=1, paycheck_config_id=1,
            name="Federal Tax", amount_type="PERCENTAGE", amount=0.22
        )
        dialog = DeductionDialog(gross_pay=3500.0, deduction=deduction)
        qtbot.addWidget(dialog)
        assert dialog.name_edit.text() == "Federal Tax"
        assert dialog.type_combo.currentText() == "PERCENTAGE"
        assert abs(dialog.percent_spin.value() - 22.0) < 0.001

    def test_populate_fields_fixed(self, qtbot, temp_db):
        from budget_app.models.paycheck import PaycheckDeduction
        from budget_app.views.paycheck_view import DeductionDialog
        deduction = PaycheckDeduction(
            id=1, paycheck_config_id=1,
            name="Health Insurance", amount_type="FIXED", amount=250.0
        )
        dialog = DeductionDialog(gross_pay=3500.0, deduction=deduction)
        qtbot.addWidget(dialog)
        assert dialog.name_edit.text() == "Health Insurance"
        assert dialog.type_combo.currentText() == "FIXED"
        assert dialog.amount_spin.value() == 250.0

    def test_get_deduction_fixed(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import DeductionDialog
        dialog = DeductionDialog(gross_pay=3500.0)
        qtbot.addWidget(dialog)
        dialog.name_edit.setText("401k")
        dialog.type_combo.setCurrentIndex(0)  # FIXED
        dialog.amount_spin.setValue(150.0)
        deduction = dialog.get_deduction()
        assert deduction.name == "401k"
        assert deduction.amount_type == "FIXED"
        assert deduction.amount == 150.0
        assert deduction.id is None

    def test_get_deduction_percentage_as_decimal(self, qtbot, temp_db):
        """get_deduction converts percentage spin value to decimal (22% -> 0.22)"""
        from budget_app.views.paycheck_view import DeductionDialog
        dialog = DeductionDialog(gross_pay=3500.0)
        qtbot.addWidget(dialog)
        dialog.name_edit.setText("State Tax")
        dialog.type_combo.setCurrentIndex(1)  # PERCENTAGE
        dialog.percent_spin.setValue(5.75)
        deduction = dialog.get_deduction()
        assert deduction.name == "State Tax"
        assert deduction.amount_type == "PERCENTAGE"
        assert abs(deduction.amount - 0.0575) < 0.00001
