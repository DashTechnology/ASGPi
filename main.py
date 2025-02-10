#!/usr/bin/env python3
"""
Main entry point for the Attendance Sign In/Sign Out System.
Initializes the PyQt application and starts the UI.
"""

import sys
from PyQt5 import QtWidgets
from ui import AttendanceApp


def main() -> None:
    """
    Main entry point for the application.
    Initializes and starts the PyQt application.
    """
    app = QtWidgets.QApplication(sys.argv)
    attendance_app = AttendanceApp()
    attendance_app.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
