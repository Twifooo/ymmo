"""API JSON.

Standardisée à la mode REST : réponses JSON, headers de pagination
(X-Total-Count / X-Page / X-Per-Page) sur les endpoints paginés,
endpoint /health pour les checks de déploiement.
Tous les endpoints publics ne nécessitent pas d'auth ; /alerts si.
"""

from __future__ import annotations

import time

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import text

from .. import APP_STARTED_AT, APP_VERSION
from ..extensions import csrf, db
from ..models import PropertyType
from ..repositories import PropertyRepository
from ..repositories.property_repository import PropertySearchCriteria
from ..services import SavedSearchService

api_bp = Blueprint("api", __name__)
csrf.exempt(api_bp)


def _analytics():
    return current_app.extensions["analytics"]


@api_bp.get("/health")
def health():
    """Sonde de déploiement : vérifie que la BDD répond et renvoie l'uptime."""
    db_status = "ok"
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_status = f"error: {exc}"
    payload = {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": APP_VERSION,
        "uptime_s": round(time.time() - APP_STARTED_AT, 1),
        "database": db_status,
    }
    code = 200 if db_status == "ok" else 503
    return jsonify(payload), code


@api_bp.get("/properties")
def search_properties():
    criteria = PropertySearchCriteria(
        keyword=request.args.get("q"),
        city=request.args.get("city"),
        property_type=PropertyType(request.args["type"]) if request.args.get("type") else None,
        min_price=request.args.get("min_price", type=float),
        max_price=request.args.get("max_price", type=float),
        min_surface=request.args.get("min_surface", type=float),
        min_rooms=request.args.get("min_rooms", type=int),
        page=request.args.get("page", default=1, type=int),
        per_page=min(request.args.get("per_page", default=12, type=int), 50),
        sort=request.args.get("sort", "recent"),
    )
    items, total = PropertyRepository.search(criteria)
    response = jsonify(
        {
            "total": total,
            "page": criteria.page,
            "per_page": criteria.per_page,
            "items": [
                {
                    "id": p.id,
                    "title": p.title,
                    "type": p.type.value,
                    "status": p.status.value,
                    "price": float(p.price),
                    "surface": p.surface,
                    "rooms": p.rooms,
                    "city": p.city,
                    "postal_code": p.postal_code,
                    "latitude": p.latitude,
                    "longitude": p.longitude,
                    "image": p.main_image_url,
                    "url": f"/biens/{p.id}",
                }
                for p in items
            ],
        }
    )
    # Headers REST standards : utiles pour des intégrations tierces.
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(criteria.page)
    response.headers["X-Per-Page"] = str(criteria.per_page)
    return response


@api_bp.get("/dashboard")
def dashboard():
    return jsonify(_analytics().dashboard())


@api_bp.post("/estimate")
def estimate():
    payload = request.get_json(silent=True) or {}
    required = {"type", "city", "surface", "rooms"}
    missing = required - payload.keys()
    if missing:
        return jsonify({"error": f"Champs manquants : {sorted(missing)}"}), 400
    try:
        result = _analytics().predict_price(payload)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    return jsonify(result)


@api_bp.get("/alerts")
@login_required
def alerts():
    """Renvoie le nombre de nouveaux biens correspondant aux recherches
    sauvegardées du client connecté. Sert au badge de la topbar.
    """
    if not current_user.is_client:
        return jsonify({"count": 0, "items": []})
    return jsonify({
        "count": SavedSearchService.count_new_matches(current_user),
        "items": SavedSearchService.details(current_user),
    })
