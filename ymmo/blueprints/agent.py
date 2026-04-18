"""Espace agent : gestion des biens, demandes de visite, transactions, KPIs."""

from __future__ import annotations

from decimal import Decimal

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..decorators import role_required
from ..extensions import db
from ..forms import PropertyForm
from ..models import (
    Transaction,
    TransactionStatus,
    UserRole,
    VisitRequest,
    VisitStatus,
)
from ..repositories import PropertyRepository, TransactionRepository
from ..services import AnalyticsService, PropertyError, PropertyService, TransactionService

agent_bp = Blueprint("agent", __name__)
analytics_service = AnalyticsService()


@agent_bp.before_request
@login_required
def _require_login():
    pass


@agent_bp.route("/")
@role_required(UserRole.AGENT, UserRole.ADMIN)
def dashboard():
    properties = PropertyRepository.list_for_agent(current_user.id)
    visits = (
        db.session.query(VisitRequest)
        .filter(VisitRequest.property_id.in_([p.id for p in properties]))
        .order_by(VisitRequest.requested_at.desc())
        .all()
        if properties
        else []
    )
    transactions = TransactionRepository.list_for_agent(current_user.id)
    dashboard_data = analytics_service.dashboard()
    return render_template(
        "agent/dashboard.html",
        properties=properties,
        visits=visits,
        transactions=transactions,
        dashboard=dashboard_data,
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
            PropertyService.attach_images(prop, files)
            analytics_service.reset_predictor()
            flash("Bien créé avec succès.", "success")
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
            PropertyService.attach_images(prop, files)
            analytics_service.reset_predictor()
            flash("Bien mis à jour.", "success")
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
        analytics_service.reset_predictor()
        flash("Bien supprimé.", "success")
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
    return redirect(url_for("agent.dashboard"))


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
