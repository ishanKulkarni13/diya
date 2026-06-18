"""
Exception hierarchy for the Assist module and providers.
"""

class ProviderError(Exception):
    """Base class for all provider-related errors."""
    pass

class AuthenticationError(ProviderError):
    """Raised when the provider rejects credentials (e.g., 401)."""
    pass

class QuotaExceededError(ProviderError):
    """Raised when the provider quota is exceeded (e.g., 429 Quota)."""
    pass

class RateLimitError(ProviderError):
    """Raised when the provider rate limits requests (e.g., 429 Rate Limit)."""
    pass

class TemporaryUnavailableError(ProviderError):
    """Raised when the provider is temporarily unavailable (e.g., 500, 502, 503)."""
    pass

class TimeoutError(ProviderError):
    """Raised when the provider request times out."""
    pass

class SafetyBlockedError(ProviderError):
    """Raised when the provider blocks the request due to safety concerns."""
    pass

class MalformedResponseError(ProviderError):
    """Raised when the provider returns an invalid or unparseable response."""
    pass

class UnknownProviderError(ProviderError):
    """Raised when an unknown or unhandled provider error occurs."""
    pass
