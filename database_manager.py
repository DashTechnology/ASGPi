#!/usr/bin/env python3
"""
Database management module for the attendance system.
Handles all Supabase operations and data persistence.
"""

import os
import sys
from datetime import datetime, timezone
from dateutil.parser import isoparse
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from supabase import create_client, Client
import config

# Load environment variables from .env file
load_dotenv()


class DatabaseManager:
    """
    Manages Supabase database operations for attendance logging and user management.
    """

    def __init__(self) -> None:
        """
        Initialize the DatabaseManager with Supabase connection.
        """
        try:
            url: str = os.environ.get("SUPABASE_URL", "")
            key: str = os.environ.get("SUPABASE_KEY", "")
            if not url or not key:
                raise ValueError(
                    "Supabase credentials not found in environment variables"
                )

            self.supabase: Client = create_client(url, key)
        except Exception as error:
            print(f"Database connection error: {error}")
            sys.exit(1)

    def get_positions(self) -> List[str]:
        """
        Retrieves unique positions from the asg_members table while preserving
        the order as returned by the database. Only returns positions for members
        with a non-empty name (i.e. non-vacant members).

        @return: List of unique positions, ordered as they appear in the database.
        """
        try:
            # Query the "position" and "name" columns from asg_members.
            response = (
                self.supabase.table("asg_members").select("position, name").execute()
            )
            if not response.data:
                return []

            positions: List[str] = []  # List to store unique positions in order
            seen_positions: set[str] = (
                set()
            )  # Set to track positions that have been seen

            # Process each member in the returned data, preserving the original order.
            for member in response.data:
                # Validate that the "name" field exists, is not None and is not empty.
                name: Optional[str] = member.get("name")
                if name is None or name.strip() == "":
                    continue  # Skip vacant member records

                # Validate presence of the "position" field.
                position: Optional[str] = member.get("position")
                if position is None:
                    continue

                # Add the position to the result if it hasn't been added yet.
                if position not in seen_positions:
                    seen_positions.add(position)
                    positions.append(position)
            return positions

        except Exception as error:
            print(f"Error fetching positions: {error}")
            return []

    def update_member(self, member_id: int, data: Dict[str, Any]) -> bool:
        """
        Updates an existing member's information.

        @param member_id: The member's ID.
        @param data: Dictionary containing fields to update.
        @return: True if successful, False otherwise.
        """
        try:
            response = (
                self.supabase.table("asg_members")
                .update(data)
                .eq("id", member_id)
                .execute()
            )
            return bool(response.data)
        except Exception as error:
            print(f"Error updating member: {error}")
            return False

    def get_member_by_rfid(self, rfid_tag: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves member information by RFID tag.

        @param rfid_tag: The RFID card identifier.
        @return: Member information if found, None otherwise.
        """
        try:
            response = (
                self.supabase.table("asg_members")
                .select("*")
                .eq("rfid_tag", rfid_tag)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as error:
            print(f"Error fetching member: {error}")
            return None

    def get_active_session(self, member_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves an active attendance session for the given member.

        @param member_id: The member's ID.
        @return: The active session data or None if no active session exists.
        """
        try:
            response = (
                self.supabase.table("asg_logs")
                .select("*")
                .eq("user_id", member_id)
                .is_("sign_out_time", "null")
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as error:
            print(f"Error fetching active session: {error}")
            return None

    def sign_in(self, rfid_tag: str) -> Optional[Dict[str, Any]]:
        """
        Records a sign in event for the given member.
        Only allows sign-in between 7:30 AM and 7:00 PM.

        @param rfid_tag: The RFID card identifier.
        @return: The log entry if successful, None otherwise.
        """
        try:
            # Check if it's before 7:30 AM or after 7:00 PM (bypass in DEV mode)
            current_time = datetime.now()
            if not config.DEV_MODE:
                # Check if it's before start time (7:30 AM)
                if current_time.hour < config.START_TIME_HOUR or (
                    current_time.hour == config.START_TIME_HOUR
                    and current_time.minute < config.START_TIME_MINUTE
                ):
                    print("Sign-in rejected: Before 7:30 AM")
                    return {"error": "before_hours"}

                # Check if it's after end time (7:00 PM)
                if current_time.hour >= config.AUTO_SIGNOUT_HOUR:
                    print("Sign-in rejected: After 7:00 PM")
                    return {"error": "after_hours"}

            # Retrieve the member using the provided RFID tag.
            member = self.get_member_by_rfid(rfid_tag)
            if not member:
                print(f"Unknown RFID tag: {rfid_tag}")
                return None

            # Generate the current UTC time in ISO format.
            now_iso = datetime.now(timezone.utc).isoformat()
            log_data = {
                "message": f"{member['name'].split(' ')[0]} Signed In",
                "user_id": member["id"],
                "sign_in_time": now_iso,
            }

            # Mark the member as in the office by setting inoffice to True.
            self.update_member(member["id"], {"inoffice": True})

            # Insert log entry for sign in.
            response = self.supabase.table("asg_logs").insert(log_data).execute()
            return response.data[0] if response.data else None
        except Exception as error:
            print(f"Error during sign in: {error}")
            return None

    def sign_out(self, rfid_tag: str) -> Optional[float]:
        """
        Records a sign out event for the given member.

        :param rfid_tag: The RFID card identifier.
        :return: Duration in hours if successful, None otherwise.
        """
        try:
            # Retrieve the member based on the RFID tag.
            member: Optional[Dict[str, Any]] = self.get_member_by_rfid(rfid_tag)
            if member is None:
                print(f"Member not found for RFID tag: {rfid_tag}")
                return None

            # Retrieve the active session for this member.
            active_session: Optional[Dict[str, Any]] = self.get_active_session(
                member["id"]
            )
            if active_session is None:
                print(f"No active session found for member ID: {member['id']}")
                return None

            # Parse the sign in time using isoparse for robust ISO8601 parsing.
            sign_in_time: datetime = isoparse(active_session["sign_in_time"])
            sign_out_time: datetime = datetime.now(timezone.utc)
            duration_hours: float = (
                sign_out_time - sign_in_time
            ).total_seconds() / 3600.0

            # Prepare the update payload for the sign out event.
            update_data: Dict[str, Any] = {
                "sign_out_time": sign_out_time.isoformat(),
                "duration": duration_hours,
                "message": f"{member['name'].split(' ')[0]} Signed Out",
            }

            # Update the sign out event in the asg_logs table.
            self.supabase.table("asg_logs").update(update_data).eq(
                "id", active_session["id"]
            ).execute()

            # Mark the member as no longer in the office.
            self.update_member(member["id"], {"inoffice": False})
            return duration_hours
        except Exception as error:
            print(f"Error during sign out: {error}")
            return None

    def auto_sign_out(self) -> None:
        """
        Automatically signs out all active members.
        Intended to be executed at a scheduled time (e.g., 7:00 pm).
        Sets duration to 0 if sign-in time is less than an hour ago.
        """
        try:
            # Retrieve all members currently in the office.
            response = (
                self.supabase.table("asg_members")
                .select("*")
                .eq("inoffice", True)
                .execute()
            )
            if not response.data:
                return

            now = datetime.now(timezone.utc)
            signed_out_members = []  # Track members who were signed out

            for member in response.data:
                active_session = self.get_active_session(member["id"])
                if active_session:
                    # Calculate time difference
                    sign_in_time = isoparse(active_session["sign_in_time"])
                    time_diff = (
                        now - sign_in_time
                    ).total_seconds() / 3600.0  # Convert to hours

                    # Set duration based on time difference
                    duration = 0.0 if time_diff < 1.0 else 1.0

                    # Prepare update data for auto sign-out
                    update_data = {
                        "sign_out_time": now.isoformat(),
                        "duration": duration,
                        "message": f"{member['name'].split(' ')[0]} Automatically signed out.",
                    }
                    self.supabase.table("asg_logs").update(update_data).eq(
                        "id", active_session["id"]
                    ).execute()

                    # Update member status to mark them as signed out
                    self.update_member(member["id"], {"inoffice": False})

                    # Add to the list of signed out members
                    signed_out_members.append(
                        f"{member['name']} ({member['position']})"
                    )

            # Return the list of signed out members for logging
            if signed_out_members:
                return {
                    "message": f"Auto sign-out executed for: {', '.join(signed_out_members)}",
                    "members": signed_out_members,
                }
            return None

        except Exception as error:
            print(f"Error during auto sign out: {error}")
            return None


if __name__ == "__main__":
    # Example test execution: Initialize DatabaseManager and print unique positions.
    db_manager = DatabaseManager()
    positions = db_manager.get_positions()
    print("Positions:", positions)
