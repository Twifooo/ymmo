"""Service de gestion des transactions."""

from __future__ import annotations

from decimal import Decimal

from .._time import utcnow
from ..extensions import db
from ..models import (
    Property,
    PropertyStatus,
    Transaction,
    TransactionStatus,
    User,
)
from ..repositories import TransactionRepository


class TransactionService:
    @staticmethod
    def create_offer(
        prop: Property, buyer: User, amount: Decimal, notes: str = ""
    ) -> Transaction:
        transaction = Transaction(
            property_id=prop.id,
            buyer_id=buyer.id,
            agent_id=prop.agent_id,
            offer_amount=amount,
            status=TransactionStatus.OFFER,
            notes=notes,
        )
        return TransactionRepository.add(transaction)

    @staticmethod
    def progress(transaction: Transaction, new_status: TransactionStatus) -> Transaction:
        transaction.status = new_status
        now = utcnow()
        if new_status == TransactionStatus.COMPROMISE and not transaction.compromise_date:
            transaction.compromise_date = now
            transaction.property.status = PropertyStatus.UNDER_OFFER
        elif new_status == TransactionStatus.SIGNED:
            transaction.signed_date = transaction.signed_date or now
            transaction.final_amount = transaction.final_amount or transaction.offer_amount
            transaction.property.status = PropertyStatus.SOLD
        elif new_status == TransactionStatus.CANCELLED:
            transaction.property.status = PropertyStatus.AVAILABLE
        db.session.commit()
        return transaction
