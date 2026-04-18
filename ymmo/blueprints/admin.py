"""Espace administrateur : pilotage global et gestion des comptes."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..decorators import role_required
from ..models import UserRole
from ..repositories import AgencyRepository, UserRepository
from ..services import AnalyticsService, AuthError, AuthService

admin_bp = Blueprint("admin", __name__)
analytics_service = AnalyticsService()


@admin_bp.before_request
@login_required
@role_required(UserRole.ADMIN)
def _gate():
    pass


@admin_bp.route("/")
def dashboard():
    return render_template(
        "admin/dashboard.html",
        users=UserRepository.list_all(),
        agencies=AgencyRepository.list_all(),
        dashboard=analytics_service.dashboard(),
    )


@admin_bp.route("/utilisateurs/<int:user_id>/role", methods=["POST"])
def change_role(user_id: int):
    user = UserRepository.get(user_id)
    if not user:
        abort(404)
    role = request.form.get("role")
    try:
        user.role = UserRole(role)
    except ValueError:
        abort(400)
    if user.role != UserRole.AGENT:
        user.agency_id = None
    UserRepository.save()
    flash(f"Rôle de {user.full_name} : {user.role.label}.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/utilisateurs/<int:user_id>/agence", methods=["POST"])
def assign_agency(user_id: int):
    user = UserRepository.get(user_id)
    if not user:
        abort(404)
    agency_id = request.form.get("agency_id", type=int)
    user.agency_id = agency_id
    UserRepository.save()
    flash(f"Agence mise à jour pour {user.full_name}.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/utilisateurs/<int:user_id>/desactiver", methods=["POST"])
def toggle_user(user_id: int):
    user = UserRepository.get(user_id)
    if not user:
        abort(404)
    user.is_active_user = not user.is_active_user
    UserRepository.save()
    flash(
        f"Compte {'activé' if user.is_active_user else 'désactivé'}.",
        "info",
    )
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/utilisateurs/agent", methods=["POST"])
def create_agent():
    try:
        AuthService.register(
            email=request.form["email"],
            password=request.form["password"],
            first_name=request.form["first_name"],
            last_name=request.form["last_name"],
            phone=request.form.get("phone"),
            role=UserRole.AGENT,
            agency_id=request.form.get("agency_id", type=int),
        )
    except AuthError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin.dashboard"))
    flash("Agent créé.", "success")
    return redirect(url_for("admin.dashboard"))
