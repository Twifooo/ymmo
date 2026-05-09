"""Message échangé entre un client et un agent à propos d'un bien."""

from __future__ import annotations

from .._time import utcnow

from ..extensions import db


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    recipient_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=True)

    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    read_at = db.Column(db.DateTime)

    sender = db.relationship("User", foreign_keys=[sender_id])
    recipient = db.relationship("User", foreign_keys=[recipient_id])
    property = db.relationship("Property")
