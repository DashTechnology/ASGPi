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
from discord_webhook import DiscordNotifier


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
        self.is_processing_tap = False
        self.is_showing_message = False  # Track if we're showing a message
        self.last_auto_signout_date = None  # Track the date of last auto sign-out
        self.auto_signout_attempted = (
            False  # Track if auto sign-out was attempted this hour
        )
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
        self.state_timer.start(30000)  # Check every 30 seconds for more accuracy

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
        )  # 3% of screen height (increased from 2.5%)
        datetime_size = int(
            screen_size.height() * 0.022
        )  # 2.2% of screen height (increased from 1.8%)
        info_size = int(screen_size.height() * 0.03)  # 3% of screen height (~18 pts)
        log_size = int(screen_size.height() * 0.025)  # 2.5% of screen height (~15 pts)
        footer_size = int(screen_size.height() * 0.02)  # 2% of screen height (~12 pts)

        # Create central widget and layout
        self.central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.central_widget)
        main_layout = QtWidgets.QVBoxLayout(self.central_widget)

        # Create status circle
        self.status_circle = QtWidgets.QWidget(self)
        self.status_circle.setFixedSize(150, 150)  # Increased circle size
        self.status_circle.setStyleSheet(
            """
            QWidget {
                background-color: rgba(128, 128, 128, 0.5);
                border-radius: 75px;
                border: 2px solid rgba(255, 255, 255, 0.2);
            }
            """
        )

        # Create breathing animation
        self.breath_animation = QtCore.QPropertyAnimation(self.status_circle, b"size")
        self.breath_animation.setDuration(2000)  # 2 seconds for one breath cycle
        self.breath_animation.setLoopCount(-1)  # Infinite loop
        self.breath_animation.setStartValue(QtCore.QSize(140, 140))
        self.breath_animation.setEndValue(QtCore.QSize(150, 150))
        self.breath_animation.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
        self.breath_animation.start()

        # Add the status circle to a container to position it
        circle_container = QtWidgets.QWidget()
        circle_container.setFixedSize(170, 170)  # Slightly larger than the circle
        circle_layout = QtWidgets.QVBoxLayout(circle_container)
        circle_layout.addWidget(self.status_circle, 0, QtCore.Qt.AlignCenter)
        circle_layout.setContentsMargins(5, 5, 5, 5)

        # Set responsive margins (2% of screen width/height)
        margin = int(min(screen_size.width(), screen_size.height()) * 0.02)
        main_layout.setContentsMargins(margin, margin, margin, margin)
        main_layout.setSpacing(
            int(margin * 0.5)
        )  # Reduced spacing between main elements

        # Create a horizontal layout for the circle and header
        top_container = QtWidgets.QHBoxLayout()
        top_container.addWidget(
            circle_container, 0, QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop
        )

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
        header_layout.setSpacing(2)  # Reduced spacing between header elements from 5

        # Title container with logo
        title_container = QtWidgets.QWidget()
        title_layout = QtWidgets.QHBoxLayout(title_container)
        title_layout.setSpacing(20)  # Space between logo and title
        title_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins

        # Add ASG logo
        logo_label = QtWidgets.QLabel(self)
        logo_size = int(
            screen_size.height() * 0.18
        )  # 18% of screen height (increased from 15%)
        logo_pixmap = QtGui.QPixmap("assets/ASG.png")
        scaled_pixmap = logo_pixmap.scaled(
            logo_size,
            logo_size,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        logo_label.setPixmap(scaled_pixmap)
        logo_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        logo_label.setStyleSheet("padding-right: 10px;")  # Reduced padding
        title_layout.addWidget(logo_label)

        # Create a container for title and subtitle
        text_container = QtWidgets.QWidget()
        text_layout = QtWidgets.QVBoxLayout(text_container)
        text_layout.setSpacing(0)  # No spacing between elements
        text_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins

        # Title text
        title_label = QtWidgets.QLabel("Associated Student Government", self)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_font = QtGui.QFont("Arial", title_size, QtGui.QFont.Bold)
        title_label.setFont(title_font)
        text_layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QtWidgets.QLabel("Los Angeles City College", self)
        subtitle_label.setAlignment(QtCore.Qt.AlignCenter)
        subtitle_font = QtGui.QFont("Arial", subtitle_size)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setStyleSheet("margin-top: -5px;")  # Negative margin to pull up
        text_layout.addWidget(subtitle_label)

        # Add the text container to the title layout
        title_layout.addWidget(text_container)
        header_layout.addWidget(title_container)

        top_container.addWidget(header_container)
        top_container.setStretch(0, 1)  # Circle takes 1 part
        top_container.setStretch(1, 9)  # Header takes 9 parts
        main_layout.addLayout(top_container)

        # Welcome/Goodbye message container
        message_container = QtWidgets.QWidget()
        message_container.setFixedHeight(80)  # Fixed height to prevent layout changes
        message_container.setStyleSheet(
            """
            QWidget {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 15px;
                margin: 5px 0;
            }
            """
        )
        message_layout = QtWidgets.QVBoxLayout(message_container)
        message_layout.setContentsMargins(10, 5, 10, 5)

        # Info label for welcome/goodbye messages and datetime
        self.info_label = QtWidgets.QLabel("", self)
        self.info_label.setAlignment(QtCore.Qt.AlignCenter)
        info_font = QtGui.QFont("Arial", info_size, QtGui.QFont.Bold)
        self.info_label.setFont(info_font)
        self.info_label.setStyleSheet("color: white;")
        self.info_label.setWordWrap(True)
        message_layout.addWidget(self.info_label)
        message_container.show()  # Always show the container since it will display datetime
        self.message_container = message_container

        main_layout.addWidget(message_container)

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
        content_layout = QtWidgets.QVBoxLayout(content_container)

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
        content_layout.addWidget(self.log_text)

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
        footer_container.setFixedHeight(
            35
        )  # Increased height for better button visibility
        footer_layout = QtWidgets.QHBoxLayout(footer_container)
        footer_layout.setContentsMargins(10, 5, 10, 5)  # Added vertical padding

        # Add Check Hours button
        check_hours_btn = QtWidgets.QPushButton("Check Hours", self)
        check_hours_btn.setFont(QtGui.QFont("Arial", 11))
        check_hours_btn.setFixedWidth(120)  # Fixed width to prevent squishing
        check_hours_btn.setFixedHeight(25)  # Fixed height for better proportions
        check_hours_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                padding: 2px 10px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
            """
        )
        check_hours_btn.clicked.connect(self.show_check_hours_window)
        footer_layout.addWidget(check_hours_btn)

        # Add Upload Logs button
        upload_logs_btn = QtWidgets.QPushButton("Upload Logs", self)
        upload_logs_btn.setFont(QtGui.QFont("Arial", 11))
        upload_logs_btn.setFixedWidth(120)  # Fixed width to prevent squishing
        upload_logs_btn.setFixedHeight(25)  # Fixed height for better proportions
        upload_logs_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                padding: 2px 10px;
                color: white;
                font-weight: bold;
                margin-left: 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
            """
        )
        upload_logs_btn.clicked.connect(self.upload_logs)
        footer_layout.addWidget(upload_logs_btn)

        # Add spacer to push Dash Tech credit to the right
        footer_layout.addStretch()

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

    def set_circle_color(self, color: str) -> None:
        """
        Sets the status circle color.

        @param color: Color to set the circle to (e.g., 'grey', 'green', 'red')
        """
        color_map = {
            "grey": "rgba(128, 128, 128, 0.5)",
            "green": "rgba(0, 255, 0, 0.5)",
            "red": "rgba(255, 0, 0, 0.5)",
        }
        self.status_circle.setStyleSheet(
            f"""
            QWidget {{
                background-color: {color_map.get(color, color_map['grey'])};
                border-radius: 75px;
                border: 2px solid rgba(255, 255, 255, 0.2);
            }}
            """
        )

    def reset_circle_color(self) -> None:
        """Resets the status circle color to grey after delay."""
        self.set_circle_color("grey")
        self.is_processing_tap = False

    def handle_tap(self, rfid_tag: str) -> None:
        """
        Handles a tap event from the RFID reader.
        Determines whether to sign in or sign out based on the current active session.

        @param rfid_tag: The RFID card identifier
        """
        if self.is_processing_tap:
            return  # Ignore taps while processing

        self.is_processing_tap = True

        if self.is_sleeping:
            return  # Ignore card taps while system is sleeping

        if not rfid_tag:
            self.show_message("Error: Invalid card read.", error=True)
            self.set_circle_color("red")
            QtCore.QTimer.singleShot(
                config.MESSAGE_DISPLAY_DURATION, self.reset_circle_color
            )
            return

        try:
            # Get member information
            member = self.db_manager.get_member_by_rfid(rfid_tag)
            if not member:
                self.show_message("Error: Unknown RFID card.", error=True)
                self.set_circle_color("red")
                QtCore.QTimer.singleShot(
                    config.MESSAGE_DISPLAY_DURATION, self.reset_circle_color
                )
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
                            self.set_circle_color("red")
                            QtCore.QTimer.singleShot(
                                config.MESSAGE_DISPLAY_DURATION, self.reset_circle_color
                            )
                            return
                        elif log_entry.get("error") == "before_hours":
                            self.show_message(
                                "Sign-in not allowed before 7:30 AM", error=True
                            )
                            self.set_circle_color("red")
                            QtCore.QTimer.singleShot(
                                config.MESSAGE_DISPLAY_DURATION, self.reset_circle_color
                            )
                            return
                    self.show_message(
                        f"Welcome {first_name}! Signed in at {current_time}"
                    )
                    self.set_circle_color("green")
                    self.append_log(
                        f"Sign in recorded for {elected_name} ({position_name}).",
                        is_sign_in=True,
                    )

                    # Send Discord notification for sign-in
                    if config.DISCORD_WEBHOOK_ENABLED:
                        threading.Thread(
                            target=DiscordNotifier.send_tap_in_notification,
                            args=(member,),
                            daemon=True,
                        ).start()
                else:
                    self.show_message("Error recording sign in.", error=True)
                    self.set_circle_color("red")
            else:
                # Active session exists; record sign out
                duration = self.db_manager.sign_out(rfid_tag)
                if duration is not None:
                    self.show_message(
                        f"Good bye, {first_name}! Signed out at {current_time}"
                    )
                    self.set_circle_color("red")
                    self.append_log(
                        f"Sign out recorded for {elected_name} ({position_name}). "
                        f"Duration: {duration:.2f} hours.",
                        is_sign_out=True,
                    )

                    # Send Discord notification for sign-out
                    if config.DISCORD_WEBHOOK_ENABLED:
                        threading.Thread(
                            target=DiscordNotifier.send_tap_out_notification,
                            args=(member, duration),
                            daemon=True,
                        ).start()
                else:
                    self.show_message("Error recording sign out.", error=True)
                    self.set_circle_color("red")

            # Reset circle color after the configured duration
            QtCore.QTimer.singleShot(
                config.MESSAGE_DISPLAY_DURATION, self.reset_circle_color
            )

        except Exception as e:
            self.show_message(f"Error processing card: {str(e)}", error=True)
            self.set_circle_color("red")
            QtCore.QTimer.singleShot(
                config.MESSAGE_DISPLAY_DURATION, self.reset_circle_color
            )

    def check_system_state(self) -> None:
        """
        Checks if it's time to sleep or wake up the system.
        Also handles auto sign out at the configured time.
        System sleeps during weekends (Saturday and Sunday).
        """
        current_time = datetime.now()
        current_hour = current_time.hour
        current_minute = current_time.minute
        current_date = current_time.date()
        current_weekday = current_time.weekday()  # Monday is 0, Sunday is 6

        # Reset auto sign-out attempt flag at the start of each hour
        if current_minute == 0 and self.auto_signout_attempted:
            self.auto_signout_attempted = False
            self.append_log("Reset auto sign-out attempt flag for new hour")

        # Check if it's a weekend (Saturday = 5, Sunday = 6)
        is_weekend = current_weekday in (5, 6)

        # Check if system should sleep
        should_sleep = False
        if not config.DEV_MODE:
            if is_weekend:
                should_sleep = True
                if not self.is_sleeping:
                    self.append_log("System entering weekend sleep mode.")
            else:
                # Regular weekday sleep check
                should_sleep = (
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
                )

        # Apply sleep state
        if should_sleep:
            if not self.is_sleeping:
                self.sleep_system()
        else:
            if self.is_sleeping:
                if is_weekend:
                    self.append_log("System resuming operation after weekend.")
                self.wake_system()

        # Check for auto sign out (only when awake and at exactly the configured hour)
        if (
            not self.is_sleeping
            and current_hour == config.AUTO_SIGNOUT_HOUR
            and current_minute == 0
            and not self.auto_signout_attempted
            and (
                self.last_auto_signout_date is None
                or self.last_auto_signout_date != current_date
            )
        ):
            self.append_log(
                f"Attempting auto sign-out at {current_time.strftime('%I:%M %p')}"
            )
            self.auto_signout_attempted = True

            result = self.db_manager.auto_sign_out()
            if result:
                if result.get("members"):
                    members_list = ", ".join(result["members"])
                    self.append_log(
                        f"Auto sign-out successful for: {members_list}",
                        is_sign_out=True,
                    )
                else:
                    self.append_log(
                        "Auto sign-out completed - no active sessions found"
                    )

                self.last_auto_signout_date = current_date

                # Upload system logs after auto sign-out
                logs = self.log_text.toPlainText()
                if logs.strip():
                    if self.db_manager.upload_system_logs(logs):
                        self.log_text.clear()
                        self.append_log(
                            "System logs were automatically uploaded after auto sign-out."
                        )
                    else:
                        self.append_log(
                            "Failed to upload system logs after auto sign-out.",
                            error=True,
                        )
            else:
                self.append_log(
                    "Auto sign-out attempt failed or no members to sign out",
                    is_sign_out=True,
                )

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
        """Updates the date and time display in the info label when no message is shown."""
        if not self.is_showing_message:  # Only update if no message is being shown
            current_datetime = datetime.now()
            formatted_datetime = current_datetime.strftime("%B %d, %Y %I:%M:%S %p")
            self.info_label.setText(f"{formatted_datetime}")
            self.info_label.setStyleSheet("color: #CCCCCC; font-size: 16pt;")

    def show_message(self, message: str, error: bool = False) -> None:
        """
        Displays a message in the info label.
        Optimized for Raspberry Pi display visibility.

        @param message: Message to display.
        @param error: Flag to indicate error (displays in red if True).
        """
        # Stop any existing timer to prevent conflicts
        self.message_timer.stop()
        self.is_showing_message = True  # Set flag to prevent datetime updates

        style = (
            "color: red; font-size: 16pt;"
            if error
            else "color: white; font-size: 16pt;"
        )
        self.info_label.setStyleSheet(style)
        self.info_label.setText(message)

        # Start the timer to clear the message after the configured duration
        self.message_timer.start(config.MESSAGE_DISPLAY_DURATION)

    def clear_welcome_message(self) -> None:
        """Clears the welcome/goodbye message and shows the current time."""
        self.is_showing_message = False  # Clear flag to allow datetime updates
        self.info_label.clear()  # Clear the current message first
        self.update_datetime()  # Show current time after clearing message

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

    def show_check_hours_window(self) -> None:
        """
        Shows the hours checking window.
        This allows members to check their accumulated hours by tapping their RFID card.
        """
        try:
            # Stop the current RFID reader
            if hasattr(self, "rfid_reader"):
                self.rfid_reader.stop_reading()
                if hasattr(self, "reader_thread"):
                    self.reader_thread.join(timeout=1.0)

            # Import here to avoid circular imports
            from check_window import CheckHoursWindow

            # Show check hours dialog with the same RFID reader instance
            check_window = CheckHoursWindow(parent=self, rfid_reader=self.rfid_reader)
            check_window.setWindowModality(QtCore.Qt.ApplicationModal)
            check_window.show()
            check_window.raise_()
            check_window.activateWindow()

            result = check_window.exec_()

            # Reinitialize and restart the RFID reader
            if hasattr(self, "rfid_reader"):
                self.rfid_reader.reinitialize()
                self.start_rfid_reader()

        except Exception as e:
            self._show_error_and_exit(f"Error opening check hours window: {str(e)}")

    def upload_logs(self) -> None:
        """
        Uploads the current system logs to the database and clears the log display.
        Shows a success or error message based on the upload result.
        """
        try:
            # Get the current logs from the text area
            logs = self.log_text.toPlainText()

            if not logs.strip():
                self.show_message("No logs to upload.", error=True)
                return

            # Upload the logs to the database
            success = self.db_manager.upload_system_logs(logs)

            if success:
                # Clear the log text area
                self.log_text.clear()
                self.show_message("Logs uploaded successfully!")
                self.append_log(
                    "System logs were uploaded to the database and cleared."
                )
            else:
                self.show_message("Failed to upload logs.", error=True)

        except Exception as e:
            self.show_message(f"Error uploading logs: {str(e)}", error=True)

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
