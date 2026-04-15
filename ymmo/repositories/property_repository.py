"""Repository des biens immobiliers.

On combine ORM (CRUD simple) et SQL textuel pour les requêtes avec
agrégations / classement multi-critères. Toutes les valeurs utilisateur
sont passées via des paramètres liés pour empêcher l'injection SQL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select, text

from ..extensions import db
from ..models import Property, PropertyStatus, PropertyType


@dataclass
class PropertySearchCriteria:
    """Critères de recherche faiblement couplés au transport HTTP."""

    keyword: str | None = None
    city: str | None = None
    postal_code: str | None = None
    property_type: PropertyType | None = None
    min_price: float | None = None
    max_price: float | None = None
    min_surface: float | None = None
    max_surface: float | None = None
    min_rooms: int | None = None
    has_parking: bool | None = None
    has_garden: bool | None = None
    statuses: list[PropertyStatus] = field(
        default_factory=lambda: [PropertyStatus.AVAILABLE]
    )
    page: int = 1
    per_page: int = 12
    sort: str = "recent"


class PropertyRepository:
    SORTS = {
        "recent": "p.created_at DESC",
        "price_asc": "p.price ASC",
        "price_desc": "p.price DESC",
        "surface_desc": "p.surface DESC",
        "popular": "p.views_count DESC",
    }

    @staticmethod
    def get(property_id: int) -> Property | None:
        return db.session.get(Property, property_id)

    @staticmethod
    def add(prop: Property) -> Property:
        db.session.add(prop)
        db.session.commit()
        return prop

    @staticmethod
    def save() -> None:
        db.session.commit()

    @staticmethod
    def delete(prop: Property) -> None:
        db.session.delete(prop)
        db.session.commit()

    @classmethod
    def search(cls, criteria: PropertySearchCriteria) -> tuple[list[Property], int]:
        """Recherche paginée. Retourne (items, total)."""
        where: list[str] = []
        params: dict[str, Any] = {}

        if criteria.statuses:
            placeholders = ",".join(f":status_{i}" for i in range(len(criteria.statuses)))
            where.append(f"p.status IN ({placeholders})")
            for i, status in enumerate(criteria.statuses):
                params[f"status_{i}"] = status.value

        if criteria.keyword:
            where.append("(LOWER(p.title) LIKE :kw OR LOWER(p.description) LIKE :kw)")
            params["kw"] = f"%{criteria.keyword.lower()}%"
        if criteria.city:
            where.append("LOWER(p.city) LIKE :city")
            params["city"] = f"%{criteria.city.lower()}%"
        if criteria.postal_code:
            where.append("p.postal_code LIKE :pc")
            params["pc"] = f"{criteria.postal_code}%"
        if criteria.property_type:
            where.append("p.type = :ptype")
            params["ptype"] = criteria.property_type.value
        if criteria.min_price is not None:
            where.append("p.price >= :min_price")
            params["min_price"] = criteria.min_price
        if criteria.max_price is not None:
            where.append("p.price <= :max_price")
            params["max_price"] = criteria.max_price
        if criteria.min_surface is not None:
            where.append("p.surface >= :min_surface")
            params["min_surface"] = criteria.min_surface
        if criteria.max_surface is not None:
            where.append("p.surface <= :max_surface")
            params["max_surface"] = criteria.max_surface
        if criteria.min_rooms is not None:
            where.append("p.rooms >= :min_rooms")
            params["min_rooms"] = criteria.min_rooms
        if criteria.has_parking:
            where.append("p.has_parking = 1")
        if criteria.has_garden:
            where.append("p.has_garden = 1")

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        order_sql = cls.SORTS.get(criteria.sort, cls.SORTS["recent"])
        offset = max(0, (criteria.page - 1) * criteria.per_page)

        count_sql = text(f"SELECT COUNT(*) FROM properties p {where_sql}")
        total = db.session.execute(count_sql, params).scalar_one()

        ids_sql = text(
            f"""
            SELECT p.id
            FROM properties p
            {where_sql}
            ORDER BY {order_sql}
            LIMIT :limit OFFSET :offset
            """
        )
        params["limit"] = criteria.per_page
        params["offset"] = offset
        ids = [row[0] for row in db.session.execute(ids_sql, params)]
        if not ids:
            return [], total

        ordered = db.session.scalars(
            select(Property).where(Property.id.in_(ids))
        ).all()
        ordered.sort(key=lambda p: ids.index(p.id))
        return list(ordered), total

    @staticmethod
    def increment_views(property_id: int) -> None:
        db.session.execute(
            text("UPDATE properties SET views_count = views_count + 1 WHERE id = :id"),
            {"id": property_id},
        )
        db.session.commit()

    @staticmethod
    def list_for_agent(agent_id: int) -> list[Property]:
        stmt = (
            select(Property)
            .where(Property.agent_id == agent_id)
            .order_by(Property.updated_at.desc())
        )
        return list(db.session.scalars(stmt))

    @staticmethod
    def list_for_agency(agency_id: int) -> list[Property]:
        stmt = (
            select(Property)
            .where(Property.agency_id == agency_id)
            .order_by(Property.updated_at.desc())
        )
        return list(db.session.scalars(stmt))

    @staticmethod
    def top_viewed(limit: int = 5) -> list[Property]:
        stmt = (
            select(Property)
            .where(Property.status == PropertyStatus.AVAILABLE)
            .order_by(Property.views_count.desc())
            .limit(limit)
        )
        return list(db.session.scalars(stmt))

    @staticmethod
    def avg_price_per_city(limit: int = 10) -> list[dict[str, Any]]:
        """Top villes par prix moyen au m². Démontre une agrégation SQL."""
        sql = text(
            """
            SELECT p.city,
                   COUNT(*)                              AS nb,
                   ROUND(AVG(p.price * 1.0 / p.surface), 2) AS avg_price_sqm,
                   ROUND(AVG(p.price), 2)                AS avg_price,
                   ROUND(AVG(p.surface), 2)              AS avg_surface
            FROM properties p
            WHERE p.surface > 0
              AND p.status IN ('available', 'sold', 'under_offer')
            GROUP BY p.city
            HAVING COUNT(*) >= 1
            ORDER BY avg_price_sqm DESC
            LIMIT :limit
            """
        )
        rows = db.session.execute(sql, {"limit": limit})
        return [dict(row._mapping) for row in rows]

    @staticmethod
    def count_by_status() -> dict[str, int]:
        stmt = select(Property.status, func.count(Property.id)).group_by(Property.status)
        return {status.value: nb for status, nb in db.session.execute(stmt)}

    @staticmethod
    def count_by_type() -> dict[str, int]:
        stmt = select(Property.type, func.count(Property.id)).group_by(Property.type)
        return {ptype.value: nb for ptype, nb in db.session.execute(stmt)}

    @staticmethod
    def all_for_dataframe() -> list[dict[str, Any]]:
        """Export brut pour pandas. On garde la requête en SQL natif
        pour pouvoir réutiliser ce flux côté reporting / data team."""
        sql = text(
            """
            SELECT p.id, p.title, p.type, p.status, p.price, p.surface,
                   p.rooms, p.bedrooms, p.bathrooms, p.has_parking,
                   p.has_garden, p.has_balcony, p.energy_class,
                   p.year_built, p.city, p.postal_code, p.views_count,
                   p.created_at, a.name AS agency_name
            FROM properties p
            JOIN agencies a ON a.id = p.agency_id
            """
        )
        return [dict(row._mapping) for row in db.session.execute(sql)]
