"""Transaction immobilière (vente).

Permet de suivre l'avancement entre l'offre, le compromis et l'acte
authentique pour produire les indicateurs métier.
"""

from __future__ import annotations

from enum import Enum

from flask_babel import gettext as _

from .._time import utcnow
from ..extensions import db


class TransactionStatus(str, Enum):
    OFFER = "offer"
    COMPROMISE = "compromise"
    SIGNED = "signed"
    CANCELLED = "cancelled"

    @property
    def label(self) -> str:
        return {
            TransactionStatus.OFFER: _("Offre déposée"),
            TransactionStatus.COMPROMISE: _("Compromis signé"),
            TransactionStatus.SIGNED: _("Acte authentique"),
            TransactionStatus.CANCELLED: _("Annulée"),
        }[self]


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(
        db.Integer, db.ForeignKey("properties.id"), nullable=False, index=True
    )
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    offer_amount = db.Column(db.Numeric(12, 2), nullable=False)
    final_amount = db.Column(db.Numeric(12, 2))
    status = db.Column(
        db.Enum(TransactionStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TransactionStatus.OFFER,
        index=True,
    )

    offer_date = db.Column(db.DateTime, default=utcnow, nullable=False)
    compromise_date = db.Column(db.DateTime)
    signed_date = db.Column(db.DateTime)
    notes = db.Column(db.Text, default="")

    property = db.relationship("Property", back_populates="transactions")
    buyer = db.relationship("User", foreign_keys=[buyer_id])
    agent = db.relationship("User", foreign_keys=[agent_id])
