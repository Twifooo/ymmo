"""Repository agences."""

from __future__ import annotations

from sqlalchemy import select

from ..extensions import db
from ..models import Agency


class AgencyRepository:
    @staticmethod
    def get(agency_id: int) -> Agency | None:
        return db.session.get(Agency, agency_id)

    @staticmethod
    def list_all() -> list[Agency]:
        stmt = select(Agency).order_by(Agency.is_headquarters.desc(), Agency.city)
        return list(db.session.scalars(stmt))

    @staticmethod
    def add(agency: Agency) -> Agency:
        db.session.add(agency)
        db.session.commit()
        return agency
