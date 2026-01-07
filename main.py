#!/usr/bin/env python3
"""Personal Budget Manager - Main Entry Point"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from budget_app.views.main_window import MainWindow


def main():
    """Main application entry point"""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Personal Budget Manager")
    app.setOrganizationName("BudgetApp")
    app.setApplicationVersion("1.0.0")

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
