import pytest
from unittest.mock import patch, MagicMock
from api.auth import get_token, _token_cache
from config import AUTH_URL, CLIENT_ID, CLIENT_SECRET


@pytest.fixture(autouse=True)
def reset_token_cache():
    _token_cache["token"] = None
    _token_cache["expires_at"] = 0
    yield


def test_get_token_success():
    mock_response = MagicMock()
    mock_response.text = "abc123-uuid-token"
    mock_response.raise_for_status.return_value = None

    with patch("api.auth.requests.get", return_value=mock_response) as mock_get:
        token = get_token()

    assert token == "abc123-uuid-token"
    mock_get.assert_called_once_with(
        AUTH_URL,
        params={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=15,
    )


def test_get_token_cached():
    mock_response = MagicMock()
    mock_response.text = "xyz789-uuid-token"
    mock_response.raise_for_status.return_value = None

    with patch("api.auth.requests.get", return_value=mock_response) as mock_post:
        token1 = get_token()
        token2 = get_token()

    assert token1 == token2
    assert mock_post.call_count == 1  # solo una llamada HTTP


def test_get_token_raises_on_http_error():
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")

    with patch("api.auth.requests.get", return_value=mock_response):
        with pytest.raises(Exception, match="401 Unauthorized"):
            get_token()
