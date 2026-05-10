"""Modèles SQLAlchemy.

Importer ce module garantit que toutes les tables sont enregistrées
auprès du metadata avant `db.create_all()`.
"""

from .agency import Agency
from .favorite import Favorite
from .message import Message
from .property import Property, PropertyImage, PropertyStatus, PropertyType
from .saved_search import SavedSearch
from .transaction import Transaction, TransactionStatus
from .user import User, UserRole
from .visit_request import VisitRequest, VisitStatus

__all__ = [
    "Agency",
    "Favorite",
    "Message",
    "Property",
    "PropertyImage",
    "PropertyStatus",
    "PropertyType",
    "SavedSearch",
    "Transaction",
    "TransactionStatus",
    "User",
    "UserRole",
    "VisitRequest",
    "VisitStatus",
]
