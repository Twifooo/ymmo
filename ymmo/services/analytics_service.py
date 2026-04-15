"""Service d'analyse de données.

Façade entre les blueprints (qui veulent des dictionnaires sérialisables)
et le module ``analytics`` (qui manipule des DataFrames pandas).
"""

from __future__ import annotations

from typing import Any

from ..analytics import MarketAnalysis, PricePredictor, build_property_dataframe
from ..repositories import PropertyRepository, TransactionRepository


class AnalyticsService:
    def __init__(self) -> None:
        self._predictor: PricePredictor | None = None

    def _get_predictor(self) -> PricePredictor:
        if self._predictor is None:
            df = build_property_dataframe(PropertyRepository.all_for_dataframe())
            self._predictor = PricePredictor().fit(df)
        return self._predictor

    def reset_predictor(self) -> None:
        self._predictor = None

    def dashboard(self) -> dict[str, Any]:
        df = build_property_dataframe(PropertyRepository.all_for_dataframe())
        analysis = MarketAnalysis(df)
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
        }

    def predict_price(self, features: dict[str, Any]) -> dict[str, Any]:
        predictor = self._get_predictor()
        prediction = predictor.predict_one(features)
        return {
            "predicted_price": round(prediction, 2),
            "price_per_sqm": round(prediction / max(features["surface"], 1), 2),
            "confidence": predictor.score,
            "model": predictor.model_name,
        }
