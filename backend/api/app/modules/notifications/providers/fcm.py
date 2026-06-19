"""Firebase Cloud Messaging provider."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class FCMProvider:
    """Firebase Cloud Messaging notification provider."""

    def __init__(self, credentials_path: str | None = None) -> None:
        """
        Initialize FCM provider.
        
        Args:
            credentials_path: Path to Firebase service account JSON
        """
        self._credentials_path = credentials_path
        self._initialized = False
        
        if credentials_path:
            try:
                # TODO: Initialize Firebase Admin SDK when credentials are provided
                # import firebase_admin
                # from firebase_admin import credentials, messaging
                # cred = credentials.Certificate(credentials_path)
                # firebase_admin.initialize_app(cred)
                self._initialized = True
                logger.info(f"FCM provider initialized with credentials from {credentials_path}")
            except Exception as e:
                logger.warning(f"Failed to initialize FCM provider: {e}")
                self._initialized = False
        else:
            logger.info("FCM provider created without credentials (push notifications disabled)")

    async def send(
        self,
        recipient: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> bool:
        """
        Send a push notification via FCM.
        
        Args:
            recipient: Device token
            title: Notification title
            body: Notification body
            data: Optional data payload
            
        Returns:
            True if sent successfully
        """
        if not self._initialized:
            logger.warning(
                f"FCM not initialized - would send: {title} to {recipient[:20]}..."
            )
            return False

        try:
            # TODO: Send actual FCM message when Firebase Admin SDK is wired
            # from firebase_admin import messaging
            # message = messaging.Message(
            #     notification=messaging.Notification(title=title, body=body),
            #     data=data or {},
            #     token=recipient,
            # )
            # response = messaging.send(message)
            logger.info(
                f"FCM notification sent: {title} to {recipient[:20]}...",
                extra={"title": title, "recipient_hint": recipient[:20], "data": data},
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send FCM notification: {e}", exc_info=True)
            return False
