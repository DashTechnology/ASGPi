#!/usr/bin/env python3
"""
RFID card registration window module.
Handles the registration of RFID cards to ASG positions.
"""

from typing import Optional, Dict, Any
from PyQt5 import QtWidgets, QtCore, QtGui
from database_manager import DatabaseManager
from rfid_reader import RFIDReader
from threading import Thread


class RegistrationWindow(QtWidgets.QDialog):
    """
    Window for registering RFID cards to ASG positions.
    Provides a user interface for assigning RFID cards to positions.
    """

    # Define a custom signal for RFID card detection.
    card_detected = QtCore.pyqtSignal(str)

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        rfid_reader: Optional[RFIDReader] = None,
    ) -> None:
        """
        Initialize the registration window with necessary components.

        @param parent: Optional parent widget.
        @param rfid_reader: Optional existing RFID reader instance.
        """
        super().__init__(parent)
        self.rfid_reader = rfid_reader  # Store the RFID reader first

        # Set window properties for full screen
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setWindowState(QtCore.Qt.WindowFullScreen)
        self.setStyleSheet(
            """
            QDialog {
                background-color: black;
                color: white;
            }
            QLabel, QCheckBox, QPushButton, QComboBox {
                color: white;
            }
        """
        )

        try:
            # Initialize components
            self.db_manager = DatabaseManager()
            if self.rfid_reader is None:
                self.rfid_reader = RFIDReader()
            self.current_rfid: Optional[str] = None
            self.positions = self.db_manager.get_positions()

            if not self.positions:
                self._show_error_and_close("No positions retrieved from the database.")
                return

            self.setup_ui()

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

        # Ensure the window is visible and on top
        self.raise_()
        self.activateWindow()

    def setup_ui(self) -> None:
        """Sets up the UI components with responsive design."""
        # Get screen size for responsive design
        screen = QtWidgets.QApplication.primaryScreen()
        screen_size = screen.size()

        # Calculate base font sizes based on screen height
        title_size = int(screen_size.height() * 0.05)  # 5% of screen height
        label_size = int(screen_size.height() * 0.03)  # 3% of screen height
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

        # Title container for logo and text
        title_container = QtWidgets.QWidget()
        title_layout = QtWidgets.QHBoxLayout(title_container)
        title_layout.setAlignment(QtCore.Qt.AlignCenter)
        title_layout.setSpacing(margin)

        # Add logo
        logo_label = QtWidgets.QLabel(self)
        logo_size = int(screen_size.height() * 0.08)  # 8% of screen height
        logo_pixmap = QtGui.QPixmap("assets/ASG.png")
        scaled_pixmap = logo_pixmap.scaled(
            logo_size,
            logo_size,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        logo_label.setPixmap(scaled_pixmap)
        logo_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        title_layout.addWidget(logo_label)

        # Title
        title_label = QtWidgets.QLabel("RFID Card Registration", self)
        title_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        title_font = QtGui.QFont("Arial", title_size, QtGui.QFont.Bold)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)

        # Add the title container to the header
        header_layout.addWidget(title_container)
        header_layout.setAlignment(QtCore.Qt.AlignCenter)

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
            QComboBox {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                padding: 10px;
                color: white;
                min-height: 40px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                border: 2px solid white;
                width: 8px;
                height: 8px;
                background: transparent;
                border-width: 0 2px 2px 0;
                transform: rotate(45deg);
                margin-top: -5px;
            }
            QComboBox QAbstractItemView {
                background-color: rgb(30, 30, 30);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                selection-background-color: rgba(255, 255, 255, 0.2);
                selection-color: white;
                color: white;
                outline: none;
                padding: 5px;
            }
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
            QCheckBox {
                color: white;
                padding: 10px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """
        )
        content_layout = QtWidgets.QVBoxLayout(content_container)
        content_layout.setSpacing(margin * 2)

        # Position selection
        position_label = QtWidgets.QLabel("Select Position:", self)
        position_label.setFont(QtGui.QFont("Arial", label_size))
        content_layout.addWidget(position_label)

        self.position_combo = QtWidgets.QComboBox()
        self.position_combo.setFont(QtGui.QFont("Arial", label_size))
        for position in self.positions:
            self.position_combo.addItem(position, position)
        content_layout.addWidget(self.position_combo)

        # RFID status
        self.rfid_label = QtWidgets.QLabel("Tap an RFID card to register...", self)
        self.rfid_label.setFont(QtGui.QFont("Arial", label_size))
        self.rfid_label.setAlignment(QtCore.Qt.AlignCenter)
        self.rfid_label.setStyleSheet("padding: 20px;")
        content_layout.addWidget(self.rfid_label)

        # Override checkbox
        self.override_checkbox = QtWidgets.QCheckBox(
            "Override lost card registration", self
        )
        self.override_checkbox.setFont(QtGui.QFont("Arial", int(label_size * 0.8)))
        content_layout.addWidget(self.override_checkbox)

        # Buttons
        button_container = QtWidgets.QWidget()
        button_layout = QtWidgets.QHBoxLayout(button_container)
        button_layout.setSpacing(margin)

        self.register_btn = QtWidgets.QPushButton("Register")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")

        for btn in [self.register_btn, self.cancel_btn]:
            btn.setFont(QtGui.QFont("Arial", button_size))
            button_layout.addWidget(btn)

        content_layout.addWidget(button_container)
        main_layout.addWidget(content_container)

        # Footer
        footer_container = QtWidgets.QWidget()
        footer_container.setStyleSheet("background: transparent; padding: 5px;")
        footer_layout = QtWidgets.QHBoxLayout(footer_container)
        footer_layout.setAlignment(QtCore.Qt.AlignRight)

        footer_label = QtWidgets.QLabel("powered by Dash Technology", self)
        footer_font = QtGui.QFont("Arial", int(screen_size.height() * 0.015))
        footer_font.setItalic(True)
        footer_label.setFont(footer_font)
        footer_label.setStyleSheet("color: rgba(255, 255, 255, 0.5);")
        footer_layout.addWidget(footer_label)

        main_layout.addWidget(footer_container)

        # Set layout stretching
        main_layout.setStretch(0, 2)  # Header takes 2 parts
        main_layout.setStretch(1, 7)  # Content takes 7 parts
        main_layout.setStretch(2, 1)  # Footer takes 1 part

        # Connect signals
        self.register_btn.clicked.connect(self.register_card)
        self.cancel_btn.clicked.connect(self.close)
        self.card_detected.connect(self.handle_card_tap)

    def _show_error_and_close(self, message: str) -> None:
        """
        Shows an error message to the user and closes the window.

        @param message: The error message to display.
        """
        QtWidgets.QMessageBox.critical(self, "Error", message)
        self.reject()

    def _on_card_detected(self, card_id: str) -> None:
        """
        Callback function invoked when an RFID card is detected.

        @param card_id: The detected RFID card identifier.
        """
        if card_id:
            self.card_detected.emit(card_id)

    def handle_card_tap(self, rfid_tag: str) -> None:
        """
        Processes a tap event from the RFID reader.
        Checks if the RFID card is already registered unless override is enabled.

        @param rfid_tag: The RFID card identifier.
        """
        try:
            # Check if the card is already registered.
            existing_member = self.db_manager.get_member_by_rfid(rfid_tag)
            if existing_member and not self.override_checkbox.isChecked():
                QtWidgets.QMessageBox.warning(
                    self,
                    "Card Already Registered",
                    f"This card is already registered to position: {existing_member['position']}",
                )
                return
            elif existing_member and self.override_checkbox.isChecked():
                # Inform user about override.
                print(
                    f"Override enabled: proceeding with registration for card {rfid_tag} despite existing registration."
                )

            self.current_rfid = rfid_tag
            self.rfid_label.setText(f"Card detected: {rfid_tag}")
            self.rfid_label.setStyleSheet("color: green")
        except Exception as e:
            self.rfid_label.setText(f"Error reading card: {str(e)}")
            self.rfid_label.setStyleSheet("color: red")

    def register_card(self) -> None:
        """
        Registers the detected RFID card with the selected position.
        Queries the asg_members table for a member with the matching position
        and updates its RFID card value.

        @raise: Displays a warning or error message if validation fails or update is unsuccessful.
        """
        try:
            # Ensure an RFID card has been detected.
            if not self.current_rfid:
                QtWidgets.QMessageBox.warning(
                    self, "Validation Error", "Please tap an RFID card"
                )
                return

            # Retrieve the selected position from the combo box.
            selected_position = self.position_combo.currentData()
            if not selected_position:
                QtWidgets.QMessageBox.warning(
                    self, "Validation Error", "Please select a valid position."
                )
                return

            # Query the asg_members table for a member record matching the selected position.
            response = (
                self.db_manager.supabase.table("asg_members")
                .select("*")
                .eq("position", selected_position)
                .execute()
            )
            # Check if a member record exists for the selected position.
            if response.data and len(response.data) > 0:
                member_record: Dict[str, Any] = response.data[0]
                # Warn if an RFID card is already set for this member.
                if member_record.get("rfid_tag"):
                    if not self.override_checkbox.isChecked():
                        reply = QtWidgets.QMessageBox.question(
                            self,
                            "Overwrite Confirmation",
                            "This position already has an RFID card registered. Do you want to overwrite it?",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                        )
                        if reply == QtWidgets.QMessageBox.No:
                            return
                    else:
                        print(
                            f"Override enabled: overriding existing RFID registration for position {selected_position}."
                        )
                # Update the member record with the new RFID card.
                success = self.db_manager.update_member(
                    member_record["id"], {"rfid_tag": self.current_rfid}
                )
                if success:
                    QtWidgets.QMessageBox.information(
                        self,
                        "Success",
                        f"Successfully updated RFID card for position: {selected_position}",
                    )
                    # Stop RFID scanning and disconnect the card detection signal.
                    self.rfid_reader.stop_reading()
                    try:
                        self.card_detected.disconnect(self.handle_card_tap)
                    except Exception as disconn_error:
                        print(f"Error disconnecting signal: {disconn_error}")
                    self.accept()
                else:
                    QtWidgets.QMessageBox.critical(
                        self, "Error", "Failed to update RFID card"
                    )
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "No Member Found",
                    "No member record found for the selected position.",
                )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Error updating card: {str(e)}"
            )

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """
        Handle the window show event.
        Restart the RFID reader when the window is displayed.

        @param event: The show event.
        """
        super().showEvent(event)
        try:
            self.rfid_reader.reinitialize()  # Reinitialize the RFID reader.
            self.reader_thread = Thread(
                target=self.rfid_reader.start_reading,
                args=(self._on_card_detected,),
                daemon=True,
            )
            self.reader_thread.start()
        except Exception as e:
            self._show_error_and_close(f"Failed to start RFID reader: {str(e)}")

    def hideEvent(self, event: QtGui.QHideEvent) -> None:
        """
        Handle the window hide event.
        Stops the RFID reader when the window is hidden.

        @param event: The hide event.
        """
        super().hideEvent(event)
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
        except Exception as e:
            print(f"Error stopping RFID reader: {str(e)}")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """
        Handle the window close event.
        Stops the RFID reader and cleans up resources before closing.

        @param event: The close event.
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
            event.accept()  # Still accept the event to ensure application closes
