# Raspberry Pi Attendance System

A Python-based attendance tracking system for Raspberry Pi using RFID-RC522 and PyQt5.

## Features

- RFID card tap-in/tap-out system
- Local SQLite database storage
- Automatic sign-out at 7:00 PM
- User-friendly PyQt5 interface
- Activity logging
- Duration tracking

## Requirements

- Raspberry Pi (any model)
- RFID-RC522 module
- Python 3.6+
- PyQt5

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd attendance-system
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

## Project Structure

- `main.py`: Application entry point
- `ui.py`: PyQt5 user interface implementation
- `database_manager.py`: SQLite database operations
- `config.py`: Configuration settings
- `requirements.txt`: Python dependencies

## Usage

1. Start the application:
```bash
python3 main.py
```

2. The main window will appear with:
   - Card ID input field
   - Tap button
   - Status messages
   - Activity log

3. To sign in/out:
   - Present RFID card to the reader
   - System automatically determines whether to sign in or out
   - Duration is calculated for sign-outs

## Configuration

Edit `config.py` to modify:
- RFID card to user mappings
- Auto sign-out time (default: 7:00 PM)
- Default duration for auto sign-out (default: 1 hour)
- UI settings

## Notes

- Users who don't sign out by 7:00 PM will be automatically signed out with a 1-hour duration
- All activities are logged with timestamps
- The system maintains a local SQLite database for persistent storage 