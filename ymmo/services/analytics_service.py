"""Service d'analyse de données.

Façade entre les blueprints (qui veulent des dictionnaires sérialisables)
et le module ``analytics`` (qui manipule des DataFrames pandas).

NB : on instancie le service via ``current_app.extensions["analytics"]``
plutôt qu'en singleton module-level (cf. ymmo/__init__.py). Cela évite
les problèmes de thread-safety quand plusieurs workers WSGI tournent.
"""

from __future__ import annotations

from typing import Any

from ..analytics import (
    MarketAnalysis,
    PricePredictor,
    agent_ranking,
    build_property_dataframe,
    monthly_revenue_chart,
    sales_velocity,
    trending_properties,
)
from ..repositories import PropertyRepository, TransactionRepository


class AnalyticsService:
    """Façade exposant les indicateurs et le modèle ML aux blueprints."""

    def __init__(self) -> None:
        self._predictor: PricePredictor | None = None

    # -- Modèle de prix : entraîné à la demande puis mis en cache ------

    def _get_predictor(self) -> PricePredictor:
        if self._predictor is None:
            df = build_property_dataframe(PropertyRepository.all_for_dataframe())
            self._predictor = PricePredictor().fit(df)
        return self._predictor

    def reset_predictor(self) -> None:
        """À appeler après un CRUD bien : la prochaine prédiction réentraîne."""
        self._predictor = None

    # -- Tableau de bord global (page /marche) -------------------------

    def dashboard(self) -> dict[str, Any]:
        df = build_property_dataframe(PropertyRepository.all_for_dataframe())
        analysis = MarketAnalysis(df)
        tx_rows = TransactionRepository.all_for_dataframe()
        return {
            "kpis": TransactionRepository.kpis(),
            "by_status": PropertyRepository.count_by_status(),
            "by_type": PropertyRepository.count_by_type(),
            "top_cities": PropertyRepository.avg_price_per_city(limit=8),
            "top_viewed": [
                {"id": p.id, "title": p.title, "views": p.views_count, "price": float(p.price)}
                for p in PropertyRepository.top_viewed(5)
            ],
            "popular_features": analysis.popular_features(),
            "trend_per_type": analysis.average_price_per_type(),
            "best_zones": analysis.best_zones_to_invest(top=8),
            "price_distribution": analysis.price_distribution(bins=8),
            "price_trend": analysis.price_trend(months=6, top_cities=5),
            "monthly_revenue": monthly_revenue_chart(TransactionRepository.monthly_revenue()),
            "sales_velocity": sales_velocity(tx_rows),
            "trending": trending_properties(
                PropertyRepository.all_for_dataframe(), days=30, top=5
            ),
        }

    # -- Estimation prix d'un bien -------------------------------------

    def predict_price(self, features: dict[str, Any]) -> dict[str, Any]:
        predictor = self._get_predictor()
        prediction = predictor.predict_one(features)
        return {
            "predicted_price": round(prediction, 2),
            "price_per_sqm": round(prediction / max(features["surface"], 1), 2),
            "confidence": predictor.score,
            "model": predictor.model_name,
        }

    # -- Vélocité de vente : combien de jours pour vendre CE bien ? ---

    def estimate_days_to_sell(self, prop) -> dict[str, Any] | None:
        """Heuristique : on combine la durée moyenne du cycle pour ce type
        de bien, et un coefficient lié à l'écart de prix vs marché local.

        Bien dans la moyenne -> base. Bien à -10% -> ~30% plus rapide.
        Bien à +10% -> ~30% plus lent.
        """
        tx_rows = TransactionRepository.all_for_dataframe()
        velocities = sales_velocity(tx_rows)
        base = velocities.get(prop.type.value)
        if not base:
            return None

        comparable = PropertyRepository.comparable_stats(prop.city, prop.type.value)
        coeff = 1.0
        delta_pct = 0.0
        if comparable and comparable.get("avg_price_sqm"):
            ref = float(comparable["avg_price_sqm"])
            if ref > 0:
                delta_pct = (float(prop.price) / float(prop.surface) - ref) / ref
                # +10% -> *1.3 (plus lent), -10% -> *0.7 (plus rapide).
                coeff = 1.0 + delta_pct * 3.0
                coeff = max(0.4, min(coeff, 2.5))

        days = max(7, int(round(base * coeff)))
        return {
            "days": days,
            "base_days": int(base),
            "delta_pct": round(delta_pct * 100, 1),
            "comparable_count": int(comparable["nb"]) if comparable else 0,
        }

    # -- Détection d'anomalies pour un agent --------------------------

    def anomalies_for_agent(self, agent_id: int, sigma: float = 2.0) -> set[int]:
        df = build_property_dataframe(PropertyRepository.all_for_dataframe())
        if df.empty:
            return set()
        ids = MarketAnalysis(df).anomaly_ids(sigma=sigma)
        # On filtre côté ORM : on n'envoie que les IDs qui sont VRAIMENT
        # dans le portefeuille de l'agent, pour éviter de fuiter info.
        agent_ids = {p.id for p in PropertyRepository.list_for_agent(agent_id)}
        return ids & agent_ids

    # -- Ranking des agents (pour l'admin) ----------------------------

    def agent_performance(self, top: int = 10) -> list[dict[str, Any]]:
        return agent_ranking(TransactionRepository.all_for_dataframe(), top=top)
