"""Mock email provider - logs only, no external service."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class MockEmailProvider:
    """Mock email provider that only logs notifications."""

    async def send(
        self,
        recipient: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> bool:
        """
        Mock send email by logging only.
        
        Args:
            recipient: Email address
            title: Email subject
            body: Email body
            data: Optional data (not used in email)
            
        Returns:
            Always True (mock always succeeds)
        """
        logger.info(
            f"[MOCK EMAIL] To: {recipient} | Subject: {title} | Body: {body}",
            extra={"recipient": recipient, "subject": title, "body": body, "provider": "mock_email"},
        )
        return True
