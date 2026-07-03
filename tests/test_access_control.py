from access_control import is_allowed_domain


def test_is_allowed_domain_matches_exact_domain():
    assert is_allowed_domain("user@admin.com.ar") is True


def test_is_allowed_domain_rejects_other_domain():
    assert is_allowed_domain("user@otrodominio.com") is False


def test_is_allowed_domain_rejects_lookalike_domain():
    assert is_allowed_domain("user@evil-admin.com.ar") is False


def test_is_allowed_domain_case_insensitive():
    assert is_allowed_domain("USER@ADMIN.COM.AR") is True
