"""Repository transactions et indicateurs de pilotage."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select, text

from .._time import utcnow
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
    def monthly_revenue(year: int | None = None) -> list[dict[str, Any]]:
        """Chiffre d'affaires signé par mois pour l'année donnée.

        ``year`` : année calendaire ; par défaut l'année en cours.
        """
        if year is None:
            year = utcnow().year
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

    @staticmethod
    def all_for_dataframe() -> list[dict[str, Any]]:
        """Export brut joint avec User et Property pour les analyses pandas
        (ranking agents, vélocité par type)."""
        sql = text(
            """
            SELECT t.id,
                   t.status,
                   t.offer_amount,
                   t.final_amount,
                   t.offer_date,
                   t.compromise_date,
                   t.signed_date,
                   t.agent_id,
                   (u.first_name || ' ' || u.last_name) AS agent_name,
                   p.type   AS property_type,
                   p.city   AS property_city
            FROM transactions t
            JOIN users      u ON u.id = t.agent_id
            JOIN properties p ON p.id = t.property_id
            """
        )
        return [dict(row._mapping) for row in db.session.execute(sql)]
