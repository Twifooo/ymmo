"""Repository transactions et indicateurs de pilotage."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select, text

from ..extensions import db
from ..models import Transaction


class TransactionRepository:
    @staticmethod
    def add(transaction: Transaction) -> Transaction:
        db.session.add(transaction)
        db.session.commit()
        return transaction

    @staticmethod
    def get(transaction_id: int) -> Transaction | None:
        return db.session.get(Transaction, transaction_id)

    @staticmethod
    def list_for_buyer(buyer_id: int) -> list[Transaction]:
        stmt = (
            select(Transaction)
            .where(Transaction.buyer_id == buyer_id)
            .order_by(Transaction.offer_date.desc())
        )
        return list(db.session.scalars(stmt))

    @staticmethod
    def list_for_agent(agent_id: int) -> list[Transaction]:
        stmt = (
            select(Transaction)
            .where(Transaction.agent_id == agent_id)
            .order_by(Transaction.offer_date.desc())
        )
        return list(db.session.scalars(stmt))

    @staticmethod
    def monthly_revenue(year: int) -> list[dict[str, Any]]:
        """Chiffre d'affaires signé par mois pour l'année donnée."""
        sql = text(
            """
            SELECT CAST(strftime('%m', t.signed_date) AS INTEGER) AS month,
                   COUNT(*)              AS nb,
                   SUM(t.final_amount)   AS total
            FROM transactions t
            WHERE t.status = 'signed'
              AND strftime('%Y', t.signed_date) = :year
            GROUP BY month
            ORDER BY month
            """
        )
        rows = db.session.execute(sql, {"year": str(year)})
        return [dict(row._mapping) for row in rows]

    @staticmethod
    def kpis() -> dict[str, Any]:
        """KPIs globaux : nombre par statut, panier moyen, durée moyenne de cycle."""
        sql = text(
            """
            SELECT
                COUNT(*)                                            AS total_count,
                SUM(CASE WHEN status='signed'      THEN 1 ELSE 0 END) AS signed_count,
                SUM(CASE WHEN status='compromise'  THEN 1 ELSE 0 END) AS compromise_count,
                SUM(CASE WHEN status='offer'       THEN 1 ELSE 0 END) AS offer_count,
                SUM(CASE WHEN status='cancelled'   THEN 1 ELSE 0 END) AS cancelled_count,
                ROUND(AVG(CASE WHEN status='signed' THEN final_amount END), 2)    AS avg_basket,
                ROUND(AVG(CASE WHEN status='signed' THEN
                    CAST((julianday(signed_date) - julianday(offer_date)) AS INTEGER)
                END), 1) AS avg_cycle_days
            FROM transactions
            """
        )
        row = db.session.execute(sql).first()
        return dict(row._mapping) if row else {}
