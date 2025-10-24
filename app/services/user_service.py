from __future__ import annotations

from typing import Optional

from werkzeug.security import check_password_hash

from werkzeug.security import generate_password_hash

from app import db
from app.models import Usuario, RoleEnum


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


def get_or_create_dev_user(role: RoleEnum) -> Usuario:
    """Return a lightweight dev user for the given role, creating if needed.

    Dev-only helper. Creates a deterministic username like `dev_admin` with a
    simple password hash. Not intended for production.
    """
    username = f"dev_{role.value.lower()}"
    user = Usuario.query.filter_by(username=username).first()
    if user:
        return user

    user = Usuario()
    user.username = username
    user.role = role
    user.nome_completo = f"Dev {role.value.title()}"
    user.password_hash = generate_password_hash("devpass")
    db.session.add(user)
    db.session.commit()
    return user
