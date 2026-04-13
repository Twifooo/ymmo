"""Bien immobilier et ses photos.

Un Property est rattaché à une Agency et à un User (agent référent).
Les images sont gérées dans une table séparée pour respecter la 1NF.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from flask_babel import gettext as _

from ..extensions import db


class PropertyType(str, Enum):
    APARTMENT = "apartment"
    HOUSE = "house"
    LAND = "land"
    COMMERCIAL = "commercial"
    OFFICE = "office"

    @property
    def label(self) -> str:
        return {
            PropertyType.APARTMENT: _("Appartement"),
            PropertyType.HOUSE: _("Maison"),
            PropertyType.LAND: _("Terrain"),
            PropertyType.COMMERCIAL: _("Local commercial"),
            PropertyType.OFFICE: _("Bureaux"),
        }[self]


class PropertyStatus(str, Enum):
    DRAFT = "draft"
    AVAILABLE = "available"
    UNDER_OFFER = "under_offer"
    SOLD = "sold"
    WITHDRAWN = "withdrawn"

    @property
    def label(self) -> str:
        return {
            PropertyStatus.DRAFT: _("Brouillon"),
            PropertyStatus.AVAILABLE: _("Disponible"),
            PropertyStatus.UNDER_OFFER: _("Sous compromis"),
            PropertyStatus.SOLD: _("Vendu"),
            PropertyStatus.WITHDRAWN: _("Retiré"),
        }[self]


class Property(db.Model):
    __tablename__ = "properties"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")

    type = db.Column(
        db.Enum(PropertyType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    status = db.Column(
        db.Enum(PropertyStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=PropertyStatus.AVAILABLE,
        index=True,
    )

    price = db.Column(db.Numeric(12, 2), nullable=False, index=True)
    surface = db.Column(db.Float, nullable=False, index=True)
    rooms = db.Column(db.Integer, nullable=False, default=1)
    bedrooms = db.Column(db.Integer, nullable=False, default=0)
    bathrooms = db.Column(db.Integer, nullable=False, default=0)
    floor = db.Column(db.Integer)
    has_parking = db.Column(db.Boolean, nullable=False, default=False)
    has_garden = db.Column(db.Boolean, nullable=False, default=False)
    has_balcony = db.Column(db.Boolean, nullable=False, default=False)
    energy_class = db.Column(db.String(2))
    year_built = db.Column(db.Integer)

    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(120), nullable=False, index=True)
    postal_code = db.Column(db.String(10), nullable=False, index=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    views_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    agency_id = db.Column(db.Integer, db.ForeignKey("agencies.id"), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    agency = db.relationship("Agency", back_populates="properties")
    agent = db.relationship("User", back_populates="properties", foreign_keys=[agent_id])
    images = db.relationship(
        "PropertyImage", back_populates="property", cascade="all, delete-orphan"
    )
    visit_requests = db.relationship(
        "VisitRequest", back_populates="property", cascade="all, delete-orphan"
    )
    favorites = db.relationship(
        "Favorite", back_populates="property", cascade="all, delete-orphan"
    )
    transactions = db.relationship("Transaction", back_populates="property")

    @property
    def price_per_sqm(self) -> float:
        if not self.surface:
            return 0.0
        return float(self.price) / self.surface

    @property
    def main_image_url(self) -> str:
        if self.images:
            return self.images[0].url
        return "/static/images/placeholder.svg"

    def __repr__(self) -> str:
        return f"<Property {self.id} {self.title!r} {self.price}€>"


class PropertyImage(db.Model):
    __tablename__ = "property_images"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(
        db.Integer, db.ForeignKey("properties.id"), nullable=False, index=True
    )
    url = db.Column(db.String(500), nullable=False)
    alt_text = db.Column(db.String(255), nullable=False, default="")
    position = db.Column(db.Integer, nullable=False, default=0)

    property = db.relationship("Property", back_populates="images")
