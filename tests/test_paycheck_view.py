"""Unit tests for Paycheck view and dialogs"""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog


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


class TestPaycheckViewConfigDisplay:
    """Tests for PaycheckView display values with a paycheck config"""

    def test_annual_gross_label_with_config(self, qtbot, sample_paycheck_config):
        """Annual gross label should show gross_amount * frequency multiplier"""
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        # BIWEEKLY: 3500 * 26 = 91000
        assert view.annual_gross_label.text() == "$91,000.00"

    def test_annual_net_label_with_config(self, qtbot, sample_paycheck_config):
        """Annual net label should show net_pay * frequency multiplier"""
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        # Net = 3500 - (3500*0.22 + 250) = 2480
        # BIWEEKLY: 2480 * 26 = 64480
        assert view.annual_net_label.text() == "$64,480.00"

    def test_pay_day_label_shows_day_name(self, qtbot, sample_paycheck_config):
        """Pay day label should display day name for pay_day_of_week=4 (Friday)"""
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        assert view.pay_day_label.text() == "Friday"

    def test_deduction_percentage_display(self, qtbot, sample_paycheck_config):
        """Percentage deduction should display in the table as '22.0000%'"""
        from budget_app.views.paycheck_view import PaycheckView
        view = PaycheckView()
        qtbot.addWidget(view)
        # Find the Federal Tax row (PERCENTAGE type) and verify format
        for row in range(view.table.rowCount()):
            if view.table.item(row, 0).text() == "Federal Tax":
                assert view.table.item(row, 2).text() == "22.0000%"
                break
        else:
            pytest.fail("Federal Tax deduction not found in table")


# ---------------------------------------------------------------------------
# Helper: build a mock StatementData for payslip tests
# ---------------------------------------------------------------------------

def _make_payslip_data(
    gross_pay=4000.0,
    net_pay=3100.0,
    deductions=None,
    pay_period_start='2026-01-01',
    pay_period_end='2026-01-15',
    statement_type='payslip',
):
    """Return a StatementData-like object for paystub tests."""
    from budget_app.utils.statement_parser import StatementData
    return StatementData(
        statement_type=statement_type,
        gross_pay=gross_pay,
        net_pay=net_pay,
        deductions=deductions or {'Federal Tax': 600.0, '401k': 300.0},
        pay_period_start=pay_period_start,
        pay_period_end=pay_period_end,
    )


# ---------------------------------------------------------------------------
# Tests for PaystubImportDialog
# ---------------------------------------------------------------------------

