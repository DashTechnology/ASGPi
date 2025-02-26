#!/usr/bin/env python3
"""
Discord webhook handler for sending attendance notifications.
Provides functionality to send tap in/out notifications to a Discord channel.
"""

import json
from datetime import datetime
from typing import Dict, Optional, Union
import requests


class DiscordWebhook:
    """
    Handles sending notifications to Discord via webhooks.
    Manages tap in/out event notifications with proper formatting.
    """

    def __init__(self, webhook_url: str) -> None:
        """
        Initialize the Discord webhook handler.

        @param webhook_url: The Discord webhook URL to send notifications to
        """
        self.webhook_url = webhook_url

    def send_tap_notification(
        self,
        member_name: str,
        position: str,
        event_type: str,
        duration: Optional[float] = None,
    ) -> bool:
        """
        Send a tap in/out notification to Discord.

        @param member_name: Name of the member
        @param position: Position/role of the member
        @param event_type: Type of event ("in" or "out")
        @param duration: Optional duration in hours for tap out events
        @return: True if notification was sent successfully, False otherwise
        """
        try:
            # Validate event type
            if event_type not in ["in", "out"]:
                raise ValueError("Event type must be either 'in' or 'out'")

            # Create the embed for the notification
            current_time = datetime.now().strftime("%I:%M %p")

            embed: Dict[str, Union[str, int]] = {
                "title": f"Member Tap {event_type.title()}",
                "description": f"**{member_name}** ({position})",
                "color": (
                    0x00FF00 if event_type == "in" else 0xFF0000
                ),  # Green for in, Red for out
                "timestamp": datetime.utcnow().isoformat(),
                "fields": [{"name": "Time", "value": current_time, "inline": True}],
            }

            # Add duration field for tap out events
            if event_type == "out" and duration is not None:
                hours = int(duration)
                minutes = int((duration - hours) * 60)
                duration_str = f"{hours}h {minutes}m"
                embed["fields"].append(
                    {"name": "Duration", "value": duration_str, "inline": True}
                )

            # Prepare the webhook payload
            payload = {"embeds": [embed]}

            # Send the webhook request
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=5,
            )

            # Check if the request was successful
            return response.status_code == 204

        except Exception as error:
            print(f"Error sending Discord notification: {error}")
            return False
