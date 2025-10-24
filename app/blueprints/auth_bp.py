from __future__ import annotations

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_login import (
    login_user,
    logout_user,
    login_required,
)

from app.services.user_service import authenticate_user


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