class TestPaystubImportDialog:
    """Tests for the PaystubImportDialog review dialog"""

    def test_window_title(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaystubImportDialog
        data = _make_payslip_data()
        dialog = PaystubImportDialog(None, data)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Import Paystub"

    def test_gross_pay_label(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaystubImportDialog
        from PyQt6.QtWidgets import QLabel
        data = _make_payslip_data(gross_pay=4000.0)
        dialog = PaystubImportDialog(None, data)
        qtbot.addWidget(dialog)
        texts = [w.text() for w in dialog.findChildren(QLabel)]
        assert "$4,000.00" in texts

    def test_net_pay_label_shown(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaystubImportDialog
        from PyQt6.QtWidgets import QLabel
        data = _make_payslip_data(net_pay=3100.0)
        dialog = PaystubImportDialog(None, data)
        qtbot.addWidget(dialog)
        texts = [w.text() for w in dialog.findChildren(QLabel)]
        assert "$3,100.00" in texts

    def test_net_pay_label_green(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaystubImportDialog
        from PyQt6.QtWidgets import QLabel
        data = _make_payslip_data(net_pay=3100.0)
        dialog = PaystubImportDialog(None, data)
        qtbot.addWidget(dialog)
        for label in dialog.findChildren(QLabel):
            if label.text() == "$3,100.00":
                assert "#4caf50" in label.styleSheet()
                break
        else:
            pytest.fail("Net pay label not found")

    def test_pay_period_shown_when_present(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaystubImportDialog
        from PyQt6.QtWidgets import QLabel
        data = _make_payslip_data(pay_period_start='2026-01-01', pay_period_end='2026-01-15')
        dialog = PaystubImportDialog(None, data)
        qtbot.addWidget(dialog)
        texts = [w.text() for w in dialog.findChildren(QLabel)]
        assert any("2026-01-01" in t and "2026-01-15" in t for t in texts)

    def test_pay_period_absent_when_missing(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaystubImportDialog
        from PyQt6.QtWidgets import QLabel
        data = _make_payslip_data(pay_period_start='', pay_period_end='')
        dialog = PaystubImportDialog(None, data)
        qtbot.addWidget(dialog)
        texts = [w.text() for w in dialog.findChildren(QLabel)]
        assert not any("Pay Period:" == t for t in texts)

    def test_deductions_table_row_count(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaystubImportDialog
        from PyQt6.QtWidgets import QTableWidget
        data = _make_payslip_data(deductions={'Fed Tax': 600, '401k': 300, 'Health': 150})
        dialog = PaystubImportDialog(None, data)
        qtbot.addWidget(dialog)
        table = dialog.findChild(QTableWidget)
        assert table.rowCount() == 3

    def test_deductions_table_values(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaystubImportDialog
        from PyQt6.QtWidgets import QTableWidget
        data = _make_payslip_data(deductions={'Fed Tax': 600.0, '401k': 300.0})
        dialog = PaystubImportDialog(None, data)
        qtbot.addWidget(dialog)
        table = dialog.findChild(QTableWidget)
        names = {table.item(r, 0).text() for r in range(table.rowCount())}
        amounts = {table.item(r, 1).text() for r in range(table.rowCount())}
        assert 'Fed Tax' in names
        assert '401k' in names
        assert '$600.00' in amounts
        assert '$300.00' in amounts

    def test_comparison_group_shown_with_config(self, qtbot, sample_paycheck_config):
        from budget_app.views.paycheck_view import PaystubImportDialog
        from PyQt6.QtWidgets import QGroupBox
        data = _make_payslip_data()
        dialog = PaystubImportDialog(None, data, config=sample_paycheck_config)
        qtbot.addWidget(dialog)
        groups = [g.title() for g in dialog.findChildren(QGroupBox)]
        assert "Comparison with Current Config" in groups

    def test_comparison_group_absent_without_config(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaystubImportDialog
        from PyQt6.QtWidgets import QGroupBox
        data = _make_payslip_data()
        dialog = PaystubImportDialog(None, data, config=None)
        qtbot.addWidget(dialog)
        groups = [g.title() for g in dialog.findChildren(QGroupBox)]
        assert "Comparison with Current Config" not in groups

    def test_gross_diff_positive_green(self, qtbot, sample_paycheck_config):
        """Gross diff > 0 should be green (paystub > config)"""
        from budget_app.views.paycheck_view import PaystubImportDialog
        from PyQt6.QtWidgets import QLabel
        # config gross = 3500, paystub gross = 4000 → diff = +500
        data = _make_payslip_data(gross_pay=4000.0)
        dialog = PaystubImportDialog(None, data, config=sample_paycheck_config)
        qtbot.addWidget(dialog)
        for label in dialog.findChildren(QLabel):
            if "+500" in label.text():
                assert "#4caf50" in label.styleSheet()
                break
        else:
            pytest.fail("Positive gross diff label not found")

    def test_gross_diff_negative_red(self, qtbot, sample_paycheck_config):
        """Gross diff < 0 should be red (paystub < config)"""
        from budget_app.views.paycheck_view import PaystubImportDialog
        from PyQt6.QtWidgets import QLabel
        # config gross = 3500, paystub gross = 3000 → diff = -500
        data = _make_payslip_data(gross_pay=3000.0)
        dialog = PaystubImportDialog(None, data, config=sample_paycheck_config)
        qtbot.addWidget(dialog)
        for label in dialog.findChildren(QLabel):
            if "-500" in label.text():
                assert "#f44336" in label.styleSheet()
                break
        else:
            pytest.fail("Negative gross diff label not found")

    def test_checkboxes_default_checked(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaystubImportDialog
        data = _make_payslip_data()
        dialog = PaystubImportDialog(None, data)
        qtbot.addWidget(dialog)
        assert dialog.update_gross_cb.isChecked()
        assert dialog.replace_deductions_cb.isChecked()

    def test_minimum_width(self, qtbot, temp_db):
        from budget_app.views.paycheck_view import PaystubImportDialog
        data = _make_payslip_data()
        dialog = PaystubImportDialog(None, data)
        qtbot.addWidget(dialog)
        assert dialog.minimumWidth() == 550


# ---------------------------------------------------------------------------
# Tests for PaycheckView._import_paystub
# ---------------------------------------------------------------------------

class TestImportPaystub:
    """Tests for the _import_paystub method on PaycheckView"""

    def test_file_dialog_cancel_does_nothing(self, qtbot, temp_db, monkeypatch):
        """Cancelling the file dialog should not crash or open any further dialog"""
        from budget_app.views.paycheck_view import PaycheckView
        from PyQt6.QtWidgets import QFileDialog
        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('', '')))
        view = PaycheckView()
        qtbot.addWidget(view)
        view._import_paystub()  # should return silently

    def test_parse_error_shows_critical(self, qtbot, temp_db, monkeypatch, mock_qmessagebox):
        """Parse failure should show QMessageBox.critical"""
        from budget_app.views.paycheck_view import PaycheckView
        from PyQt6.QtWidgets import QFileDialog
        import budget_app.views.paycheck_view as pv
        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/fake/paystub.pdf', 'PDF Files (*.pdf)')))
        monkeypatch.setattr(pv, 'parse_statement', lambda path: (_ for _ in ()).throw(ValueError("bad pdf")))
        view = PaycheckView()
        qtbot.addWidget(view)
        view._import_paystub()
        assert mock_qmessagebox.critical_called
        assert "bad pdf" in mock_qmessagebox.critical_text

    def test_wrong_doc_type_shows_warning(self, qtbot, temp_db, monkeypatch, mock_qmessagebox):
        """Non-payslip document should show QMessageBox.warning"""
        from budget_app.views.paycheck_view import PaycheckView
        from PyQt6.QtWidgets import QFileDialog
        import budget_app.views.paycheck_view as pv
        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/fake/stmt.pdf', 'PDF Files (*.pdf)')))
        data = _make_payslip_data(statement_type='credit_card')
        monkeypatch.setattr(pv, 'parse_statement', lambda path: data)
        view = PaycheckView()
        qtbot.addWidget(view)
        view._import_paystub()
        assert mock_qmessagebox.warning_called
        assert "credit_card" in mock_qmessagebox.warning_text

    def test_successful_parse_opens_dialog(self, qtbot, temp_db, monkeypatch):
        """Successful parse should open PaystubImportDialog"""
        from budget_app.views.paycheck_view import PaycheckView, PaystubImportDialog
        from PyQt6.QtWidgets import QFileDialog
        import budget_app.views.paycheck_view as pv
        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/fake/paystub.pdf', 'PDF Files (*.pdf)')))
        data = _make_payslip_data()
        monkeypatch.setattr(pv, 'parse_statement', lambda path: data)
        dialog_opened = []
        monkeypatch.setattr(PaystubImportDialog, 'exec',
                            lambda self: (dialog_opened.append(True),
                                          QDialog.DialogCode.Rejected)[-1])
        view = PaycheckView()
        qtbot.addWidget(view)
        view._import_paystub()
        assert len(dialog_opened) == 1

    def test_dialog_cancel_no_changes(self, qtbot, sample_paycheck_config, monkeypatch):
        """Cancelling the import dialog should not modify config"""
        from budget_app.views.paycheck_view import PaycheckView, PaystubImportDialog
        from budget_app.models.paycheck import PaycheckConfig
        from PyQt6.QtWidgets import QFileDialog
        import budget_app.views.paycheck_view as pv

        original_gross = sample_paycheck_config.gross_amount
        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/fake/paystub.pdf', 'PDF Files (*.pdf)')))
        data = _make_payslip_data(gross_pay=9999.0)
        monkeypatch.setattr(pv, 'parse_statement', lambda path: data)
        monkeypatch.setattr(PaystubImportDialog, 'exec',
                            lambda self: QDialog.DialogCode.Rejected)
        view = PaycheckView()
        qtbot.addWidget(view)
        view._import_paystub()
        config = PaycheckConfig.get_current()
        assert config.gross_amount == original_gross

    def test_accept_both_checkboxes(self, qtbot, sample_paycheck_config, monkeypatch):
        """Accept with both checkboxes: updates gross and replaces deductions"""
        from budget_app.views.paycheck_view import PaycheckView, PaystubImportDialog
        from budget_app.models.paycheck import PaycheckConfig
        from PyQt6.QtWidgets import QFileDialog
        import budget_app.views.paycheck_view as pv

        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/fake/paystub.pdf', 'PDF Files (*.pdf)')))
        data = _make_payslip_data(gross_pay=5000.0,
                                   deductions={'State Tax': 200.0, 'Dental': 50.0})
        monkeypatch.setattr(pv, 'parse_statement', lambda path: data)
        # Both checkboxes default to checked, just accept
        monkeypatch.setattr(PaystubImportDialog, 'exec',
                            lambda self: QDialog.DialogCode.Accepted)
        view = PaycheckView()
        qtbot.addWidget(view)
        view._import_paystub()

        config = PaycheckConfig.get_current()
        assert config.gross_amount == 5000.0
        names = {d.name for d in config.deductions}
        assert names == {'State Tax', 'Dental'}

    def test_accept_only_update_gross(self, qtbot, sample_paycheck_config, monkeypatch):
        """Accept with only 'Update gross' checked: gross changes, deductions stay"""
        from budget_app.views.paycheck_view import PaycheckView, PaystubImportDialog
        from budget_app.models.paycheck import PaycheckConfig
        from PyQt6.QtWidgets import QFileDialog
        import budget_app.views.paycheck_view as pv

        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/fake/paystub.pdf', 'PDF Files (*.pdf)')))
        data = _make_payslip_data(gross_pay=6000.0, deductions={'NewDed': 100.0})
        monkeypatch.setattr(pv, 'parse_statement', lambda path: data)

        def exec_with_only_gross(self):
            self.replace_deductions_cb.setChecked(False)
            return QDialog.DialogCode.Accepted
        monkeypatch.setattr(PaystubImportDialog, 'exec', exec_with_only_gross)

        view = PaycheckView()
        qtbot.addWidget(view)
        view._import_paystub()

        config = PaycheckConfig.get_current()
        assert config.gross_amount == 6000.0
        # Original deductions should remain (Federal Tax, Health Insurance)
        names = {d.name for d in config.deductions}
        assert 'Federal Tax' in names
        assert 'Health Insurance' in names

    def test_accept_only_replace_deductions(self, qtbot, sample_paycheck_config, monkeypatch):
        """Accept with only 'Replace deductions' checked: gross stays, deductions replaced"""
        from budget_app.views.paycheck_view import PaycheckView, PaystubImportDialog
        from budget_app.models.paycheck import PaycheckConfig
        from PyQt6.QtWidgets import QFileDialog
        import budget_app.views.paycheck_view as pv

        original_gross = sample_paycheck_config.gross_amount
        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/fake/paystub.pdf', 'PDF Files (*.pdf)')))
        data = _make_payslip_data(gross_pay=9999.0, deductions={'NewDed': 100.0})
        monkeypatch.setattr(pv, 'parse_statement', lambda path: data)

        def exec_with_only_deductions(self):
            self.update_gross_cb.setChecked(False)
            return QDialog.DialogCode.Accepted
        monkeypatch.setattr(PaystubImportDialog, 'exec', exec_with_only_deductions)

        view = PaycheckView()
        qtbot.addWidget(view)
        view._import_paystub()

        config = PaycheckConfig.get_current()
        assert config.gross_amount == original_gross
        names = {d.name for d in config.deductions}
        assert names == {'NewDed'}

    def test_accept_neither_checkbox(self, qtbot, sample_paycheck_config, monkeypatch):
        """Accept with neither checkbox: no changes to config"""
        from budget_app.views.paycheck_view import PaycheckView, PaystubImportDialog
        from budget_app.models.paycheck import PaycheckConfig
        from PyQt6.QtWidgets import QFileDialog
        import budget_app.views.paycheck_view as pv

        original_gross = sample_paycheck_config.gross_amount
        original_deduction_names = {d.name for d in sample_paycheck_config.deductions}
        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/fake/paystub.pdf', 'PDF Files (*.pdf)')))
        data = _make_payslip_data(gross_pay=9999.0, deductions={'NewDed': 100.0})
        monkeypatch.setattr(pv, 'parse_statement', lambda path: data)

        def exec_with_nothing(self):
            self.update_gross_cb.setChecked(False)
            self.replace_deductions_cb.setChecked(False)
            return QDialog.DialogCode.Accepted
        monkeypatch.setattr(PaystubImportDialog, 'exec', exec_with_nothing)

        view = PaycheckView()
        qtbot.addWidget(view)
        view._import_paystub()

        config = PaycheckConfig.get_current()
        assert config.gross_amount == original_gross
        assert {d.name for d in config.deductions} == original_deduction_names

    def test_import_creates_config_when_none_exists(self, qtbot, temp_db, monkeypatch):
        """Import when no config exists should create a new PaycheckConfig"""
        from budget_app.views.paycheck_view import PaycheckView, PaystubImportDialog
        from budget_app.models.paycheck import PaycheckConfig
        from PyQt6.QtWidgets import QFileDialog
        import budget_app.views.paycheck_view as pv

        assert PaycheckConfig.get_current() is None

        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/fake/paystub.pdf', 'PDF Files (*.pdf)')))
        data = _make_payslip_data(gross_pay=4500.0, deductions={'Tax': 500.0})
        monkeypatch.setattr(pv, 'parse_statement', lambda path: data)
        monkeypatch.setattr(PaystubImportDialog, 'exec',
                            lambda self: QDialog.DialogCode.Accepted)

        view = PaycheckView()
        qtbot.addWidget(view)
        view._import_paystub()

        config = PaycheckConfig.get_current()
        assert config is not None
        assert config.gross_amount == 4500.0

    def test_import_replaces_all_old_deductions(self, qtbot, sample_paycheck_config, monkeypatch):
        """Replacing deductions should delete all old ones"""
        from budget_app.views.paycheck_view import PaycheckView, PaystubImportDialog
        from budget_app.models.paycheck import PaycheckConfig
        from PyQt6.QtWidgets import QFileDialog
        import budget_app.views.paycheck_view as pv

        # sample_paycheck_config has 2 deductions (Federal Tax, Health Insurance)
        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/fake/paystub.pdf', 'PDF Files (*.pdf)')))
        data = _make_payslip_data(deductions={'Only One': 123.0})
        monkeypatch.setattr(pv, 'parse_statement', lambda path: data)
        monkeypatch.setattr(PaystubImportDialog, 'exec',
                            lambda self: QDialog.DialogCode.Accepted)

        view = PaycheckView()
        qtbot.addWidget(view)
        view._import_paystub()

        config = PaycheckConfig.get_current()
        assert len(config.deductions) == 1
        assert config.deductions[0].name == 'Only One'

    def test_deductions_saved_as_fixed_type(self, qtbot, sample_paycheck_config, monkeypatch):
        """Imported deductions should be saved as FIXED type"""
        from budget_app.views.paycheck_view import PaycheckView, PaystubImportDialog
        from budget_app.models.paycheck import PaycheckConfig
        from PyQt6.QtWidgets import QFileDialog
        import budget_app.views.paycheck_view as pv

        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/fake/paystub.pdf', 'PDF Files (*.pdf)')))
        data = _make_payslip_data(deductions={'Tax': 600.0, '401k': 300.0})
        monkeypatch.setattr(pv, 'parse_statement', lambda path: data)
        monkeypatch.setattr(PaystubImportDialog, 'exec',
                            lambda self: QDialog.DialogCode.Accepted)

        view = PaycheckView()
        qtbot.addWidget(view)
        view._import_paystub()

        config = PaycheckConfig.get_current()
        for d in config.deductions:
            assert d.amount_type == 'FIXED'

    def test_deductions_correct_amounts(self, qtbot, sample_paycheck_config, monkeypatch):
        """Imported deductions should have correct dollar amounts"""
        from budget_app.views.paycheck_view import PaycheckView, PaystubImportDialog
        from budget_app.models.paycheck import PaycheckConfig
        from PyQt6.QtWidgets import QFileDialog
        import budget_app.views.paycheck_view as pv

        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/fake/paystub.pdf', 'PDF Files (*.pdf)')))
        data = _make_payslip_data(deductions={'Tax': 600.0, '401k': 300.0})
        monkeypatch.setattr(pv, 'parse_statement', lambda path: data)
        monkeypatch.setattr(PaystubImportDialog, 'exec',
                            lambda self: QDialog.DialogCode.Accepted)

        view = PaycheckView()
        qtbot.addWidget(view)
        view._import_paystub()

        config = PaycheckConfig.get_current()
        amounts = {d.name: d.amount for d in config.deductions}
        assert amounts['Tax'] == 600.0
        assert amounts['401k'] == 300.0

    def test_deductions_have_correct_config_id(self, qtbot, sample_paycheck_config, monkeypatch):
        """Imported deductions should have the correct paycheck_config_id"""
        from budget_app.views.paycheck_view import PaycheckView, PaystubImportDialog
        from budget_app.models.paycheck import PaycheckConfig
        from PyQt6.QtWidgets import QFileDialog
        import budget_app.views.paycheck_view as pv

        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/fake/paystub.pdf', 'PDF Files (*.pdf)')))
        data = _make_payslip_data(deductions={'Tax': 600.0})
        monkeypatch.setattr(pv, 'parse_statement', lambda path: data)
        monkeypatch.setattr(PaystubImportDialog, 'exec',
                            lambda self: QDialog.DialogCode.Accepted)

        view = PaycheckView()
        qtbot.addWidget(view)
        view._import_paystub()

        config = PaycheckConfig.get_current()
        for d in config.deductions:
            assert d.paycheck_config_id == config.id

    def test_view_refreshes_after_import(self, qtbot, sample_paycheck_config, monkeypatch):
        """After successful import, the view should refresh to show new values"""
        from budget_app.views.paycheck_view import PaycheckView, PaystubImportDialog
        from PyQt6.QtWidgets import QFileDialog
        import budget_app.views.paycheck_view as pv

        monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                            staticmethod(lambda *a, **kw: ('/fake/paystub.pdf', 'PDF Files (*.pdf)')))
        data = _make_payslip_data(gross_pay=7777.0, deductions={})
        monkeypatch.setattr(pv, 'parse_statement', lambda path: data)
        monkeypatch.setattr(PaystubImportDialog, 'exec',
                            lambda self: QDialog.DialogCode.Accepted)

        view = PaycheckView()
        qtbot.addWidget(view)
        view._import_paystub()

        assert view.gross_label.text() == "$7,777.00"
