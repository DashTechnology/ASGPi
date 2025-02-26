#!/usr/bin/env python3
"""
Hours checking window module.
Allows users to check their accumulated hours by tapping their RFID card.
"""

from datetime import datetime, timedelta
from threading import Thread
from typing import Optional
from PyQt5 import QtWidgets, QtCore, QtGui

from database_manager import DatabaseManager
from rfid_reader import RFIDReader


class CheckHoursWindow(QtWidgets.QDialog):
    """
    Window for checking accumulated hours via RFID card tap.
    Shows total hours and current session details if signed in.
    """

    # Define a custom signal for RFID card detection
    card_detected = QtCore.pyqtSignal(str)

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        rfid_reader: Optional[RFIDReader] = None,
    ) -> None:
        """
        Initialize the check hours window with necessary components.

        @param parent: Optional parent widget
        @param rfid_reader: Optional existing RFID reader instance
        """
        super().__init__(parent)
        self.rfid_reader = rfid_reader

        # Set window properties for full screen
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setWindowState(QtCore.Qt.WindowFullScreen)
        self.setStyleSheet(
            """
            QDialog {
                background-color: black;
                color: white;
            }
            QLabel {
                color: white;
            }
        """
        )

        try:
            # Initialize database manager
            self.db_manager = DatabaseManager()
            if self.rfid_reader is None:
                self.rfid_reader = RFIDReader()

            self.setup_ui()

            # Connect the card detected signal to the handler
            self.card_detected.connect(self.handle_card_tap)

        except Exception as e:
            self._show_error_and_close(f"Failed to initialize components: {str(e)}")
            return

        # Start RFID reader
        try:
            self.reader_thread = Thread(
                target=self.rfid_reader.start_reading,
                args=(self._on_card_detected,),
                daemon=True,
            )
            self.reader_thread.start()
        except Exception as e:
            self._show_error_and_close(f"Failed to start RFID reader: {str(e)}")
            return

    def setup_ui(self) -> None:
        """Sets up the UI components with responsive design."""
        # Get screen size for responsive design
        screen = QtWidgets.QApplication.primaryScreen()
        screen_size = screen.size()

        # Calculate base font sizes based on screen height
        title_size = int(screen_size.height() * 0.04)  # 4% of screen height
        info_size = int(screen_size.height() * 0.03)  # 3% of screen height
        button_size = int(screen_size.height() * 0.025)  # 2.5% of screen height

        # Create main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        margin = int(min(screen_size.width(), screen_size.height()) * 0.02)
        main_layout.setContentsMargins(margin, margin, margin, margin)
        main_layout.setSpacing(margin)

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
                padding: 20px;
            }
        """
        )
        header_layout = QtWidgets.QVBoxLayout(header_container)

        # Title
        title_label = QtWidgets.QLabel("Check Your Hours", self)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_font = QtGui.QFont("Arial", title_size, QtGui.QFont.Bold)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QtWidgets.QLabel(
            "Tap your RFID card to check your hours", self
        )
        subtitle_label.setAlignment(QtCore.Qt.AlignCenter)
        subtitle_font = QtGui.QFont("Arial", info_size)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setStyleSheet("color: #CCCCCC;")
        header_layout.addWidget(subtitle_label)

        main_layout.addWidget(header_container)

        # Content container
        content_container = QtWidgets.QWidget()
        content_container.setStyleSheet(
            """
            QWidget {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 15px;
                padding: 20px;
            }
        """
        )
        content_layout = QtWidgets.QVBoxLayout(content_container)

        # Info display
        self.info_label = QtWidgets.QLabel("", self)
        self.info_label.setAlignment(QtCore.Qt.AlignCenter)
        self.info_label.setFont(QtGui.QFont("Arial", info_size))
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: white;")
        content_layout.addWidget(self.info_label)

        main_layout.addWidget(content_container)

        # Button container
        button_container = QtWidgets.QWidget()
        button_layout = QtWidgets.QHBoxLayout(button_container)

        # Close button
        close_btn = QtWidgets.QPushButton("Close", self)
        close_btn.setFont(QtGui.QFont("Arial", button_size))
        close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                padding: 15px 30px;
                color: white;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """
        )
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        main_layout.addWidget(button_container)

        # Set layout stretching
        main_layout.setStretch(0, 1)  # Header takes 1 part
        main_layout.setStretch(1, 4)  # Content takes 4 parts
        main_layout.setStretch(2, 1)  # Button container takes 1 part

    def _show_error_and_close(self, message: str) -> None:
        """
        Shows an error message and closes the window.

        @param message: The error message to display
        """
        QtWidgets.QMessageBox.critical(self, "Error", message)
        self.reject()

    def _on_card_detected(self, card_id: str) -> None:
        """
        Callback function for RFID card detection.

        @param card_id: The detected card's ID
        """
        if card_id:
            self.card_detected.emit(card_id)

    def handle_card_tap(self, rfid_tag: str) -> None:
        """
        Handles a card tap event, displays the member's hours for the current week.

        @param rfid_tag: The RFID card identifier
        """
        try:
            # Get member information
            member = self.db_manager.get_member_by_rfid(rfid_tag)
            if not member:
                self.info_label.setText("Error: Unknown RFID card.")
                self.info_label.setStyleSheet("color: red;")
                return

            # Get active session if any
            active_session = self.db_manager.get_active_session(member["id"])

            # Get all sessions for the member from the current week
            # Get the start of the current week (Monday)
            current_date = datetime.now()
            start_of_week = current_date - timedelta(days=current_date.weekday())
            start_of_week = start_of_week.replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            # Query only sessions from this week
            response = (
                self.db_manager.supabase.table("asg_logs")
                .select("*")
                .eq("user_id", member["id"])
                .gte("sign_in_time", start_of_week.isoformat() + "Z")
                .order("sign_in_time", desc=True)
                .execute()
            )

            if not response.data and not active_session:
                self.info_label.setText(
                    f"No hours recorded this week for {member['name']}"
                )
                return

            # Calculate current week hours
            current_week_hours = 0.0

            for session in response.data:
                # If duration is None, calculate it from sign_in_time to now (active session)
                duration = session.get("duration")
                if duration is None:
                    try:
                        sign_in_time = datetime.fromisoformat(
                            session["sign_in_time"].replace("Z", "+00:00")
                        )
                        current_time = datetime.now(sign_in_time.tzinfo)
                        duration = (
                            current_time - sign_in_time
                        ).total_seconds() / 3600.0
                    except (ValueError, TypeError, KeyError) as e:
                        print(f"Error calculating session duration: {e}")
                        continue

                try:
                    current_week_hours += float(duration)
                except (ValueError, TypeError):
                    print(f"Invalid duration value in session: {duration}")
                    continue

            # Add current active session duration if exists
            current_duration = 0.0
            if active_session:
                try:
                    sign_in_time = datetime.fromisoformat(
                        active_session["sign_in_time"].replace("Z", "+00:00")
                    )
                    current_time = datetime.now(sign_in_time.tzinfo)
                    current_duration = (
                        current_time - sign_in_time
                    ).total_seconds() / 3600.0

                    if sign_in_time >= start_of_week:
                        current_week_hours += current_duration
                except (ValueError, TypeError, KeyError) as e:
                    print(f"Error calculating current session duration: {e}")
                    current_duration = 0.0

            # Format the display message
            message_parts = []
            message_parts.append(f"Member: {member['name']} ({member['position']})")
            message_parts.append(f"Current Week Hours: {current_week_hours:.2f}")

            if active_session and current_duration > 0:
                message_parts.append("\nCurrent Session:")
                message_parts.append(
                    f"Signed in at: {sign_in_time.strftime('%I:%M %p')}"
                )
                message_parts.append(f"Current duration: {current_duration:.2f} hours")

            self.info_label.setText("\n".join(message_parts))
            self.info_label.setStyleSheet("color: white;")

        except Exception as e:
            self.info_label.setText(f"Error checking hours: {str(e)}")
            self.info_label.setStyleSheet("color: red;")
            print(
                f"Detailed error in handle_card_tap: {str(e)}"
            )  # Add detailed logging

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """
        Handle the window close event.

        @param event: The close event
        """
        try:
            if hasattr(self, "rfid_reader"):
                self.rfid_reader.stop_reading()
            if hasattr(self, "reader_thread"):
                self.reader_thread.join(timeout=1.0)

            # Ensure parent window stays in full screen and focused
            if self.parent():
                self.parent().showFullScreen()
                self.parent().raise_()
                self.parent().activateWindow()

            event.accept()
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
            event.accept()  # Still accept the event to ensure window closes
