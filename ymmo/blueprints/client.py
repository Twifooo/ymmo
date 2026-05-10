"""Espace client : favoris, demandes de visite, transactions, messages, alertes."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..decorators import role_required
from ..extensions import db
from ..forms import ContactAgencyForm, SavedSearchForm, VisitRequestForm
from ..models import Message, UserRole
from ..repositories import PropertyRepository, TransactionRepository
from ..services import PropertyError, PropertyService, SavedSearchService

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
    saved_searches = SavedSearchService.details(current_user)
    # Une fois affichées, on remet le compteur d'alertes à 0.
    SavedSearchService.mark_seen(current_user)
    return render_template(
        "client/dashboard.html",
        favorites=favorites,
        visits=visits,
        transactions=transactions,
        saved_searches=saved_searches,
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


# -- Recherches sauvegardées / alertes --------------------------------

@client_bp.route("/alertes", methods=["GET", "POST"])
@role_required(UserRole.CLIENT, UserRole.ADMIN)
def alerts():
    form = SavedSearchForm()
    if form.validate_on_submit():
        SavedSearchService.create(
            current_user,
            label=form.label.data,
            city=form.city.data,
            property_type=form.property_type.data,
            max_price=form.max_price.data,
            min_surface=float(form.min_surface.data) if form.min_surface.data is not None else None,
        )
        flash("Alerte enregistrée. Vous serez notifié(e) à votre prochaine visite.", "success")
        return redirect(url_for("client.alerts"))
    return render_template(
        "client/alerts.html",
        form=form,
        searches=SavedSearchService.details(current_user),
    )


@client_bp.route("/alertes/<int:search_id>/supprimer", methods=["POST"])
@role_required(UserRole.CLIENT, UserRole.ADMIN)
def delete_alert(search_id: int):
    if SavedSearchService.delete(current_user, search_id):
        flash("Alerte supprimée.", "info")
    else:
        flash("Alerte introuvable.", "error")
    return redirect(url_for("client.alerts"))
