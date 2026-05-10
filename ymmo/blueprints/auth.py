"""Authentification : connexion, inscription, déconnexion.

Limites anti-bruteforce via Flask-Limiter :
- 5 tentatives de connexion par minute, par IP,
- 3 inscriptions par minute, par IP.
"""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import limiter
from ..forms import LoginForm, RegisterForm
from ..services import AuthError, AuthService

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/connexion", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("public.home"))

    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = AuthService.authenticate(form.email.data, form.password.data)
        except AuthError as exc:
            flash(str(exc), "error")
        else:
            login_user(user, remember=form.remember.data)
            next_url = request.args.get("next") or _redirect_for_role(user.role.value)
            flash(f"Bonjour {user.first_name}, ravi de vous revoir !", "success")
            return redirect(next_url)

    return render_template("auth/login.html", form=form)


@auth_bp.route("/inscription", methods=["GET", "POST"])
@limiter.limit("3 per minute", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("public.home"))

    form = RegisterForm()
    if form.validate_on_submit():
        try:
            user = AuthService.register(
                email=form.email.data,
                password=form.password.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                phone=form.phone.data,
            )
        except AuthError as exc:
            flash(str(exc), "error")
        else:
            login_user(user)
            flash("Bienvenue chez Ymmo !", "success")
            return redirect(url_for("client.dashboard"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/deconnexion")
@login_required
def logout():
    logout_user()
    flash("À bientôt sur Ymmo.", "info")
    return redirect(url_for("public.home"))


def _redirect_for_role(role: str) -> str:
    return {
        "admin": url_for("admin.dashboard"),
        "agent": url_for("agent.dashboard"),
        "client": url_for("client.dashboard"),
    }.get(role, url_for("public.home"))
