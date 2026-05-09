"""Demande de visite ou d'information envoyée par un client à une agence."""

from __future__ import annotations

from enum import Enum

from flask_babel import gettext as _

from .._time import utcnow
from ..extensions import db


class VisitStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DONE = "done"
    CANCELLED = "cancelled"

    @property
    def label(self) -> str:
        return {
            VisitStatus.PENDING: _("En attente"),
            VisitStatus.CONFIRMED: _("Confirmée"),
            VisitStatus.DONE: _("Effectuée"),
            VisitStatus.CANCELLED: _("Annulée"),
        }[self]


class VisitRequest(db.Model):
    __tablename__ = "visit_requests"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(
        db.Integer, db.ForeignKey("properties.id"), nullable=False, index=True
    )
    client_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    requested_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    preferred_date = db.Column(db.DateTime)
    message = db.Column(db.Text, nullable=False, default="")
    status = db.Column(
        db.Enum(VisitStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=VisitStatus.PENDING,
        index=True,
    )

    property = db.relationship("Property", back_populates="visit_requests")
    client = db.relationship(
        "User", back_populates="visit_requests", foreign_keys=[client_id]
    )
