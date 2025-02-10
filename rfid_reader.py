#!/usr/bin/env python3
"""
RFID reader module for the attendance system.
Handles all MFRC522 RFID reader operations.
"""

import time
from typing import Optional, Tuple, Callable
from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO


class RFIDReader:
    """
    Manages RFID reader operations using the MFRC522 module.
    """

    def __init__(self) -> None:
        """
        Initialize the RFID reader.
        Sets up GPIO and creates SimpleMFRC522 instance.
        """
        self._setup_gpio()
        self._continue_reading = True

    def _setup_gpio(self) -> None:
        """
        Set up GPIO and initialize the RFID reader.
        Can be called multiple times safely.
        """
        try:
            GPIO.cleanup()  # Clean up any existing GPIO setup
        except Exception:
            pass  # Ignore errors during cleanup

        # Initialize GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        self.reader = SimpleMFRC522()

    def start_reading(self, callback: Callable[[str], None]) -> None:
        """
        Start continuous reading of RFID cards.

        @param callback: Function to call when a card is detected.
                        The function should accept a card_id parameter.
        """
        self._continue_reading = True
        try:
            while self._continue_reading:
                card_id = self.read_card()
                if card_id:
                    callback(str(card_id))
                time.sleep(0.5)  # Prevent excessive CPU usage
        except Exception as e:
            print(f"Error reading RFID: {e}")
        finally:
            self.cleanup()

    def stop_reading(self) -> None:
        """
        Stop the continuous reading loop.
        """
        self._continue_reading = False

    def read_card(self) -> Optional[int]:
        """
        Read a single card.

        @return: Card ID if successful, None otherwise
        """
        try:
            card_id, _ = self.reader.read_no_block()
            return card_id if card_id else None
        except Exception as e:
            print(f"Error reading card: {e}")
            self._setup_gpio()  # Try to reinitialize on error
            return None

    def cleanup(self) -> None:
        """
        Clean up GPIO resources.
        """
        try:
            GPIO.cleanup()
        except Exception as e:
            print(f"Error during GPIO cleanup: {e}")

    def reinitialize(self) -> None:
        """
        Reinitialize the RFID reader.
        Useful when switching between windows or after errors.
        """
        self._setup_gpio()
