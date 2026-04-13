"""Agence Ymmo : siège ou succursale rattachée.

Le brief mentionne 12 agences + 1 siège ; chacune regroupe des agents
qui sont rattachés à des biens.
"""

from __future__ import annotations

from datetime import datetime

from ..extensions import db


class Agency(db.Model):
    __tablename__ = "agencies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    city = db.Column(db.String(120), nullable=False, index=True)
    postal_code = db.Column(db.String(10), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(30))
    email = db.Column(db.String(255))
    is_headquarters = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    agents = db.relationship("User", back_populates="agency")
    properties = db.relationship("Property", back_populates="agency")

    def __repr__(self) -> str:
        return f"<Agency {self.name}>"
