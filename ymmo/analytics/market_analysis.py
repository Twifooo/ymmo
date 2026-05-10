"""Analyses statistiques du marché immobilier.

Le pipeline est : extraction SQL -> DataFrame pandas -> nettoyage ->
agrégations -> rendu JSON-friendly pour les vues.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd

from .._time import utcnow


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
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

    df = df.dropna(subset=["price", "surface"])
    df = df[(df["surface"] > 0) & (df["price"] > 0)]
    df["price_per_sqm"] = df["price"] / df["surface"]
    return df.reset_index(drop=True)


class MarketAnalysis:
    """Indicateurs et agrégations à partir du DataFrame nettoyé."""

    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df

    # -- Indicateurs simples --------------------------------------------

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

    # -- Détection d'anomalies -----------------------------------------

    def anomalies(self, sigma: float = 2.0) -> list[dict[str, Any]]:
        """Identifie les biens dont le prix au m² s'écarte de plus de ``sigma``
        écarts-types par rapport à la moyenne (city, type).

        Utilisé sur le tableau de bord agent pour signaler une annonce
        possiblement mal valorisée (sur- ou sous-cotée).
        """
        if self.df.empty or "city" not in self.df.columns or "type" not in self.df.columns:
            return []

        grouped = self.df.groupby(["city", "type"])["price_per_sqm"].agg(["mean", "std"]).reset_index()
        merged = self.df.merge(grouped, on=["city", "type"], how="left")
        # On évite la division par zéro quand un groupe ne contient qu'un bien.
        merged = merged[merged["std"].fillna(0) > 0]
        merged["zscore"] = (merged["price_per_sqm"] - merged["mean"]) / merged["std"]

        flagged = merged[merged["zscore"].abs() >= sigma].copy()
        flagged["delta_pct"] = (
            (flagged["price_per_sqm"] - flagged["mean"]) / flagged["mean"] * 100
        ).round(1)
        flagged["zscore"] = flagged["zscore"].round(2)

        cols = ["id", "title", "city", "type", "price", "price_per_sqm", "mean", "zscore", "delta_pct"]
        cols = [c for c in cols if c in flagged.columns]
        return flagged[cols].to_dict(orient="records")

    def anomaly_ids(self, sigma: float = 2.0) -> set[int]:
        """Helper pratique pour décorer les listes côté template."""
        return {int(a["id"]) for a in self.anomalies(sigma=sigma) if "id" in a}

    # -- Tendance temporelle (prix moyen sur 6 mois par ville) ---------

    def price_trend(self, months: int = 6, top_cities: int = 5) -> dict[str, Any]:
        """Renvoie les prix moyens par mois sur ``months`` derniers mois,
        pour les ``top_cities`` villes les plus représentées.

        Retour : ``{"labels": [...mois...], "series": {city: [..valeurs..]}}``
        Permet de tracer un line-chart SVG côté template (fait main, pas de
        librairie externe).
        """
        if self.df.empty or "created_at" not in self.df.columns:
            return {"labels": [], "series": {}}

        end = utcnow().replace(day=1)
        start = end - timedelta(days=30 * months)
        df = self.df[self.df["created_at"] >= start].copy()
        if df.empty:
            return {"labels": [], "series": {}}

        df["month"] = df["created_at"].dt.to_period("M").astype(str)
        # On garde les villes les plus représentées pour ne pas saturer le graphique.
        cities = df["city"].value_counts().head(top_cities).index.tolist()
        df = df[df["city"].isin(cities)]

        pivot = (
            df.groupby(["month", "city"])["price_per_sqm"]
            .mean()
            .round(0)
            .unstack(fill_value=0)
        )
        pivot = pivot.sort_index()
        # Chaque colonne devient une série, on conserve l'ordre des mois.
        return {
            "labels": list(pivot.index),
            "series": {city: [int(v) for v in pivot[city].tolist()] for city in pivot.columns},
        }


# ---------------------------------------------------------------------------
# Helpers indépendants : ranking agents, vélocité de vente, revenu mensuel.
# Ces fonctions sont volontairement out of class : elles consomment d'autres
# DataFrames (transactions) que le DF des biens passé à MarketAnalysis.
# ---------------------------------------------------------------------------


def agent_ranking(transactions: list[dict[str, Any]], top: int = 10) -> list[dict[str, Any]]:
    """Classe les agents par : ventes signées DESC, panier moyen DESC,
    durée moyenne ASC.

    ``transactions`` doit contenir : agent_id, agent_name, status,
    final_amount, offer_date, signed_date.
    """
    df = pd.DataFrame(transactions)
    if df.empty:
        return []

    df = df[df["status"] == "signed"].copy()
    if df.empty:
        return []
    df["offer_date"] = pd.to_datetime(df["offer_date"], errors="coerce")
    df["signed_date"] = pd.to_datetime(df["signed_date"], errors="coerce")
    df["cycle_days"] = (df["signed_date"] - df["offer_date"]).dt.days

    grouped = (
        df.groupby(["agent_id", "agent_name"], dropna=False)
        .agg(
            sold=("final_amount", "size"),
            avg_value=("final_amount", "mean"),
            total_value=("final_amount", "sum"),
            avg_days=("cycle_days", "mean"),
        )
        .reset_index()
    )
    grouped[["avg_value", "total_value"]] = grouped[["avg_value", "total_value"]].round(0)
    grouped["avg_days"] = grouped["avg_days"].round(1)
    grouped = grouped.sort_values(
        by=["sold", "avg_value", "avg_days"],
        ascending=[False, False, True],
    ).head(top)
    return grouped.to_dict(orient="records")


def monthly_revenue_chart(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Transforme la sortie ``TransactionRepository.monthly_revenue`` en
    structure prête pour un line-chart SVG. Les mois manquants sont
    complétés à zéro pour que la courbe couvre l'année entière.
    """
    df = pd.DataFrame(rows)
    months = list(range(1, 13))
    labels = ["jan", "fév", "mar", "avr", "mai", "jui", "jul", "aoû", "sep", "oct", "nov", "déc"]
    if df.empty:
        return {"labels": labels, "totals": [0] * 12, "counts": [0] * 12}

    df = df.set_index("month")
    totals = [int(float(df.loc[m, "total"])) if m in df.index else 0 for m in months]
    counts = [int(df.loc[m, "nb"]) if m in df.index else 0 for m in months]
    return {"labels": labels, "totals": totals, "counts": counts}


