"""Formulaires liés aux biens immobiliers."""

from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    DateTimeLocalField,
    DecimalField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from ..models import PropertyStatus, PropertyType


def _type_choices() -> list[tuple[str, str]]:
    return [(t.value, t.label) for t in PropertyType]


def _status_choices() -> list[tuple[str, str]]:
    return [(s.value, s.label) for s in PropertyStatus]


class PropertySearchForm(FlaskForm):
    # Recherche en GET, on ne stocke rien -> CSRF inutile et gênant ici
    # (sinon le bookmark / lien copié casse).
    class Meta:
        csrf = False

    keyword = StringField("Mots-clés", validators=[Optional(), Length(max=120)])
    city = StringField("Ville", validators=[Optional(), Length(max=80)])
    property_type = SelectField(
        "Type",
        choices=[("", "Tous types")] + _type_choices(),
        validators=[Optional()],
    )
    min_price = DecimalField("Prix min", validators=[Optional(), NumberRange(min=0)])
    max_price = DecimalField("Prix max", validators=[Optional(), NumberRange(min=0)])
    min_surface = DecimalField("Surface min (m²)", validators=[Optional(), NumberRange(min=0)])
    min_rooms = IntegerField("Pièces min", validators=[Optional(), NumberRange(min=0)])
    has_parking = BooleanField("Parking")
    has_garden = BooleanField("Jardin")
    sort = SelectField(
        "Trier par",
        choices=[
            ("recent", "Plus récents"),
            ("price_asc", "Prix croissant"),
            ("price_desc", "Prix décroissant"),
            ("surface_desc", "Surface décroissante"),
            ("popular", "Plus consultés"),
        ],
        default="recent",
    )
    submit = SubmitField("Rechercher")


class PropertyForm(FlaskForm):
    title = StringField("Titre", validators=[DataRequired(), Length(max=160)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=4000)])
    type = SelectField("Type", choices=_type_choices(), validators=[DataRequired()])
    status = SelectField(
        "Statut", choices=_status_choices(), validators=[DataRequired()]
    )
    price = DecimalField("Prix (€)", validators=[DataRequired(), NumberRange(min=0)])
    surface = DecimalField("Surface (m²)", validators=[DataRequired(), NumberRange(min=1)])
    rooms = IntegerField("Pièces", validators=[DataRequired(), NumberRange(min=0)])
    bedrooms = IntegerField("Chambres", validators=[Optional(), NumberRange(min=0)])
    bathrooms = IntegerField("Salles de bain", validators=[Optional(), NumberRange(min=0)])
    floor = IntegerField("Étage", validators=[Optional(), NumberRange(min=-3, max=50)])
    has_parking = BooleanField("Parking")
    has_garden = BooleanField("Jardin")
    has_balcony = BooleanField("Balcon")
    energy_class = SelectField(
        "Classe énergie",
        choices=[("", "—")] + [(c, c) for c in ["A", "B", "C", "D", "E", "F", "G"]],
        validators=[Optional()],
    )
    year_built = IntegerField(
        "Année de construction", validators=[Optional(), NumberRange(min=1700, max=2100)]
    )
    address = StringField("Adresse", validators=[DataRequired(), Length(max=255)])
    city = StringField("Ville", validators=[DataRequired(), Length(max=120)])
    postal_code = StringField(
        "Code postal", validators=[DataRequired(), Length(min=4, max=10)]
    )
    images = FileField(
        "Photos",
        validators=[
            FileAllowed(
                ["png", "jpg", "jpeg", "webp"],
                "Formats acceptés : PNG, JPG, WEBP.",
            )
        ],
        render_kw={"multiple": True, "accept": "image/*"},
    )
    submit = SubmitField("Enregistrer")


class VisitRequestForm(FlaskForm):
    preferred_date = DateTimeLocalField(
        "Date souhaitée", format="%Y-%m-%dT%H:%M", validators=[Optional()]
    )
    message = TextAreaField(
        "Message",
        validators=[DataRequired(), Length(min=10, max=1000)],
        render_kw={"rows": 4, "placeholder": "Présentez votre projet en quelques mots."},
    )
    submit = SubmitField("Envoyer la demande")


class ContactAgencyForm(FlaskForm):
    subject = StringField("Sujet", validators=[DataRequired(), Length(max=255)])
    body = TextAreaField(
        "Message",
        validators=[DataRequired(), Length(min=10, max=2000)],
        render_kw={"rows": 5},
    )
    submit = SubmitField("Envoyer")


class PriceEstimationForm(FlaskForm):
    """Estimateur de prix. CSRF activé car on poste depuis un formulaire utilisateur."""

    type = SelectField("Type", choices=_type_choices(), validators=[DataRequired()])
    city = StringField("Ville", validators=[DataRequired(), Length(max=120)])
    surface = DecimalField("Surface (m²)", validators=[DataRequired(), NumberRange(min=5)])
    rooms = IntegerField("Pièces", validators=[DataRequired(), NumberRange(min=1)])
    bedrooms = IntegerField("Chambres", validators=[Optional(), NumberRange(min=0)])
    bathrooms = IntegerField("Salles de bain", validators=[Optional(), NumberRange(min=0)])
    has_parking = BooleanField("Parking")
    has_garden = BooleanField("Jardin")
    has_balcony = BooleanField("Balcon")
    submit = SubmitField("Estimer")


class SavedSearchForm(FlaskForm):
    """Création / mise à jour d'une alerte client."""

    label = StringField("Libellé", validators=[DataRequired(), Length(max=120)])
    city = StringField("Ville", validators=[Optional(), Length(max=120)])
    property_type = SelectField(
        "Type",
        choices=[("", "Indifférent")] + _type_choices(),
        validators=[Optional()],
    )
    max_price = DecimalField("Prix max (€)", validators=[Optional(), NumberRange(min=0)])
    min_surface = DecimalField("Surface min (m²)", validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField("Créer l'alerte")
