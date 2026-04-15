"""Services métier.

Les services contiennent la logique du domaine, indépendamment du
transport HTTP. Un service peut être appelé depuis un blueprint web,
une commande CLI ou un test sans modification.
"""

from .auth_service import AuthService, AuthError
from .property_service import PropertyService, PropertyError
from .transaction_service import TransactionService
from .analytics_service import AnalyticsService

__all__ = [
    "AnalyticsService",
    "AuthError",
    "AuthService",
    "PropertyError",
    "PropertyService",
    "TransactionService",
]
