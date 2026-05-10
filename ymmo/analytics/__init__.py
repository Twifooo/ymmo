"""Module d'analyse et de manipulation de données.

Conformément au programme B2 ("Analyse et manipulation de données en
Python"), ce module nettoie les données issues de la base, calcule des
indicateurs métier et entraîne un modèle de régression pour estimer le
prix d'un bien.
"""

from .market_analysis import (
    MarketAnalysis,
    agent_ranking,
    build_property_dataframe,
    monthly_revenue_chart,
    sales_velocity,
    trending_properties,
)
from .price_predictor import PricePredictor

__all__ = [
    "MarketAnalysis",
    "PricePredictor",
    "agent_ranking",
    "build_property_dataframe",
    "monthly_revenue_chart",
    "sales_velocity",
    "trending_properties",
]
