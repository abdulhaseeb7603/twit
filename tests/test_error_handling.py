"""Tests for error classification in the bridge layer.

Validates that classify_error() correctly categorizes:
- HTTP 429 as RATE_LIMITED (retryable)
- HTTP 503 as SERVICE_UNAVAILABLE (retryable)
- Timeout exceptions as TIMEOUT (retryable)
- Cloudflare blocks as CLOUDFLARE_BLOCK (retryable)
- Cookie/auth failures as TWIKIT_AUTH_FAILED (not retryable)
- Unknown errors as UNKNOWN_ERROR (not retryable)
"""

from unittest.mock import MagicMock

import pytest


def _make_http_status_error(status_code: int):
    """Create a mock httpx.HTTPStatusError with given status code."""
    try:
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_request = MagicMock()
        return httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=mock_request,
            response=mock_response,
        )
    except ImportError:
        # httpx not installed yet; create a stand-in
        error = Exception(f"HTTP {status_code}")
        error.response = MagicMock()
        error.response.status_code = status_code
        return error


class TestClassifyError:
    """Tests for the classify_error() function in common.py."""

    def test_classify_rate_limit_error(self, scripts_dir):
        """HTTP 429 should be classified as RATE_LIMITED, retryable."""
        from common import classify_error

        error = _make_http_status_error(429)
        code, retryable = classify_error(error)
        assert code == "RATE_LIMITED"
        assert retryable is True

    def test_classify_service_unavailable(self, scripts_dir):
        """HTTP 503 should be classified as SERVICE_UNAVAILABLE, retryable."""
        from common import classify_error

        error = _make_http_status_error(503)
        code, retryable = classify_error(error)
        assert code == "SERVICE_UNAVAILABLE"
        assert retryable is True

    def test_classify_timeout(self, scripts_dir):
        """Timeout exceptions should be classified as TIMEOUT, retryable."""
        from common import classify_error

        try:
            import httpx

            error = httpx.TimeoutException("Connection timed out")
        except ImportError:
            error = TimeoutError("Connection timed out")

        code, retryable = classify_error(error)
        assert code == "TIMEOUT"
        assert retryable is True

    def test_classify_cloudflare_block(self, scripts_dir):
        """Exceptions mentioning 'Cloudflare' should be CLOUDFLARE_BLOCK, retryable."""
        from common import classify_error

        error = Exception("Blocked by Cloudflare protection")
        code, retryable = classify_error(error)
        assert code == "CLOUDFLARE_BLOCK"
        assert retryable is True

    def test_classify_auth_failure(self, scripts_dir):
        """Exceptions mentioning 'cookie' should be TWIKIT_AUTH_FAILED, not retryable."""
        from common import classify_error

        error = Exception("cookie has expired or is invalid")
        code, retryable = classify_error(error)
        assert code == "TWIKIT_AUTH_FAILED"
        assert retryable is False

    def test_classify_unknown_error(self, scripts_dir):
        """Generic exceptions should be UNKNOWN_ERROR, not retryable."""
        from common import classify_error

        error = Exception("Something completely unexpected")
        code, retryable = classify_error(error)
        assert code == "UNKNOWN_ERROR"
        assert retryable is False
