"""Couche d'accès aux données.

Les repositories isolent les requêtes SQL du reste de l'application :
- les services consomment les repositories,
- les blueprints n'écrivent jamais de SQL directement.

Les requêtes complexes (recherche multi-critères, agrégations, top-N)
sont écrites en SQL avec ``text()`` et des paramètres liés pour rester
performantes et démontrer la maîtrise de SQL avancé.
"""

from .agency_repository import AgencyRepository
from .property_repository import PropertyRepository
from .transaction_repository import TransactionRepository
from .user_repository import UserRepository

__all__ = [
    "AgencyRepository",
    "PropertyRepository",
    "TransactionRepository",
    "UserRepository",
]
