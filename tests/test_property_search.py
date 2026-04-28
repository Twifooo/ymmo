"""Tests de la recherche multi-critères."""

from decimal import Decimal

from ymmo.extensions import db
from ymmo.models import (
    Agency,
    Property,
    PropertyStatus,
    PropertyType,
    User,
    UserRole,
)
from ymmo.repositories import PropertyRepository
from ymmo.repositories.property_repository import PropertySearchCriteria


def _build_dataset(app):
    agency = Agency(
        name="Test Agency",
        city="Aix",
        postal_code="13100",
        address="x",
        is_headquarters=True,
    )
    agent = User(
        email="agent@test.com",
        password_hash="x",
        first_name="A",
        last_name="A",
        role=UserRole.AGENT,
        agency=agency,
    )
    db.session.add_all([agency, agent])
    db.session.commit()

    samples = [
        ("Studio Lyon", PropertyType.APARTMENT, 200_000, 25, "Lyon", "69002"),
        ("Maison Lyon", PropertyType.HOUSE, 600_000, 120, "Lyon", "69002"),
        ("Appart Paris", PropertyType.APARTMENT, 800_000, 60, "Paris", "75008"),
        ("Terrain Aix", PropertyType.LAND, 150_000, 800, "Aix", "13100"),
    ]
    for title, ptype, price, surface, city, pc in samples:
        db.session.add(
            Property(
                title=title,
                type=ptype,
                status=PropertyStatus.AVAILABLE,
                price=Decimal(price),
                surface=surface,
                rooms=3,
                bedrooms=2,
                bathrooms=1,
                address="rue x",
                city=city,
                postal_code=pc,
                agent_id=agent.id,
                agency_id=agency.id,
            )
        )
    db.session.commit()


def test_search_by_city(app):
    with app.app_context():
        _build_dataset(app)
        items, total = PropertyRepository.search(
            PropertySearchCriteria(city="Lyon")
        )
        assert total == 2
        assert {p.title for p in items} == {"Studio Lyon", "Maison Lyon"}


def test_search_with_price_range(app):
    with app.app_context():
        _build_dataset(app)
        items, total = PropertyRepository.search(
            PropertySearchCriteria(min_price=300_000, max_price=700_000)
        )
        assert total == 1
        assert items[0].title == "Maison Lyon"


def test_search_by_type(app):
    with app.app_context():
        _build_dataset(app)
        items, total = PropertyRepository.search(
            PropertySearchCriteria(property_type=PropertyType.LAND)
        )
        assert total == 1
        assert items[0].title == "Terrain Aix"


def test_avg_price_per_city(app):
    with app.app_context():
        _build_dataset(app)
        rows = PropertyRepository.avg_price_per_city()
        cities = {row["city"] for row in rows}
        assert cities == {"Lyon", "Paris", "Aix"}
