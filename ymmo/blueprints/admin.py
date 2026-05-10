"""Espace administrateur : pilotage global et gestion des comptes."""

from __future__ import annotations

import csv
import io

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from ..decorators import role_required
from ..models import UserRole
from ..repositories import AgencyRepository, TransactionRepository, UserRepository
from ..services import AuthError, AuthService

admin_bp = Blueprint("admin", __name__)


def _analytics():
    """Récupère le service AnalyticsService partagé attaché à l'app."""
    return current_app.extensions["analytics"]


@admin_bp.before_request
@login_required
@role_required(UserRole.ADMIN)
def _gate():
    pass


@admin_bp.route("/")
def dashboard():
    # Recherche simple sur la liste utilisateurs (par email / nom).
    query = request.args.get("q", default="", type=str).strip()
    role_filter = request.args.get("role", default="", type=str).strip()
    role_enum = UserRole(role_filter) if role_filter in {r.value for r in UserRole} else None
    page = max(1, request.args.get("page", default=1, type=int))
    users, total = UserRepository.search(query=query or None, role=role_enum, page=page, per_page=20)
    pages = max(1, -(-total // 20))

    return render_template(
        "admin/dashboard.html",
        users=users,
        users_total=total,
        users_page=page,
        users_pages=pages,
        users_query=query,
        users_role=role_filter,
        agencies=AgencyRepository.list_all(),
        dashboard=_analytics().dashboard(),
        ranking=_analytics().agent_performance(top=10),
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
    return redirect(request.referrer or url_for("admin.dashboard"))


@admin_bp.route("/utilisateurs/<int:user_id>/agence", methods=["POST"])
def assign_agency(user_id: int):
    user = UserRepository.get(user_id)
    if not user:
        abort(404)
    agency_id = request.form.get("agency_id", type=int)
    user.agency_id = agency_id
    UserRepository.save()
    flash(f"Agence mise à jour pour {user.full_name}.", "success")
    return redirect(request.referrer or url_for("admin.dashboard"))


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
    return redirect(request.referrer or url_for("admin.dashboard"))


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


@admin_bp.route("/exports/transactions.csv")
def export_transactions_csv():
    """Export CSV des transactions du réseau (admin only)."""
    rows = TransactionRepository.all_for_dataframe()
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "id", "status", "offer_amount", "final_amount",
            "offer_date", "compromise_date", "signed_date",
            "agent_id", "agent_name", "property_type", "property_city",
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ("" if v is None else v) for k, v in row.items()})
    return Response(
        buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="transactions.csv"'},
    )
