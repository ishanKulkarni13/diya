import pytest
from unittest.mock import patch, MagicMock

from google.genai.errors import APIError

from app.modules.assist.providers.gemini import GeminiProvider
from app.modules.assist.exceptions import (
    AuthenticationError,
    QuotaExceededError,
    RateLimitError,
    TemporaryUnavailableError,
    TimeoutError,
    MalformedResponseError,
    UnknownProviderError
)

@pytest.fixture
def provider():
    return GeminiProvider(api_key="test-key", model_name="test-model")

@pytest.fixture(autouse=True)
def mock_sleep():
    with patch("time.sleep"):
        yield

@pytest.mark.asyncio
async def test_provider_success(provider):
    with patch.object(provider, '_execute_with_retry') as mock_execute:
        mock_response = MagicMock()
        mock_response.parsed.spoken_text = "test spoken"
        mock_response.parsed.display_text = "test display"
        mock_execute.return_value = mock_response

        result = await provider.analyze_image(b"test", "image/jpeg", "describe_scene")
        assert result.analysis.spoken_text == "test spoken"
        assert result.provider_name == "gemini"

@pytest.mark.asyncio
async def test_provider_malformed_response(provider):
    with patch.object(provider, '_execute_with_retry') as mock_execute:
        mock_response = MagicMock()
        mock_response.parsed = None
        mock_execute.return_value = mock_response

        with pytest.raises(MalformedResponseError):
            await provider.analyze_image(b"test", "image/jpeg", "describe_scene")

def test_execute_with_retry_401(provider):
    with patch.object(provider, '_client') as mock_client:
        err = APIError("Unauthorized", {})
        err.code = 401
        mock_client.models.generate_content.side_effect = err
        with pytest.raises(AuthenticationError):
            provider._execute_with_retry("prompt", "image")
        assert mock_client.models.generate_content.call_count == 1

def test_execute_with_retry_429_quota(provider):
    with patch.object(provider, '_client') as mock_client:
        err = APIError("Quota exceeded", {})
        err.code = 429
        mock_client.models.generate_content.side_effect = err
        with pytest.raises(QuotaExceededError):
            provider._execute_with_retry("prompt", "image")
        assert mock_client.models.generate_content.call_count == 1

def test_execute_with_retry_429_rate_limit(provider):
    with patch.object(provider, '_client') as mock_client:
        err = APIError("Rate limit", {})
        err.code = 429
        mock_client.models.generate_content.side_effect = err
        with pytest.raises(RateLimitError):
            provider._execute_with_retry("prompt", "image")
        # Tenacity will retry RateLimitError 3 times, plus 1 initial = 4 attempts. Wait, stop_after_attempt(3) means 3 total attempts
        assert mock_client.models.generate_content.call_count == 3

def test_execute_with_retry_503(provider):
    with patch.object(provider, '_client') as mock_client:
        err = APIError("Unavailable", {})
        err.code = 503
        mock_client.models.generate_content.side_effect = err
        with pytest.raises(TemporaryUnavailableError):
            provider._execute_with_retry("prompt", "image")
        assert mock_client.models.generate_content.call_count == 3

def test_execute_with_retry_timeout(provider):
    with patch.object(provider, '_client') as mock_client:
        import httpx
        mock_client.models.generate_content.side_effect = httpx.TimeoutException("Timeout")
        with pytest.raises(TimeoutError):
            provider._execute_with_retry("prompt", "image")
        assert mock_client.models.generate_content.call_count == 3
