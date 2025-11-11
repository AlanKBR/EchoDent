from __future__ import annotations

from datetime import timedelta

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import login_required, login_user, logout_user

from app.models import RoleEnum
from app.services.user_service import authenticate_user, get_or_create_dev_user
from app.utils.decorators import debug_only

auth_bp = Blueprint("auth_bp", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():  # pragma: no cover - thin controller
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        user = authenticate_user(username, password)
        if user:
            login_user(user)
            # Redirect to 'next' (from @login_required), else dashboard
            next_url = request.args.get("next") or request.form.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("core_bp.dashboard"))

        flash("Usuário ou senha inválidos.", "danger")
        # fall through to render template again

    return render_template("login.html")


@auth_bp.route("/logout", methods=["GET"])
@login_required
def logout():  # pragma: no cover - thin controller
    logout_user()
    return redirect(url_for("auth_bp.login"))


@auth_bp.route("/__dev/login_as/<role>", methods=["GET"])  # dev-only
@debug_only
def dev_login_as(role: str):  # pragma: no cover - dev helper
    """Login as a specific role for local debugging.

    Enabled only when app.debug or TESTING is set. Use:
      GET /__dev/login_as/admin
      GET /__dev/login_as/dentista
      GET /__dev/login_as/secretaria

    Optionally pass ?next=/dashboard to control redirect.
    """
    if not (current_app.debug or current_app.config.get("TESTING")):
        abort(404)

    role_map = {
        "admin": RoleEnum.ADMIN,
        "dentista": RoleEnum.DENTISTA,
        "secretaria": RoleEnum.SECRETARIA,
    }
    key = (role or "").strip().lower()
    enum = role_map.get(key)
    if not enum:
        abort(400)

    user = get_or_create_dev_user(enum)
    # Persist login across separate browser contexts
    # (DevTools, Simple Browser, etc.)
    try:
        session.permanent = True
    except Exception:
        pass
    # Remember cookie for 30 days to avoid re-login during dev
    login_user(user, remember=True, duration=timedelta(days=30))
    next_url = request.args.get("next") or url_for("core_bp.dashboard")
    return redirect(next_url)


@auth_bp.route("/__dev/ensure_login", methods=["GET"])  # dev-only convenience
@debug_only
def dev_ensure_login():  # pragma: no cover - dev helper
    """Ensure there's an authenticated dev session, then redirect.

    Usage (dev only): /__dev/ensure_login?role=admin&next=/agenda
    If already logged in, just redirects. If not, logs in with the
    requested role.
    """
    if not (current_app.debug or current_app.config.get("TESTING")):
        abort(404)

    # If user already authenticated, just forward
    try:
        from flask_login import current_user

        if current_user and getattr(current_user, "is_authenticated", False):
            nxt = request.args.get("next") or url_for("core_bp.dashboard")
            return redirect(nxt)
    except Exception:
        pass

    role = (request.args.get("role") or "admin").strip().lower()
    role_map = {
        "admin": RoleEnum.ADMIN,
        "dentista": RoleEnum.DENTISTA,
        "secretaria": RoleEnum.SECRETARIA,
    }
    enum = role_map.get(role, RoleEnum.ADMIN)
    user = get_or_create_dev_user(enum)
    try:
        session.permanent = True
    except Exception:
        pass
    login_user(user, remember=True, duration=timedelta(days=30))
    nxt = request.args.get("next") or url_for("core_bp.dashboard")
    return redirect(nxt)


@auth_bp.route("/__dev/quick_login/<role>", methods=["GET"])  # E2E helper
@debug_only
def dev_quick_login(role: str):  # pragma: no cover - E2E test helper
    """Ultra-fast login for E2E tests - returns JSON status.

    Usage: GET /__dev/quick_login/ADMIN
    Returns: {"status": "ok", "user": "Dev Admin", "role": "ADMIN"}

    Use this in MCP tests to verify login without navigating pages.
    """
    if not (current_app.debug or current_app.config.get("TESTING")):
        abort(404)

    role_map = {
        "admin": RoleEnum.ADMIN,
        "dentista": RoleEnum.DENTISTA,
        "secretaria": RoleEnum.SECRETARIA,
    }
    key = (role or "").strip().upper()
    enum = role_map.get(key.lower())
    if not enum:
        return {"status": "error", "message": f"Invalid role: {key}"}, 400

    user = get_or_create_dev_user(enum)
    session.permanent = True
    login_user(user, remember=True, duration=timedelta(days=30))

    return {
        "status": "ok",
        "user": user.nome_completo,
        "role": enum.value,
        "username": user.username,
    }
