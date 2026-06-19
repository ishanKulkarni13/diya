"""Mock SMS provider - logs only, no external service."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class MockSMSProvider:
    """Mock SMS provider that only logs notifications."""

    async def send(
        self,
        recipient: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> bool:
        """
        Mock send SMS by logging only.
        
        Args:
            recipient: Phone number
            title: Message title (not used in SMS)
            body: Message body
            data: Optional data (not used in SMS)
            
        Returns:
            Always True (mock always succeeds)
        """
        logger.info(
            f"[MOCK SMS] To: {recipient} | Message: {body}",
            extra={"recipient": recipient, "body": body, "provider": "mock_sms"},
        )
        return True
