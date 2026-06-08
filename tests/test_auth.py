import pytest
from unittest.mock import patch, MagicMock
from api.auth import get_token, _token_cache


def test_get_token_success():
    # Reset cache to avoid pollution from other tests
    _token_cache["token"] = None
    _token_cache["expires_at"] = 0

    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "abc123", "expires_in": 3600}
    mock_response.raise_for_status.return_value = None

    with patch("api.auth.requests.post", return_value=mock_response) as mock_post:
        token = get_token()

    assert token == "abc123"
    mock_post.assert_called_once()


def test_get_token_cached():
    # Reset cache to ensure fresh start
    _token_cache["token"] = None
    _token_cache["expires_at"] = 0

    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "xyz789", "expires_in": 3600}
    mock_response.raise_for_status.return_value = None

    with patch("api.auth.requests.post", return_value=mock_response) as mock_post:
        token1 = get_token()
        token2 = get_token()

    assert token1 == token2
    assert mock_post.call_count == 1  # solo una llamada HTTP


def test_get_token_raises_on_http_error():
    # Reset cache to force a new HTTP call
    _token_cache["token"] = None
    _token_cache["expires_at"] = 0

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")

    with patch("api.auth.requests.post", return_value=mock_response):
        with pytest.raises(Exception, match="401 Unauthorized"):
            get_token()
