"""Espace client : favoris, demandes de visite, transactions, messages."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..decorators import role_required
from ..extensions import db
from ..forms import ContactAgencyForm, VisitRequestForm
from ..models import Message, UserRole
from ..repositories import PropertyRepository, TransactionRepository
from ..services import PropertyError, PropertyService

client_bp = Blueprint("client", __name__)


@client_bp.before_request
@login_required
def _require_login():
    pass


@client_bp.route("/")
@role_required(UserRole.CLIENT, UserRole.ADMIN)
def dashboard():
    favorites = current_user.favorites
    visits = current_user.visit_requests
    transactions = TransactionRepository.list_for_buyer(current_user.id)
    return render_template(
        "client/dashboard.html",
        favorites=favorites,
        visits=visits,
        transactions=transactions,
    )


@client_bp.route("/favoris/<int:property_id>", methods=["POST"])
@role_required(UserRole.CLIENT, UserRole.ADMIN)
def toggle_favorite(property_id: int):
    added = PropertyService.toggle_favorite(current_user, property_id)
    flash("Ajouté à vos favoris." if added else "Retiré de vos favoris.", "info")
    return redirect(request.referrer or url_for("public.property_detail", property_id=property_id))


@client_bp.route("/visite/<int:property_id>", methods=["GET", "POST"])
@role_required(UserRole.CLIENT, UserRole.ADMIN)
def request_visit(property_id: int):
    prop = PropertyRepository.get(property_id)
    if not prop:
        abort(404)
    form = VisitRequestForm()
    if form.validate_on_submit():
        try:
            PropertyService.request_visit(
                current_user,
                property_id=property_id,
                message=form.message.data,
                preferred_date=form.preferred_date.data,
            )
        except PropertyError as exc:
            flash(str(exc), "error")
        else:
            flash("Votre demande de visite a bien été envoyée.", "success")
            return redirect(url_for("client.dashboard"))
    return render_template("client/visit_request.html", form=form, prop=prop)


@client_bp.route("/contact/<int:property_id>", methods=["GET", "POST"])
@role_required(UserRole.CLIENT, UserRole.ADMIN)
def contact_agency(property_id: int):
    prop = PropertyRepository.get(property_id)
    if not prop:
        abort(404)
    form = ContactAgencyForm()
    if form.validate_on_submit():
        message = Message(
            sender_id=current_user.id,
            recipient_id=prop.agent_id,
            property_id=prop.id,
            subject=form.subject.data,
            body=form.body.data,
        )
        db.session.add(message)
        db.session.commit()
        flash("Message envoyé à l'agence.", "success")
        return redirect(url_for("public.property_detail", property_id=prop.id))
    form.subject.data = form.subject.data or f"Demande d'information : {prop.title}"
    return render_template("client/contact.html", form=form, prop=prop)
