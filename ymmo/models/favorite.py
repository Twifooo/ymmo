"""Liste des biens mis en favoris par un client."""

from __future__ import annotations

from datetime import datetime

from ..extensions import db


class Favorite(db.Model):
    __tablename__ = "favorites"
    __table_args__ = (db.UniqueConstraint("user_id", "property_id", name="uq_user_property"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    property_id = db.Column(
        db.Integer, db.ForeignKey("properties.id"), nullable=False, index=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="favorites")
    property = db.relationship("Property", back_populates="favorites")
