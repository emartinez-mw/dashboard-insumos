from access_control import is_allowed_domain, is_session_expired


def test_is_allowed_domain_matches_exact_domain():
    assert is_allowed_domain("user@admin.com.ar") is True


def test_is_allowed_domain_rejects_other_domain():
    assert is_allowed_domain("user@otrodominio.com") is False


def test_is_allowed_domain_rejects_lookalike_domain():
    assert is_allowed_domain("user@evil-admin.com.ar") is False


def test_is_allowed_domain_case_insensitive():
    assert is_allowed_domain("USER@ADMIN.COM.AR") is True


def test_is_session_expired_false_just_before_limit():
    assert is_session_expired(last_activity=0, now=7199, timeout_seconds=7200) is False


def test_is_session_expired_true_just_after_limit():
    assert is_session_expired(last_activity=0, now=7201, timeout_seconds=7200) is True


def test_is_session_expired_false_exactly_at_limit():
    assert is_session_expired(last_activity=0, now=7200, timeout_seconds=7200) is False
