#!/usr/bin/env python3
"""
User interface module for the attendance system.
Implements the main window and UI components using PyQt5.
Optimized for Raspberry Pi 2 Model B.
"""

from datetime import datetime
from threading import Thread
import sys
from typing import Optional, Dict, Any
from PyQt5 import QtWidgets, QtCore, QtGui

from database_manager import DatabaseManager
from rfid_reader import RFIDReader
from registration_window import RegistrationWindow
import config


class AttendanceApp(QtWidgets.QMainWindow):
    """
    Main application window for the attendance system.
    Optimized for Raspberry Pi 2 Model B with resource management and error handling.
    """

    # Define a custom signal for RFID card detection
    card_detected = QtCore.pyqtSignal(str)

    def __init__(self) -> None:
        """
        Initializes the main window, sets up the UI, and starts the auto sign out timer.
        Implements resource-efficient initialization for Raspberry Pi.
        """
        super().__init__()

        # Set window to full screen
        self.showFullScreen()
        self.setStyleSheet("background-color: black; color: white;")
        # Hide the mouse cursor
        self.setCursor(QtCore.Qt.BlankCursor)

        # Track system state
        self.is_sleeping = False
        self.central_widget = None
        self.setup_ui()

        try:
            # Initialize components with error handling
            self.db_manager = DatabaseManager()
            self.rfid_reader = RFIDReader()
        except Exception as e:
            self._show_error_and_exit(f"Failed to initialize components: {str(e)}")
            return

        # Timer for checking auto sign out and sleep/wake state
        self.state_timer = QtCore.QTimer(self)
        self.state_timer.timeout.connect(self.check_system_state)
        self.state_timer.start(60000)  # Check every minute

        # Timer for updating date/time display
        self.datetime_timer = QtCore.QTimer(self)
        self.datetime_timer.timeout.connect(self.update_datetime)
        self.datetime_timer.start(1000)  # Update every second

        # Timer for clearing welcome message
        self.message_timer = QtCore.QTimer(self)
        self.message_timer.timeout.connect(self.clear_welcome_message)
        self.message_timer.setSingleShot(True)

        # Connect the card detected signal to the handler
        self.card_detected.connect(self.handle_tap)

        try:
            # Start RFID reader in a separate thread with error handling
            self.start_rfid_reader()
        except Exception as e:
            self._show_error_and_exit(f"Failed to start RFID reader: {str(e)}")
            return

        self.append_log("Application started. Waiting for RFID cards...")
        self.update_datetime()  # Initial datetime update
        self.check_system_state()  # Initial state check

    def setup_ui(self) -> None:
        """Sets up the UI components with responsive design."""
        # Get screen size for responsive design
        screen = QtWidgets.QApplication.primaryScreen()
        screen_size = screen.size()

        # Calculate base font sizes based on screen height
        title_size = int(
            screen_size.height() * 0.04
        )  # 4% of screen height (~24 pts for 600px)
        subtitle_size = int(
            screen_size.height() * 0.03
        )  # 3% of screen height (~18 pts)
        datetime_size = int(
            screen_size.height() * 0.02
        )  # 2% of screen height (~12 pts)
        info_size = int(screen_size.height() * 0.03)  # 3% of screen height (~18 pts)
        log_size = int(screen_size.height() * 0.015)  # 1.5% of screen height (~9 pts)
        footer_size = int(screen_size.height() * 0.02)  # 2% of screen height (~12 pts)

        # Create central widget and layout
        self.central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.central_widget)
        main_layout = QtWidgets.QVBoxLayout(self.central_widget)

        # Set responsive margins (2% of screen width/height)
        margin = int(min(screen_size.width(), screen_size.height()) * 0.02)
        main_layout.setContentsMargins(margin, margin, margin, margin)
        main_layout.setSpacing(
            int(margin * 0.5)
        )  # Reduced spacing between main elements

        # Header container with gradient background
        header_container = QtWidgets.QWidget()
        header_container.setStyleSheet(
            """
            QWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 rgba(0, 0, 0, 0.8),
                    stop: 1 rgba(0, 0, 0, 0.3)
                );
                border-radius: 15px;
                padding: 10px;
            }
        """
        )
        header_layout = QtWidgets.QVBoxLayout(header_container)
        header_layout.setSpacing(5)  # Reduced spacing between header elements

        # Title Section
        title_label = QtWidgets.QLabel("Associated Student Government", self)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_font = QtGui.QFont("Arial", title_size, QtGui.QFont.Bold)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QtWidgets.QLabel("Los Angeles City College", self)
        subtitle_label.setAlignment(QtCore.Qt.AlignCenter)
        subtitle_font = QtGui.QFont("Arial", subtitle_size)
        subtitle_label.setFont(subtitle_font)
        header_layout.addWidget(subtitle_label)

        # Date and Time Display
        self.datetime_label = QtWidgets.QLabel("", self)
        self.datetime_label.setAlignment(QtCore.Qt.AlignCenter)
        datetime_font = QtGui.QFont("Arial", datetime_size)
        self.datetime_label.setFont(datetime_font)
        self.datetime_label.setStyleSheet("color: #CCCCCC;")
        header_layout.addWidget(self.datetime_label)

        main_layout.addWidget(header_container)

        # Content container
        content_container = QtWidgets.QWidget()
        content_container.setStyleSheet(
            """
            QWidget {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 15px;
                padding: 15px;
            }
        """
        )
        content_layout = QtWidgets.QHBoxLayout(content_container)

        # Logo section with frame
        logo_container = QtWidgets.QFrame()
        logo_container.setStyleSheet(
            """
            QFrame {
                background: transparent;
                border-radius: 15px;
                padding: 10px;
            }
        """
        )
        logo_layout = QtWidgets.QVBoxLayout(logo_container)

        # Calculate logo size (40% of screen height)
        logo_size = int(screen_size.height() * 0.4)

        logo_label = QtWidgets.QLabel(self)
        logo_pixmap = QtGui.QPixmap("assets/ASG.png")
        scaled_pixmap = logo_pixmap.scaled(
            logo_size,
            logo_size,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        logo_label.setPixmap(scaled_pixmap)
        logo_label.setAlignment(QtCore.Qt.AlignCenter)
        logo_layout.addWidget(logo_label)
        content_layout.addWidget(logo_container)

        # Right panel container
        right_panel = QtWidgets.QVBoxLayout()
        right_panel.setSpacing(int(margin * 0.7))  # Reduced spacing in right panel

        # Welcome message
        self.info_label = QtWidgets.QLabel("", self)
        self.info_label.setAlignment(QtCore.Qt.AlignCenter)
        info_font = QtGui.QFont("Arial", info_size, QtGui.QFont.Bold)
        self.info_label.setFont(info_font)
        self.info_label.setStyleSheet("color: white; padding: 10px;")
        self.info_label.setWordWrap(True)
        right_panel.addWidget(self.info_label)

        # Log text area
        self.log_text = QtWidgets.QPlainTextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(100)
        log_font = QtGui.QFont("Monospace", log_size)
        log_font.setStyleHint(QtGui.QFont.TypeWriter)
        self.log_text.setFont(log_font)
        self.log_text.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 15px;
                color: white;
            }
        """
        )
        # Set height to 40% of screen height
        self.log_text.setMinimumHeight(
            int(
                screen_size.height() * 0.32
            )  # Reduced to 32% to make more room for footer
        )  # Reduced to 35% to make room for footer
        right_panel.addWidget(self.log_text)

        content_layout.addLayout(right_panel)
        content_layout.setStretch(0, 4)  # Logo takes 4 parts
        content_layout.setStretch(1, 6)  # Right panel takes 6 parts

        main_layout.addWidget(content_container)

        # Footer with Dash Tech credit
        footer_container = QtWidgets.QWidget()
        footer_container.setStyleSheet(
            """
            QWidget {
                background: rgba(0, 0, 0, 0.3);
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                margin: 5px 0px 2px 0px;
            }
            """
        )
        footer_container.setFixedHeight(25)  # Even smaller height
        footer_layout = QtWidgets.QHBoxLayout(footer_container)
        footer_layout.setContentsMargins(10, 0, 10, 0)
        footer_layout.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        footer_label = QtWidgets.QLabel("powered by Dash Technology", self)
        footer_font = QtGui.QFont("Arial", 11)  # Even smaller font size
        footer_font.setItalic(True)
        footer_label.setFont(footer_font)
        footer_label.setStyleSheet(
            """
            color: rgba(255, 255, 255, 0.8);
            """
        )

        # Make the label clickable
        footer_label.setCursor(QtCore.Qt.PointingHandCursor)
        footer_label.mousePressEvent = self.show_registration_window
        footer_layout.addWidget(footer_label)

        main_layout.addWidget(footer_container)

        # Set layout stretching
        main_layout.setStretch(0, 2)  # Header takes 2 parts
        main_layout.setStretch(1, 5)  # Content takes 5 parts (reduced from 6)
        main_layout.setStretch(2, 0)  # Footer fixed height

    def _show_error_and_exit(self, message: str) -> None:
        """
        Shows a critical error message and exits the application.

        @param message: The error message to display
        """
        QtWidgets.QMessageBox.critical(self, "Critical Error", message)
        sys.exit(1)

    def _on_card_detected(self, card_id: str) -> None:
        """
        Callback function for RFID card detection.
        Emits the card_detected signal to be handled in the main thread.

        @param card_id: The detected card's ID
        """
        if card_id:  # Only emit if card_id is valid
            self.card_detected.emit(card_id)

    def handle_tap(self, rfid_tag: str) -> None:
        """
        Handles a tap event from the RFID reader.
        Determines whether to sign in or sign out based on the current active session.

        @param rfid_tag: The RFID card identifier
        """
        if self.is_sleeping:
            return  # Ignore card taps while system is sleeping

        if not rfid_tag:
            self.show_message("Error: Invalid card read.", error=True)
            return

        try:
            # Get member information
            member = self.db_manager.get_member_by_rfid(rfid_tag)
            if not member:
                self.show_message("Error: Unknown RFID card.", error=True)
                return

            # Get member's position information
            position_name = member["position"]
            elected_name = member["name"]
            first_name = member["name"].split(" ")[0]
            current_time = datetime.now().strftime("%I:%M %p")

            # Check if an active session exists for this member
            active_session = self.db_manager.get_active_session(member["id"])
            if active_session is None:
                # No active session; record sign in
                log_entry = self.db_manager.sign_in(rfid_tag)
                if log_entry is not None:
                    if isinstance(log_entry, dict):
                        if log_entry.get("error") == "after_hours":
                            self.show_message(
                                "Sign-in not allowed after 7:00 PM", error=True
                            )
                            return
                        elif log_entry.get("error") == "before_hours":
                            self.show_message(
                                "Sign-in not allowed before 7:30 AM", error=True
                            )
                            return
                    self.show_message(
                        f"Welcome {first_name}! Signed in at {current_time}"
                    )
                    self.append_log(
                        f"Sign in recorded for {elected_name} ({position_name}).",
                        is_sign_in=True,
                    )
                else:
                    self.show_message("Error recording sign in.", error=True)
            else:
                # Active session exists; record sign out
                duration = self.db_manager.sign_out(rfid_tag)
                if duration is not None:
                    self.show_message(
                        f"Good bye, {first_name}! Signed out at {current_time}"
                    )
                    self.append_log(
                        f"Sign out recorded for {elected_name} ({position_name}). "
                        f"Duration: {duration:.2f} hours.",
                        is_sign_out=True,
                    )
                else:
                    self.show_message("Error recording sign out.", error=True)
        except Exception as e:
            self.show_message(f"Error processing card: {str(e)}", error=True)

    def check_system_state(self) -> None:
        """
        Checks if it's time to sleep or wake up the system.
        Also handles auto sign out.
        """
        current_time = datetime.now()
        current_hour = current_time.hour
        current_minute = current_time.minute

        # Check if it's before start time (7:30 AM) or after sleep time (7:30 PM)
        if not config.DEV_MODE and (
            (
                current_hour < config.START_TIME_HOUR
                or (
                    current_hour == config.START_TIME_HOUR
                    and current_minute < config.START_TIME_MINUTE
                )
            )
            or (
                current_hour == config.SLEEP_TIME_HOUR
                and current_minute >= config.SLEEP_TIME_MINUTE
            )
            or current_hour > config.SLEEP_TIME_HOUR
        ):
            if not self.is_sleeping:
                self.sleep_system()
        else:
            if self.is_sleeping:
                self.wake_system()

        # Check for auto sign out (only when awake)
        if not self.is_sleeping and current_hour >= config.AUTO_SIGNOUT_HOUR:
            result = self.db_manager.auto_sign_out()
            if result and result.get("message"):
                self.append_log(result["message"], is_sign_out=True)

    def sleep_system(self) -> None:
        """Puts the system to sleep."""
        self.is_sleeping = True
        self.central_widget.setVisible(False)
        self.setStyleSheet("background-color: black;")
        self.append_log("System entering sleep mode until 8:00 AM.")

        # Stop the RFID reader
        if hasattr(self, "rfid_reader"):
            self.rfid_reader.stop_reading()
            if hasattr(self, "reader_thread") and self.reader_thread.is_alive():
                self.reader_thread.join(timeout=1.0)

    def wake_system(self) -> None:
        """Wakes up the system."""
        self.is_sleeping = False
        self.central_widget.setVisible(True)
        self.setStyleSheet("background-color: black; color: white;")
        self.append_log("Good morning! System resuming normal operation.")

        # Restart the RFID reader
        self.start_rfid_reader()

    def start_rfid_reader(self) -> None:
        """Starts the RFID reader in a separate thread."""
        self.reader_thread = Thread(
            target=self.rfid_reader.start_reading,
            args=(self._on_card_detected,),
            daemon=True,
        )
        self.reader_thread.start()

    def update_datetime(self) -> None:
        """Updates the date and time display."""
        current_datetime = datetime.now()
        formatted_datetime = current_datetime.strftime("%B %d, %Y %I:%M:%S %p")
        self.datetime_label.setText(formatted_datetime)

    def clear_welcome_message(self) -> None:
        """Clears the welcome/goodbye message after timeout."""
        self.info_label.clear()

    def show_message(self, message: str, error: bool = False) -> None:
        """
        Displays a message in the info label.
        Optimized for Raspberry Pi display visibility.

        @param message: Message to display.
        @param error: Flag to indicate error (displays in red if True).
        """
        style = (
            "color: red; font-size: 16pt;"
            if error
            else "color: white; font-size: 16pt;"
        )
        self.info_label.setStyleSheet(style)
        self.info_label.setText(message)

        # Start the timer to clear the message after 5 seconds
        self.message_timer.start(5000)  # Increased from 3000 to 5000 milliseconds

    def append_log(
        self, log_message: str, is_sign_in: bool = False, is_sign_out: bool = False
    ) -> None:
        """
        Appends a log message with a timestamp to the log text area.
        Implements memory-efficient logging for Raspberry Pi.

        @param log_message: The log message to append.
        @param is_sign_in: Flag to indicate if this is a sign-in message (green).
        @param is_sign_out: Flag to indicate if this is a sign-out message (red).
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Create HTML formatted text with color
            if is_sign_in:
                colored_text = (
                    f'<span style="color: #00FF00;">[{timestamp}] {log_message}</span>'
                )
            elif is_sign_out:
                colored_text = (
                    f'<span style="color: #FF0000;">[{timestamp}] {log_message}</span>'
                )
            else:
                colored_text = f"[{timestamp}] {log_message}"

            # Append the text with HTML formatting
            cursor = self.log_text.textCursor()
            cursor.movePosition(QtGui.QTextCursor.End)
            cursor.insertHtml(colored_text + "<br>")

            # Ensure the latest message is visible
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )

            # Process events to prevent UI freezing on RPi
            QtWidgets.QApplication.processEvents()
        except Exception as e:
            print(f"Error appending log: {str(e)}")

    def show_registration_window(
        self, event: Optional[QtGui.QMouseEvent] = None
    ) -> None:
        """
        Shows the RFID card registration window.
        This is a secret function triggered by clicking the footer text.
        """
        try:
            # Stop the current RFID reader
            if hasattr(self, "rfid_reader"):
                self.rfid_reader.stop_reading()
                if hasattr(self, "reader_thread"):
                    self.reader_thread.join(timeout=1.0)

            # Show registration dialog with the same RFID reader instance
            registration = RegistrationWindow(parent=self, rfid_reader=self.rfid_reader)

            # Ensure the registration window is properly displayed
            registration.setWindowModality(QtCore.Qt.ApplicationModal)
            registration.show()  # Show the window first
            registration.raise_()  # Raise it to the top
            registration.activateWindow()  # Make it the active window

            result = registration.exec_()

            # Reinitialize and restart the RFID reader
            if hasattr(self, "rfid_reader"):
                self.rfid_reader.reinitialize()
                self.start_rfid_reader()

            if result == QtWidgets.QDialog.Accepted:
                self.append_log("New member registration completed successfully.")

        except Exception as e:
            self._show_error_and_exit(f"Error during registration: {str(e)}")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """
        Handle the window close event.
        Ensures proper cleanup of resources on Raspberry Pi.

        @param event: The close event
        """
        try:
            # Stop the RFID reader
            if hasattr(self, "rfid_reader"):
                self.rfid_reader.stop_reading()

            # Wait for reader thread to finish
            if hasattr(self, "reader_thread") and self.reader_thread.is_alive():
                self.reader_thread.join(timeout=1.0)

            event.accept()
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
            event.accept()  # Still accept the event to ensure application closes
