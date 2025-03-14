"""
Configuration settings for the attendance system.
"""

from typing import Dict

# Database configuration
DB_PATH: str = "attendance.db"

# RFID card to user mapping
USER_MAPPING: Dict[str, str] = {"123456": "Alice", "654321": "Bob"}

# Time settings
AUTO_SIGNOUT_HOUR: int = 22  # 8:00 PM
SLEEP_TIME_HOUR: int = 22
SLEEP_TIME_MINUTE: int = 30  # 8:00 PM
WAKE_TIME_HOUR: int = 8  # 8:00 AM
WAKE_TIME_MINUTE: int = 0

# Sign-in start time
START_TIME_HOUR: int = 7  # 7:00 AM
START_TIME_MINUTE: int = 0  # 7:00 AM

DEFAULT_DURATION_HOURS: float = 1.0  # Duration assigned for auto sign-out

# UI Settings
WINDOW_TITLE: str = "ASG Attendance System"
WINDOW_GEOMETRY: tuple[int, int, int, int] = (
    100,
    100,
    1024,
    600,
)  # x, y, width, height
AUTO_SIGNOUT_CHECK_INTERVAL: int = 60000  # milliseconds (1 minute)

# Message display duration in milliseconds (5 seconds)
MESSAGE_DISPLAY_DURATION: int = 5000

# Development mode flag. When set to True, bypasses sign-in time restrictions and sleep/wake auto adjustments.
DEV_MODE: bool = False

# Discord webhook configuration
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1344389702735761418/u5S9fgUadcS2lfFpgGnBXwJ9nwS87uORHyR_5ermeDeiyFPdmWVUI8QXaCCSf33j4Kml"