def sales_velocity(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    """Calcule la vélocité de vente moyenne (jours offre→signature) par
    type de bien. Retour : ``{"apartment": 78.3, "house": 92.1, ...}``.
    """
    df = pd.DataFrame(transactions)
    if df.empty:
        return {}
    df = df[df["status"] == "signed"].copy()
    if df.empty:
        return {}
    df["offer_date"] = pd.to_datetime(df["offer_date"], errors="coerce")
    df["signed_date"] = pd.to_datetime(df["signed_date"], errors="coerce")
    df["cycle_days"] = (df["signed_date"] - df["offer_date"]).dt.days
    df = df.dropna(subset=["cycle_days"])
    if df.empty or "property_type" not in df.columns:
        return {}
    avg = df.groupby("property_type")["cycle_days"].mean().round(0)
    return {str(k): int(v) for k, v in avg.items()}


def trending_properties(rows: list[dict[str, Any]], days: int = 30, top: int = 5) -> list[dict[str, Any]]:
    """Top ``top`` biens créés ces ``days`` derniers jours, classés par vues.

    "Trending" = biens récents qui captent beaucoup d'attention, pas juste
    les biens les plus vus historiquement.
    """
    df = pd.DataFrame(rows)
    if df.empty or "created_at" not in df.columns:
        return []
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    cutoff = utcnow() - timedelta(days=days)
    recent = df[df["created_at"] >= cutoff].copy()
    if recent.empty:
        return []
    recent = recent.sort_values("views_count", ascending=False).head(top)
    cols = ["id", "title", "city", "price", "views_count", "type"]
    cols = [c for c in cols if c in recent.columns]
    return recent[cols].to_dict(orient="records")
