"""Service des recherches sauvegardées et des alertes nouveaux biens.

Quand un client crée une alerte, on enregistre ses critères. Sur sa
prochaine connexion (ou via /api/alerts), on compte combien de NOUVEAUX
biens "available" correspondent depuis sa dernière consultation.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from .._time import utcnow
from ..extensions import db
from ..models import SavedSearch, User


class SavedSearchService:
    @staticmethod
    def list_for(user: User) -> list[SavedSearch]:
        return list(user.saved_searches)

    @staticmethod
    def create(user: User, label: str, **kwargs: Any) -> SavedSearch:
        s = SavedSearch(
            user_id=user.id,
            label=(label or "Ma recherche")[:120],
            city=kwargs.get("city") or None,
            property_type=kwargs.get("property_type") or None,
            max_price=kwargs.get("max_price"),
            min_surface=kwargs.get("min_surface"),
        )
        db.session.add(s)
        db.session.commit()
        return s

    @staticmethod
    def delete(user: User, search_id: int) -> bool:
        s = db.session.get(SavedSearch, search_id)
        if not s or s.user_id != user.id:
            return False
        db.session.delete(s)
        db.session.commit()
        return True

    @staticmethod
    def count_new_matches(user: User) -> int:
        """Nombre cumulé de nouveaux biens depuis la dernière consultation."""
        total = 0
        for search in user.saved_searches:
            where_sql, params = search.matches_query()
            n = db.session.execute(
                text(f"SELECT COUNT(*) FROM properties WHERE {where_sql}"), params
            ).scalar_one()
            total += int(n or 0)
        return total

    @staticmethod
    def details(user: User) -> list[dict[str, Any]]:
        """Pour chaque alerte du client : ses critères + le nombre de nouveaux biens."""
        results: list[dict[str, Any]] = []
        for search in user.saved_searches:
            where_sql, params = search.matches_query()
            n = db.session.execute(
                text(f"SELECT COUNT(*) FROM properties WHERE {where_sql}"), params
            ).scalar_one()
            results.append({
                "id": search.id,
                "label": search.label,
                "city": search.city,
                "property_type": search.property_type,
                "max_price": float(search.max_price) if search.max_price else None,
                "min_surface": search.min_surface,
                "new_matches": int(n or 0),
                "last_seen_at": search.last_seen_at.isoformat() if search.last_seen_at else None,
            })
        return results

    @staticmethod
    def mark_seen(user: User) -> None:
        """Repousse last_seen_at à maintenant : remet le compteur à zéro."""
        now = utcnow()
        for search in user.saved_searches:
            search.last_seen_at = now
        db.session.commit()
