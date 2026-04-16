"""Estimation du prix d'un bien par régression linéaire.

Pipeline scikit-learn classique : OneHotEncoder pour les variables
catégorielles (type, ville), passthrough pour les variables numériques,
puis ``LinearRegression``. Le score R² du modèle est exposé pour servir
d'indicateur de confiance dans l'UI.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

NUMERIC_FEATURES = ["surface", "rooms", "bedrooms", "bathrooms"]
BOOLEAN_FEATURES = ["has_parking", "has_garden", "has_balcony"]
CATEGORICAL_FEATURES = ["type", "city"]
ALL_FEATURES = NUMERIC_FEATURES + BOOLEAN_FEATURES + CATEGORICAL_FEATURES


class PricePredictor:
    """Estimateur de prix entraîné sur le portefeuille existant."""

    model_name = "LinearRegression + OneHotEncoder"

    def __init__(self) -> None:
        self.pipeline: Pipeline | None = None
        self.score: float = 0.0
        self._known_cities: set[str] = set()

    def fit(self, df: pd.DataFrame) -> "PricePredictor":
        if df.empty or len(df) < 5:
            self.pipeline = None
            self.score = 0.0
            return self

        usable = df.dropna(subset=ALL_FEATURES + ["price"]).copy()
        for col in BOOLEAN_FEATURES:
            usable[col] = usable[col].astype(int)
        self._known_cities = set(usable["city"].unique())

        preprocessor = ColumnTransformer(
            transformers=[
                (
                    "cat",
                    OneHotEncoder(handle_unknown="ignore"),
                    CATEGORICAL_FEATURES,
                )
            ],
            remainder="passthrough",
        )
        pipeline = Pipeline(
            steps=[("pre", preprocessor), ("reg", LinearRegression())]
        )
        x = usable[ALL_FEATURES]
        y = usable["price"]
        pipeline.fit(x, y)
        self.pipeline = pipeline
        self.score = round(float(pipeline.score(x, y)), 3)
        return self

    def predict_one(self, features: dict[str, Any]) -> float:
        if self.pipeline is None:
            raise RuntimeError("Le modèle n'a pas pu être entraîné (échantillon trop faible).")
        row = {key: features.get(key) for key in ALL_FEATURES}
        for col in BOOLEAN_FEATURES:
            row[col] = int(bool(row.get(col)))
        for col in NUMERIC_FEATURES:
            row[col] = float(row.get(col) or 0)
        for col in CATEGORICAL_FEATURES:
            row[col] = str(row.get(col) or "")
        prediction = self.pipeline.predict(pd.DataFrame([row]))[0]
        return max(float(prediction), 0.0)

    def is_city_known(self, city: str) -> bool:
        return city in self._known_cities
