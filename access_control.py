ALLOWED_DOMAIN = "admin.com.ar"


def is_allowed_domain(email: str, allowed_domain: str = ALLOWED_DOMAIN) -> bool:
    """Compara el dominio exacto tras el @, no endswith (evita bypass tipo evil-admin.com.ar)."""
    return email.split("@")[-1].lower() == allowed_domain.lower()


INACTIVITY_TIMEOUT_SECONDS = 7200


def is_session_expired(last_activity: float, now: float, timeout_seconds: int = INACTIVITY_TIMEOUT_SECONDS) -> bool:
    return (now - last_activity) > timeout_seconds
