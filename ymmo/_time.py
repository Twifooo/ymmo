"""Helper temps : remplace `datetime.utcnow()` (déprécié à partir de Python 3.12).

On stocke en BDD en naïf UTC pour rester compatible avec les colonnes
``db.DateTime`` existantes (sans tzinfo). Tout passe par cet alias :
- ``utcnow()`` pour les ``default=`` et ``onupdate=`` SQLAlchemy,
- ``utcnow()`` aussi côté services (services/transaction_service.py).

Si on migrait vers ``DateTime(timezone=True)``, on adapterait juste cette
fonction sans toucher au reste de l'app.
"""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Maintenant en UTC, sans tzinfo (pour rester compatible BDD)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
