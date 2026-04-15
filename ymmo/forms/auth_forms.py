"""Formulaires d'authentification."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


class LoginForm(FlaskForm):
    email = StringField(
        "Adresse email",
        validators=[DataRequired(), Email()],
        render_kw={"autocomplete": "email", "inputmode": "email"},
    )
    password = PasswordField(
        "Mot de passe",
        validators=[DataRequired()],
        render_kw={"autocomplete": "current-password"},
    )
    remember = BooleanField("Se souvenir de moi")
    submit = SubmitField("Se connecter")


class RegisterForm(FlaskForm):
    first_name = StringField(
        "Prénom",
        validators=[DataRequired(), Length(max=80)],
        render_kw={"autocomplete": "given-name"},
    )
    last_name = StringField(
        "Nom",
        validators=[DataRequired(), Length(max=80)],
        render_kw={"autocomplete": "family-name"},
    )
    email = StringField(
        "Adresse email",
        validators=[DataRequired(), Email()],
        render_kw={"autocomplete": "email"},
    )
    phone = StringField(
        "Téléphone",
        validators=[Optional(), Length(max=30)],
        render_kw={"autocomplete": "tel", "inputmode": "tel"},
    )
    password = PasswordField(
        "Mot de passe",
        validators=[DataRequired(), Length(min=8, message="8 caractères minimum.")],
        render_kw={"autocomplete": "new-password"},
    )
    confirm = PasswordField(
        "Confirmer le mot de passe",
        validators=[
            DataRequired(),
            EqualTo("password", message="Les mots de passe ne correspondent pas."),
        ],
        render_kw={"autocomplete": "new-password"},
    )
    submit = SubmitField("Créer mon compte")
