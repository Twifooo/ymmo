"""Analyses statistiques du marché immobilier.

Le pipeline est : extraction SQL -> DataFrame pandas -> nettoyage ->
agrégations -> rendu JSON-friendly pour les vues.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


NUMERIC_COLUMNS = ("price", "surface", "rooms", "bedrooms", "bathrooms", "views_count")
BOOLEAN_FEATURES = ("has_parking", "has_garden", "has_balcony")


def build_property_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Convertit la sortie du repository en DataFrame nettoyé.

    Étapes :
    - typage strict (les enums SQLAlchemy reviennent en str ou Enum),
    - suppression des lignes inutilisables (surface ou prix nuls),
    - calcul du prix au m² qui sert de base aux analyses.
    """
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "type" in df.columns:
        df["type"] = df["type"].astype(str).str.replace("PropertyType.", "", regex=False)
    if "status" in df.columns:
        df["status"] = df["status"].astype(str).str.replace("PropertyStatus.", "", regex=False)

    df = df.dropna(subset=["price", "surface"])
    df = df[(df["surface"] > 0) & (df["price"] > 0)]
    df["price_per_sqm"] = df["price"] / df["surface"]
    return df.reset_index(drop=True)


class MarketAnalysis:
    """Indicateurs et agrégations à partir du DataFrame nettoyé."""

    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df

    def popular_features(self) -> dict[str, float]:
        """Pourcentage de biens disposant de chaque équipement."""
        if self.df.empty:
            return {feature: 0.0 for feature in BOOLEAN_FEATURES}
        return {
            feature: round(float(self.df[feature].mean()) * 100, 1)
            for feature in BOOLEAN_FEATURES
            if feature in self.df.columns
        }

    def average_price_per_type(self) -> list[dict[str, Any]]:
        """Prix moyen et au m² par type de bien."""
        if self.df.empty or "type" not in self.df.columns:
            return []
        grouped = (
            self.df.groupby("type")
            .agg(
                count=("price", "size"),
                avg_price=("price", "mean"),
                avg_price_sqm=("price_per_sqm", "mean"),
                avg_surface=("surface", "mean"),
            )
            .round(2)
            .reset_index()
            .sort_values("avg_price", ascending=False)
        )
        return grouped.to_dict(orient="records")

    def best_zones_to_invest(self, top: int = 5) -> list[dict[str, Any]]:
        """Zones où acheter : combinaison demande (vues) et prix au m² bas.

        On normalise les deux signaux puis on calcule un score
        ``demand - 0.6 * cost`` pour favoriser les villes attractives mais
        encore abordables.
        """
        if self.df.empty or "city" not in self.df.columns:
            return []

        grouped = (
            self.df.groupby("city")
            .agg(
                count=("price", "size"),
                avg_price=("price", "mean"),
                avg_price_sqm=("price_per_sqm", "mean"),
                avg_views=("views_count", "mean"),
            )
            .reset_index()
        )

        def normalize(series: pd.Series) -> pd.Series:
            spread = series.max() - series.min()
            if spread == 0:
                return pd.Series(np.zeros(len(series)), index=series.index)
            return (series - series.min()) / spread

        grouped["demand_score"] = normalize(grouped["avg_views"])
        grouped["cost_score"] = normalize(grouped["avg_price_sqm"])
        grouped["opportunity_score"] = (
            grouped["demand_score"] - 0.6 * grouped["cost_score"]
        ).round(3)

        grouped = grouped.sort_values("opportunity_score", ascending=False).head(top)
        grouped[["avg_price", "avg_price_sqm", "avg_views"]] = grouped[
            ["avg_price", "avg_price_sqm", "avg_views"]
        ].round(2)
        return grouped.to_dict(orient="records")

    def price_distribution(self, bins: int = 10) -> list[dict[str, Any]]:
        """Histogramme des prix pour alimenter un graphique côté frontend."""
        if self.df.empty:
            return []
        counts, edges = np.histogram(self.df["price"], bins=bins)
        return [
            {
                "min": round(float(edges[i]), 0),
                "max": round(float(edges[i + 1]), 0),
                "count": int(counts[i]),
            }
            for i in range(len(counts))
        ]
