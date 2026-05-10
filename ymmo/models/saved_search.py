"""Recherche sauvegardée d'un client.

Permet de notifier le client (badge en haut de page) quand de nouveaux
biens correspondant à ses critères entrent au catalogue depuis la
dernière fois qu'il a consulté son espace.
"""

from __future__ import annotations

from .._time import utcnow

from ..extensions import db


class SavedSearch(db.Model):
    __tablename__ = "saved_searches"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    label = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(120))
    property_type = db.Column(db.String(40))
    max_price = db.Column(db.Numeric(12, 2))
    min_surface = db.Column(db.Float)

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    last_seen_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("saved_searches", cascade="all, delete-orphan"))

    def matches_query(self):
        """Construit la liste de fragments WHERE (avec params liés) pour
        compter les biens correspondants. Renvoyé par le repository.
        """
        fragments: list[str] = ["status = 'available'", "created_at > :since"]
        params: dict = {"since": self.last_seen_at}
        if self.city:
            fragments.append("LOWER(city) = :city")
            params["city"] = self.city.lower()
        if self.property_type:
            fragments.append("type = :ptype")
            params["ptype"] = self.property_type
        if self.max_price:
            fragments.append("price <= :mp")
            params["mp"] = float(self.max_price)
        if self.min_surface:
            fragments.append("surface >= :ms")
            params["ms"] = float(self.min_surface)
        return " AND ".join(fragments), params
