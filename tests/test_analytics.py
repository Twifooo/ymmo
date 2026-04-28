"""Tests du module analytics."""

import pandas as pd

from ymmo.analytics import MarketAnalysis, PricePredictor, build_property_dataframe


def _sample_rows() -> list[dict]:
    return [
        {"id": i, "type": "apartment", "status": "available",
         "price": 200_000 + i * 1000, "surface": 40 + i,
         "rooms": 2, "bedrooms": 1, "bathrooms": 1,
         "has_parking": i % 2, "has_garden": 0, "has_balcony": 1,
         "energy_class": "C", "year_built": 2010,
         "city": "Lyon" if i % 2 else "Paris",
         "postal_code": "69002", "views_count": i * 10,
         "created_at": None, "agency_name": "Test", "title": f"P{i}"}
        for i in range(20)
    ]


def test_build_dataframe_filters_invalid_rows():
    rows = _sample_rows() + [
        {"id": 99, "type": "house", "status": "available", "price": 0, "surface": 0,
         "rooms": 1, "bedrooms": 1, "bathrooms": 1,
         "has_parking": 0, "has_garden": 0, "has_balcony": 0,
         "energy_class": "C", "year_built": 2000, "city": "X",
         "postal_code": "00000", "views_count": 0, "created_at": None,
         "agency_name": "T", "title": "bad"}
    ]
    df = build_property_dataframe(rows)
    assert (df["price"] > 0).all()
    assert (df["surface"] > 0).all()
    assert "price_per_sqm" in df.columns


def test_market_analysis_outputs():
    df = build_property_dataframe(_sample_rows())
    analysis = MarketAnalysis(df)
    assert analysis.popular_features()["has_parking"] >= 0
    assert isinstance(analysis.average_price_per_type(), list)
    zones = analysis.best_zones_to_invest(top=2)
    assert all("opportunity_score" in z for z in zones)


def test_price_predictor_fit_and_predict():
    df = build_property_dataframe(_sample_rows())
    predictor = PricePredictor().fit(df)
    assert predictor.pipeline is not None
    estimation = predictor.predict_one({
        "type": "apartment", "city": "Lyon", "surface": 50,
        "rooms": 2, "bedrooms": 1, "bathrooms": 1,
        "has_parking": True, "has_garden": False, "has_balcony": True,
    })
    assert estimation > 0


def test_price_predictor_skips_when_too_few_rows():
    predictor = PricePredictor().fit(pd.DataFrame())
    assert predictor.pipeline is None
