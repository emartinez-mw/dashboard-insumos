ALLOWED_DOMAIN = "admin.com.ar"


def is_allowed_domain(email: str, allowed_domain: str = ALLOWED_DOMAIN) -> bool:
    """Compara el dominio exacto tras el @, no endswith (evita bypass tipo evil-admin.com.ar)."""
    return email.split("@")[-1].lower() == allowed_domain.lower()
