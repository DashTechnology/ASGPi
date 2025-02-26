#!/usr/bin/env python3
"""
Discord webhook handler for sending attendance notifications.
Provides functionality to send tap in/out notifications to a Discord channel.
"""

import json
from datetime import datetime
from typing import Dict, Optional, Union, List
import requests
import random


class DiscordWebhook:
    """
    Handles sending notifications to Discord via webhooks.
    Manages tap in/out event notifications with proper formatting.
    """

    # Collection of meme GIFs for special members
    PRESIDENT_MEMES: List[str] = [
        "https://media.giphy.com/media/3o7TKF1fSIs1R19B8k/giphy.gif",  # Cool entrance
        "https://media.giphy.com/media/l0IykG0AM7911MrCM/giphy.gif",  # Boss entrance
        "https://media.giphy.com/media/3o7qE1YN7aBOFPRw8E/giphy.gif",  # Like a boss
        "https://media.giphy.com/media/l46C93LNM33JJ1SMw/giphy.gif",  # Epic entrance
        "https://media.giphy.com/media/xT0BKqxuUDfosKEXXG/giphy.gif",  # Cool guy
    ]

    YAPPER_MEMES: List[str] = [
        "https://media.giphy.com/media/l0HlMWkHJKvNv6B8Y/giphy.gif",  # Funny entrance
        "https://media.giphy.com/media/26n6R5HOYPbekK0YE/giphy.gif",  # Happy dance
        "https://media.giphy.com/media/26tP24Yd1GznbcXkI/giphy.gif",  # Cool moves
        "https://media.giphy.com/media/26gsjCZpPolPr3sBy/giphy.gif",  # Fun vibes
        "https://media.giphy.com/media/26ufq9mryvc5HI27m/giphy.gif",  # Party time
    ]

    def __init__(self, webhook_url: str) -> None:
        """
        Initialize the Discord webhook handler.

        @param webhook_url: The Discord webhook URL to send notifications to
        """
        self.webhook_url = webhook_url

    def _get_special_member_info(
        self, member_name: str
    ) -> Optional[Dict[str, Union[str, List[str]]]]:
        """
        Get special formatting for specific members.

        @param member_name: Name of the member
        @return: Dictionary with special member info if applicable, None otherwise
        """
        if "Movses" in member_name:
            return {
                "display_name": "President Movies",
                "memes": self.PRESIDENT_MEMES,
                "title_emoji": "👑",
            }
        elif "Moises" in member_name:
            return {
                "display_name": "President Movies second Son / Yapper",
                "memes": self.YAPPER_MEMES,
                "title_emoji": "🎭",
            }
        return None

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

            # Check for special member handling
            special_member = self._get_special_member_info(member_name)
            if special_member:
                display_name = special_member["display_name"]
                title_emoji = special_member["title_emoji"]
                random_meme = random.choice(special_member["memes"])
            else:
                display_name = member_name
                title_emoji = "🎯"
                random_meme = None

            embed: Dict[str, Union[str, int]] = {
                "title": f"{title_emoji} Member Tap {event_type.title()} {title_emoji}",
                "description": f"**{display_name}** ({position})",
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

            # Add meme GIF for special members
            if random_meme:
                embed["image"] = {"url": random_meme}

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
