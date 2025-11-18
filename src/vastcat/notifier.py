"""Notification helpers."""
from __future__ import annotations

from typing import Optional
import json
import requests


class Notifier:
    def __init__(self, discord_webhook: Optional[str] = None) -> None:
        self.discord_webhook = discord_webhook

    def notify(self, title: str, message: str) -> None:
        if not self.discord_webhook:
            return
        payload = {
            "username": "Vastcat",
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": 0xF4A460,
                }
            ],
        }
        try:
            resp = requests.post(self.discord_webhook, data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=10)
            resp.raise_for_status()
        except Exception:
            pass  # Silent fail for notifications
