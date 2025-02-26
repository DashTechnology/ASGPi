#!/usr/bin/env python3
"""
Discord webhook integration for attendance system.
Sends notifications to Discord when members tap in or tap out.
"""

import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import config


class DiscordNotifier:
    """
    Handles sending notifications to Discord via webhooks.
    """

    @staticmethod
    def send_tap_in_notification(member: Dict[str, Any]) -> bool:
        """
        Sends a notification to Discord when a member taps in.

        @param member: Dictionary containing member information
        @return: True if successful, False otherwise
        """
        # Check if Discord webhook is enabled
        if not config.DISCORD_WEBHOOK_ENABLED:
            return True

        try:
            current_time = datetime.now().strftime("%I:%M %p on %B %d, %Y")
            name = member.get("name", "Unknown Member")
            position = member.get("position", "Unknown Position")

            # Create embedded message
            embed = {
                "title": "Member Signed In",
                "description": f"{name} has signed in at {current_time}",
                "color": 3066993,  # Green color
                "fields": [
                    {"name": "Position", "value": position, "inline": True},
                    {"name": "Time", "value": current_time, "inline": True},
                ],
                "thumbnail": {"url": "https://i.imgur.com/zZEKuq4.png"},  # Sign in icon
                "footer": {"text": "ASG Attendance System"},
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Send webhook
            payload = {"embeds": [embed]}

            try:
                response = requests.post(
                    config.DISCORD_WEBHOOK_URL,
                    data=json.dumps(payload),
                    headers={"Content-Type": "application/json"},
                    timeout=5,  # Set timeout to 5 seconds
                )

                if response.status_code == 204:
                    print(f"Successfully sent Discord sign-in notification for {name}")
                    return True
                else:
                    print(
                        f"Discord webhook returned status code: {response.status_code}"
                    )
                    return False
            except requests.RequestException as req_error:
                print(f"Network error during Discord notification: {str(req_error)}")
                return False
        except Exception as e:
            print(f"Error sending Discord tap in notification: {str(e)}")
            return False

    @staticmethod
    def send_tap_out_notification(
        member: Dict[str, Any], duration: Optional[float] = None
    ) -> bool:
        """
        Sends a notification to Discord when a member taps out.

        @param member: Dictionary containing member information
        @param duration: Duration of the session in hours
        @return: True if successful, False otherwise
        """
        # Check if Discord webhook is enabled
        if not config.DISCORD_WEBHOOK_ENABLED:
            return True

        try:
            current_time = datetime.now().strftime("%I:%M %p on %B %d, %Y")
            name = member.get("name", "Unknown Member")
            position = member.get("position", "Unknown Position")

            duration_str = "Unknown"
            if duration is not None:
                hours = int(duration)
                minutes = int((duration - hours) * 60)
                duration_str = f"{hours} hours, {minutes} minutes"

            # Create embedded message
            embed = {
                "title": "Member Signed Out",
                "description": f"{name} has signed out at {current_time}",
                "color": 15158332,  # Red color
                "fields": [
                    {"name": "Position", "value": position, "inline": True},
                    {"name": "Time", "value": current_time, "inline": True},
                    {
                        "name": "Session Duration",
                        "value": duration_str,
                        "inline": False,
                    },
                ],
                "thumbnail": {
                    "url": "https://i.imgur.com/38pZcaE.png"  # Sign out icon
                },
                "footer": {"text": "ASG Attendance System"},
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Send webhook
            payload = {"embeds": [embed]}

            try:
                response = requests.post(
                    config.DISCORD_WEBHOOK_URL,
                    data=json.dumps(payload),
                    headers={"Content-Type": "application/json"},
                    timeout=5,  # Set timeout to 5 seconds
                )

                if response.status_code == 204:
                    print(f"Successfully sent Discord sign-out notification for {name}")
                    return True
                else:
                    print(
                        f"Discord webhook returned status code: {response.status_code}"
                    )
                    return False
            except requests.RequestException as req_error:
                print(f"Network error during Discord notification: {str(req_error)}")
                return False
        except Exception as e:
            print(f"Error sending Discord tap out notification: {str(e)}")
            return False
