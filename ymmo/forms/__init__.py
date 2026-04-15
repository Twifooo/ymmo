"""Formulaires WTForms : validation côté serveur + protection CSRF."""

from .auth_forms import LoginForm, RegisterForm
from .property_forms import (
    ContactAgencyForm,
    PriceEstimationForm,
    PropertyForm,
    PropertySearchForm,
    VisitRequestForm,
)

__all__ = [
    "ContactAgencyForm",
    "LoginForm",
    "PriceEstimationForm",
    "PropertyForm",
    "PropertySearchForm",
    "RegisterForm",
    "VisitRequestForm",
]
