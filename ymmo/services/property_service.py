"""Service métier des biens immobiliers."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flask import current_app
from markupsafe import escape
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import (
    Favorite,
    Property,
    PropertyImage,
    PropertyStatus,
    PropertyType,
    User,
    UserRole,
    VisitRequest,
    VisitStatus,
)
from ..repositories import PropertyRepository
from ..repositories.property_repository import PropertySearchCriteria


class PropertyError(Exception):
    """Erreur métier liée à un bien."""


@dataclass
class UploadReport:
    """Compte-rendu d'un upload multi-fichiers : combien acceptés, rejetés et pourquoi."""

    saved: int = 0
    rejected: list[tuple[str, str]] = None  # (filename, reason)

    def __post_init__(self) -> None:
        if self.rejected is None:
            self.rejected = []


class PropertyService:
    @staticmethod
    def search(criteria: PropertySearchCriteria) -> tuple[list[Property], int]:
        return PropertyRepository.search(criteria)

    @staticmethod
    def get_or_404(property_id: int) -> Property:
        prop = PropertyRepository.get(property_id)
        if not prop:
            raise PropertyError("Bien introuvable.")
        return prop

    @staticmethod
    def view(property_id: int) -> Property:
        prop = PropertyService.get_or_404(property_id)
        PropertyRepository.increment_views(property_id)
        return prop

    @staticmethod
    def create(*, agent: User, data: dict[str, Any]) -> Property:
        if agent.role not in (UserRole.AGENT, UserRole.ADMIN):
            raise PropertyError("Seul un agent ou un administrateur peut créer un bien.")
        if not agent.agency_id and not data.get("agency_id"):
            raise PropertyError("L'agent doit être rattaché à une agence.")

        prop = Property(
            title=data["title"],
            description=data.get("description", ""),
            type=PropertyType(data["type"]),
            status=PropertyStatus(data.get("status", PropertyStatus.AVAILABLE.value)),
            price=data["price"],
            surface=data["surface"],
            rooms=data.get("rooms", 1),
            bedrooms=data.get("bedrooms", 0),
            bathrooms=data.get("bathrooms", 0),
            floor=data.get("floor"),
            has_parking=bool(data.get("has_parking")),
            has_garden=bool(data.get("has_garden")),
            has_balcony=bool(data.get("has_balcony")),
            energy_class=data.get("energy_class"),
            year_built=data.get("year_built"),
            address=data["address"],
            city=data["city"],
            postal_code=data["postal_code"],
            agent_id=agent.id,
            agency_id=data.get("agency_id") or agent.agency_id,
        )
        return PropertyRepository.add(prop)

    @staticmethod
    def update(prop: Property, *, actor: User, data: dict[str, Any]) -> Property:
        PropertyService._authorize_modify(prop, actor)
        for field in (
            "title",
            "description",
            "price",
            "surface",
            "rooms",
            "bedrooms",
            "bathrooms",
            "floor",
            "energy_class",
            "year_built",
            "address",
            "city",
            "postal_code",
        ):
            if field in data and data[field] is not None:
                setattr(prop, field, data[field])

        for boolean_field in ("has_parking", "has_garden", "has_balcony"):
            if boolean_field in data:
                setattr(prop, boolean_field, bool(data[boolean_field]))

        if "type" in data and data["type"]:
            prop.type = PropertyType(data["type"])
        if "status" in data and data["status"]:
            prop.status = PropertyStatus(data["status"])

        PropertyRepository.save()
        return prop

    @staticmethod
    def delete(prop: Property, *, actor: User) -> None:
        PropertyService._authorize_modify(prop, actor)
        PropertyRepository.delete(prop)

    @staticmethod
    def _authorize_modify(prop: Property, actor: User) -> None:
        if actor.is_admin:
            return
        if actor.role == UserRole.AGENT and prop.agent_id == actor.id:
            return
        raise PropertyError("Action non autorisée sur ce bien.")

    @staticmethod
    def attach_images(prop: Property, files: list[FileStorage]) -> UploadReport:
        """Sauvegarde les images uploadées et renvoie un rapport détaillé.

        Avant : silencieux, l'utilisateur ne voyait pas les rejets.
        Maintenant : on remonte ``saved`` + liste des rejets pour que le
        blueprint puisse flasher un message clair.
        """
        allowed = current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
        upload_dir: Path = current_app.config["UPLOAD_FOLDER"]
        upload_dir.mkdir(parents=True, exist_ok=True)

        report = UploadReport()
        # On sanitise le titre du bien avant de l'utiliser dans alt_text :
        # un titre malveillant pourrait contenir du HTML qu'on stockerait brut.
        safe_title = escape(prop.title or "")[:200]

        for file in files:
            if not file or not file.filename:
                continue
            ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
            if ext not in allowed:
                report.rejected.append((file.filename, "format non supporté"))
                continue
            # Limite individuelle : 4 Mo (au-delà, on refuse pour ne pas saturer).
            file.seek(0, 2)
            size = file.tell()
            file.seek(0)
            if size > 4 * 1024 * 1024:
                report.rejected.append((file.filename, "fichier > 4 Mo"))
                continue

            unique = f"{secrets.token_hex(8)}_{secure_filename(file.filename)}"
            path = upload_dir / unique
            try:
                file.save(path)
            except OSError as exc:
                report.rejected.append((file.filename, f"écriture impossible : {exc}"))
                continue

            db.session.add(
                PropertyImage(
                    property_id=prop.id,
                    url=f"/static/uploads/{unique}",
                    alt_text=f"Photo de {safe_title}",
                    position=len(prop.images),
                )
            )
            report.saved += 1
        if report.saved:
            db.session.commit()
        return report

    @staticmethod
    def toggle_favorite(user: User, property_id: int) -> bool:
        existing = next(
            (f for f in user.favorites if f.property_id == property_id), None
        )
        if existing:
            db.session.delete(existing)
            db.session.commit()
            return False
        db.session.add(Favorite(user_id=user.id, property_id=property_id))
        db.session.commit()
        return True

    @staticmethod
    def request_visit(
        client: User, property_id: int, message: str, preferred_date=None
    ) -> VisitRequest:
        if not client.is_client:
            raise PropertyError("Seul un client peut demander une visite.")
        prop = PropertyService.get_or_404(property_id)
        visit = VisitRequest(
            property_id=prop.id,
            client_id=client.id,
            message=message.strip(),
            preferred_date=preferred_date,
            status=VisitStatus.PENDING,
        )
        db.session.add(visit)
        db.session.commit()
        return visit

    @staticmethod
    def favorited_by(prop: Property) -> list[User]:
        """Liste des clients ayant mis ce bien en favori (vue agent)."""
        return [fav.user for fav in prop.favorites]
