"""Espace agent : gestion des biens, demandes de visite, transactions, KPIs."""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

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
from flask_login import current_user, login_required

from .._time import utcnow
from ..decorators import role_required
from ..extensions import db
from ..forms import PropertyForm
from ..models import (
    PropertyStatus,
    Transaction,
    TransactionStatus,
    UserRole,
    VisitRequest,
    VisitStatus,
)
from ..repositories import PropertyRepository, TransactionRepository
from ..services import PropertyError, PropertyService, TransactionService

agent_bp = Blueprint("agent", __name__)


def _analytics():
    return current_app.extensions["analytics"]


@agent_bp.before_request
@login_required
def _require_login():
    pass


@agent_bp.route("/")
@role_required(UserRole.AGENT, UserRole.ADMIN)
def dashboard():
    page = max(1, request.args.get("page", default=1, type=int))
    query = request.args.get("q", default="", type=str).strip() or None
    properties, total = PropertyRepository.list_for_agent_paginated(
        current_user.id, page=page, per_page=10, query=query
    )
    pages = max(1, -(-total // 10))

    visits = (
        db.session.query(VisitRequest)
        .filter(VisitRequest.property_id.in_([p.id for p in properties]))
        .order_by(VisitRequest.requested_at.desc())
        .all()
        if properties
        else []
    )
    transactions = TransactionRepository.list_for_agent(current_user.id)
    dashboard_data = _analytics().dashboard()
    anomaly_ids = _analytics().anomalies_for_agent(current_user.id)
    return render_template(
        "agent/dashboard.html",
        properties=properties,
        properties_total=total,
        properties_page=page,
        properties_pages=pages,
        properties_query=query or "",
        visits=visits,
        transactions=transactions,
        dashboard=dashboard_data,
        anomaly_ids=anomaly_ids,
    )


@agent_bp.route("/calendrier")
@role_required(UserRole.AGENT, UserRole.ADMIN)
def calendar():
    """Vue hebdomadaire des visites confirmées de l'agent."""
    start_offset = request.args.get("offset", default=0, type=int)
    today = utcnow().date()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=start_offset)
    days = [monday + timedelta(days=i) for i in range(7)]

    my_props = PropertyRepository.list_for_agent(current_user.id)
    my_prop_ids = [p.id for p in my_props]

    visits = (
        db.session.query(VisitRequest)
        .filter(
            VisitRequest.property_id.in_(my_prop_ids),
            VisitRequest.preferred_date.isnot(None),
            VisitRequest.preferred_date >= monday,
            VisitRequest.preferred_date < monday + timedelta(days=7),
        )
        .order_by(VisitRequest.preferred_date)
        .all()
        if my_prop_ids
        else []
    )

    # Regroupement par jour pour la grille calendrier.
    by_day: dict[str, list[VisitRequest]] = defaultdict(list)
    for v in visits:
        by_day[v.preferred_date.date().isoformat()].append(v)

    return render_template(
        "agent/calendar.html",
        days=days,
        by_day=by_day,
        offset=start_offset,
    )


@agent_bp.route("/biens/<int:property_id>/favoris")
@role_required(UserRole.AGENT, UserRole.ADMIN)
def property_favorites(property_id: int):
    """Liste des clients ayant ajouté ce bien à leurs favoris."""
    prop = PropertyRepository.get(property_id)
    if not prop:
        abort(404)
    if not (current_user.is_admin or prop.agent_id == current_user.id):
        abort(403)
    return render_template(
        "agent/property_favorites.html",
        prop=prop,
        favorites=PropertyService.favorited_by(prop),
    )


@agent_bp.route("/biens/nouveau", methods=["GET", "POST"])
@role_required(UserRole.AGENT, UserRole.ADMIN)
def create_property():
    form = PropertyForm()
    if form.validate_on_submit():
        try:
            prop = PropertyService.create(agent=current_user, data=_form_data(form))
        except PropertyError as exc:
            flash(str(exc), "error")
        else:
            files = request.files.getlist("images")
            report = PropertyService.attach_images(prop, files)
            if report.rejected:
                for name, reason in report.rejected:
                    flash(f"Image refusée — {name} : {reason}.", "warning")
            _analytics().reset_predictor()
            flash(
                f"Bien créé avec succès ({report.saved} photo(s) ajoutée(s)).",
                "success",
            )
            return redirect(url_for("agent.dashboard"))
    return render_template("agent/property_form.html", form=form, prop=None)


@agent_bp.route("/biens/<int:property_id>/edition", methods=["GET", "POST"])
@role_required(UserRole.AGENT, UserRole.ADMIN)
def edit_property(property_id: int):
    prop = PropertyRepository.get(property_id)
    if not prop:
        abort(404)
    form = PropertyForm(obj=prop)
    if request.method == "GET":
        form.type.data = prop.type.value
        form.status.data = prop.status.value
    if form.validate_on_submit():
        try:
            PropertyService.update(prop, actor=current_user, data=_form_data(form))
        except PropertyError as exc:
            flash(str(exc), "error")
        else:
            files = request.files.getlist("images")
            report = PropertyService.attach_images(prop, files)
            if report.rejected:
                for name, reason in report.rejected:
                    flash(f"Image refusée — {name} : {reason}.", "warning")
            _analytics().reset_predictor()
            flash(
                f"Bien mis à jour ({report.saved} photo(s) ajoutée(s)).",
                "success",
            )
            return redirect(url_for("agent.dashboard"))
    return render_template("agent/property_form.html", form=form, prop=prop)


@agent_bp.route("/biens/<int:property_id>/supprimer", methods=["POST"])
@role_required(UserRole.AGENT, UserRole.ADMIN)
def delete_property(property_id: int):
    prop = PropertyRepository.get(property_id)
    if not prop:
        abort(404)
    try:
        PropertyService.delete(prop, actor=current_user)
    except PropertyError as exc:
        flash(str(exc), "error")
    else:
        _analytics().reset_predictor()
        flash("Bien supprimé.", "success")
    return redirect(url_for("agent.dashboard"))


@agent_bp.route("/biens/bulk", methods=["POST"])
@role_required(UserRole.AGENT, UserRole.ADMIN)
def bulk_update():
    """Met à jour le statut de plusieurs biens en une action."""
    ids = request.form.getlist("property_ids", type=int)
    new_status = request.form.get("new_status", "")
    if new_status not in {s.value for s in PropertyStatus}:
        flash("Statut invalide.", "error")
        return redirect(url_for("agent.dashboard"))
    if not ids:
        flash("Sélectionnez au moins un bien.", "warning")
        return redirect(url_for("agent.dashboard"))
    # Sécurité : un agent (non admin) ne peut toucher qu'à ses biens.
    agent_filter = None if current_user.is_admin else current_user.id
    n = PropertyRepository.bulk_update_status(ids, new_status, agent_id=agent_filter)
    _analytics().reset_predictor()
    flash(f"{n} bien(s) mis à jour ({PropertyStatus(new_status).label}).", "success")
    return redirect(url_for("agent.dashboard"))


@agent_bp.route("/visites/<int:visit_id>/<string:action>", methods=["POST"])
@role_required(UserRole.AGENT, UserRole.ADMIN)
def update_visit(visit_id: int, action: str):
    visit = db.session.get(VisitRequest, visit_id)
    if not visit:
        abort(404)
    mapping = {
        "confirmer": VisitStatus.CONFIRMED,
        "terminer": VisitStatus.DONE,
        "annuler": VisitStatus.CANCELLED,
    }
    if action not in mapping:
        abort(400)
    visit.status = mapping[action]
    db.session.commit()
    flash(f"Visite : {visit.status.label}.", "info")
    return redirect(request.referrer or url_for("agent.dashboard"))


@agent_bp.route("/transactions/nouvelle/<int:property_id>", methods=["POST"])
@role_required(UserRole.AGENT, UserRole.ADMIN)
def create_offer(property_id: int):
    prop = PropertyRepository.get(property_id)
    if not prop:
        abort(404)
    buyer_id = request.form.get("buyer_id", type=int)
    amount = request.form.get("amount", type=str)
    if not buyer_id or not amount:
        flash("Acheteur et montant requis.", "error")
        return redirect(url_for("agent.dashboard"))
    from ..repositories import UserRepository

    buyer = UserRepository.get(buyer_id)
    if not buyer or not buyer.is_client:
        flash("Acheteur invalide.", "error")
        return redirect(url_for("agent.dashboard"))
    TransactionService.create_offer(prop, buyer, Decimal(amount))
    flash("Offre enregistrée.", "success")
    return redirect(url_for("agent.dashboard"))


@agent_bp.route("/transactions/<int:transaction_id>/<string:status>", methods=["POST"])
@role_required(UserRole.AGENT, UserRole.ADMIN)
def progress_transaction(transaction_id: int, status: str):
    tr = db.session.get(Transaction, transaction_id)
    if not tr:
        abort(404)
    try:
        TransactionService.progress(tr, TransactionStatus(status))
    except ValueError:
        abort(400)
    flash("Statut de transaction mis à jour.", "info")
    return redirect(url_for("agent.dashboard"))


@agent_bp.route("/exports/biens.csv")
@role_required(UserRole.AGENT, UserRole.ADMIN)
def export_properties_csv():
    """Export CSV des biens de l'agent (ou de tous les biens pour admin)."""
    properties = (
        PropertyRepository.list_for_agent(current_user.id)
        if not current_user.is_admin
        else db.session.query(__import__("ymmo.models", fromlist=["Property"]).Property).all()
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["id", "title", "type", "status", "price", "surface", "rooms", "city", "postal_code", "views"]
    )
    for p in properties:
        writer.writerow(
            [p.id, p.title, p.type.value, p.status.value, float(p.price),
             p.surface, p.rooms, p.city, p.postal_code, p.views_count]
        )
    return Response(
        buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="biens.csv"'},
    )


def _form_data(form: PropertyForm) -> dict:
    return {
        "title": form.title.data,
        "description": form.description.data,
        "type": form.type.data,
        "status": form.status.data,
        "price": form.price.data,
        "surface": float(form.surface.data) if form.surface.data is not None else None,
        "rooms": form.rooms.data,
        "bedrooms": form.bedrooms.data,
        "bathrooms": form.bathrooms.data,
        "floor": form.floor.data,
        "has_parking": form.has_parking.data,
        "has_garden": form.has_garden.data,
        "has_balcony": form.has_balcony.data,
        "energy_class": form.energy_class.data or None,
        "year_built": form.year_built.data,
        "address": form.address.data,
        "city": form.city.data,
        "postal_code": form.postal_code.data,
    }
