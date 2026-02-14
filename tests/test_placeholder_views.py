"""Tests for placeholder views (PDF Import, Bank API)"""

import pytest


class TestPDFImportView:
    """Tests for PDFImportView placeholder"""

    def test_creates_without_error(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        assert view is not None

    def test_has_layout(self, qtbot):
        from budget_app.views.pdf_import_view import PDFImportView
        view = PDFImportView()
        qtbot.addWidget(view)
        assert view.layout() is not None


class TestBankAPIView:
    """Tests for BankAPIView placeholder"""

    def test_creates_without_error(self, qtbot):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        assert view is not None

    def test_has_layout(self, qtbot):
        from budget_app.views.bank_api_view import BankAPIView
        view = BankAPIView()
        qtbot.addWidget(view)
        assert view.layout() is not None
