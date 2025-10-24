from __future__ import annotations

from werkzeug.security import generate_password_hash

from app import db
from app.models import Usuario, RoleEnum
from app.services.user_service import authenticate_user


def test_authenticate_success(app, db_session):
    # Arrange: create an active user with a known password
    user = Usuario()
    user.username = "auth_user"
    user.password_hash = generate_password_hash("s3cret!")
    user.role = RoleEnum.DENTISTA
    user.is_active = True
    db.session.add(user)
    db.session.commit()

    # Act
    got = authenticate_user("auth_user", "s3cret!")

    # Assert
    assert got is not None
    assert got.id == user.id


def test_authenticate_wrong_password(app, db_session):
    user = Usuario()
    user.username = "auth_user2"
    user.password_hash = generate_password_hash("right")
    user.role = RoleEnum.DENTISTA
    user.is_active = True
    db.session.add(user)
    db.session.commit()

    got = authenticate_user("auth_user2", "wrong")

    assert got is None


def test_authenticate_inactive_user(app, db_session):
    user = Usuario()
    user.username = "inactive_user"
    user.password_hash = generate_password_hash("pw")
    user.role = RoleEnum.DENTISTA
    user.is_active = False
    db.session.add(user)
    db.session.commit()

    got = authenticate_user("inactive_user", "pw")

    assert got is None


def test_authenticate_nonexistent_user(app, db_session):
    got = authenticate_user("does_not_exist", "irrelevant")
    assert got is None
