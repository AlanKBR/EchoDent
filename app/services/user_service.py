from __future__ import annotations

from typing import Optional

from werkzeug.security import check_password_hash

from app.models import Usuario


def authenticate_user(username: str, password: str) -> Optional[Usuario]:
    """Authenticate a user by username and password.

    Returns the Usuario if credentials are valid and the user is active,
    otherwise returns None.
    """
    user = Usuario.query.filter_by(username=username).first()
    if not user:
        return None
    if not getattr(user, "is_active", False):
        return None
    if not check_password_hash(user.password_hash, password):
        return None
    return user
