"""API JSON minimale.

Sert de base à des extensions futures (mobile, intégration tierce) et
illustre la séparation présentation / données. Les endpoints publics
ne nécessitent pas d'authentification, l'estimation utilise le modèle ML.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..extensions import csrf
from ..models import PropertyType
from ..repositories import PropertyRepository
from ..repositories.property_repository import PropertySearchCriteria
from ..services import AnalyticsService

api_bp = Blueprint("api", __name__)
csrf.exempt(api_bp)
analytics_service = AnalyticsService()


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
    return jsonify(
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
                    "image": p.main_image_url,
                    "url": f"/biens/{p.id}",
                }
                for p in items
            ],
        }
    )


@api_bp.get("/dashboard")
def dashboard():
    return jsonify(analytics_service.dashboard())


@api_bp.post("/estimate")
def estimate():
    payload = request.get_json(silent=True) or {}
    required = {"type", "city", "surface", "rooms"}
    missing = required - payload.keys()
    if missing:
        return jsonify({"error": f"Champs manquants : {sorted(missing)}"}), 400
    try:
        result = analytics_service.predict_price(payload)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    return jsonify(result)
