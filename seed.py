"""Peuplement de la base avec un jeu de données démo cohérent.

Lancer : ``python seed.py``

Le script supprime puis recrée toutes les tables, puis injecte :
- 1 siège (Aix-en-Provence) + 12 agences
- 1 administrateur, 1 agent par agence, plusieurs clients
- ~120 biens immobiliers répartis dans toute la France
- des demandes de visites, favoris et transactions
"""

from __future__ import annotations

import logging
import random
from datetime import timedelta
from decimal import Decimal

from dotenv import load_dotenv

# Charger .env avant l'import de la factory : la config est lue à l'import.
load_dotenv()

from ymmo import create_app  # noqa: E402
from ymmo._time import utcnow  # noqa: E402
from ymmo.extensions import db  # noqa: E402
from ymmo.models import (  # noqa: E402
    Agency,
    Favorite,
    Property,
    PropertyImage,
    PropertyStatus,
    PropertyType,
    Transaction,
    TransactionStatus,
    User,
    UserRole,
    VisitRequest,
    VisitStatus,
)


logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("seed")

random.seed(42)


# ---------------------------------------------------------------------------
# Référentiels (agences, villes, latitudes, photos, prénoms / noms).
# ---------------------------------------------------------------------------

# 1 siège + 12 agences. Le tuple porte aussi (lat, lng) du siège local pour
# que la carte Leaflet puisse pointer chaque agence sur la France.
AGENCIES = [
    ("Ymmo Aix-en-Provence", "Aix-en-Provence", "13100", "12 cours Mirabeau", True,  43.5297, 5.4474),
    ("Ymmo Marseille",       "Marseille",       "13008", "45 rue Paradis",            False, 43.2965, 5.3698),
    ("Ymmo Lyon",            "Lyon",            "69002", "8 place Bellecour",         False, 45.7578, 4.8320),
    ("Ymmo Paris",           "Paris",           "75008", "120 avenue des Champs-Élysées", False, 48.8566, 2.3522),
    ("Ymmo Bordeaux",        "Bordeaux",        "33000", "10 cours de l'Intendance",  False, 44.8378, -0.5792),
    ("Ymmo Toulouse",        "Toulouse",        "31000", "5 place du Capitole",       False, 43.6047, 1.4442),
    ("Ymmo Nantes",          "Nantes",          "44000", "30 rue Crébillon",          False, 47.2184, -1.5536),
    ("Ymmo Lille",           "Lille",           "59800", "22 rue Faidherbe",          False, 50.6292, 3.0573),
    ("Ymmo Strasbourg",      "Strasbourg",      "67000", "18 place Kléber",           False, 48.5734, 7.7521),
    ("Ymmo Nice",            "Nice",            "06000", "9 promenade des Anglais",   False, 43.7102, 7.2620),
    ("Ymmo Rennes",          "Rennes",          "35000", "14 rue Saint-Michel",       False, 48.1173, -1.6778),
    ("Ymmo Montpellier",     "Montpellier",     "34000", "7 place de la Comédie",     False, 43.6108, 3.8767),
    ("Ymmo Grenoble",        "Grenoble",        "38000", "3 rue Félix Poulat",        False, 45.1885, 5.7245),
]

# Pool : (ville, code postal, prix moyen au m², lat, lng).
# La lat/lng permet au front de placer chaque bien sur une carte interactive
# sans dépendre d'un service externe de géocodage.
CITIES_POOL = [
    ("Aix-en-Provence", "13100",  5500, 43.5297, 5.4474),
    ("Marseille",       "13008",  4200, 43.2965, 5.3698),
    ("Lyon",            "69002",  5300, 45.7578, 4.8320),
    ("Paris",           "75008", 11500, 48.8566, 2.3522),
    ("Bordeaux",        "33000",  5000, 44.8378, -0.5792),
    ("Toulouse",        "31000",  4100, 43.6047, 1.4442),
    ("Nantes",          "44000",  4200, 47.2184, -1.5536),
    ("Lille",           "59800",  3700, 50.6292, 3.0573),
    ("Strasbourg",      "67000",  3600, 48.5734, 7.7521),
    ("Nice",            "06000",  5200, 43.7102, 7.2620),
    ("Rennes",          "35000",  4000, 48.1173, -1.6778),
    ("Montpellier",     "34000",  3900, 43.6108, 3.8767),
    ("Grenoble",        "38000",  3400, 45.1885, 5.7245),
]

FIRST_NAMES = ["Léa", "Hugo", "Camille", "Nathan", "Inès", "Sacha", "Lina", "Théo",
               "Manon", "Yanis", "Chloé", "Adam", "Sarah", "Mathéo", "Romane"]
LAST_NAMES = ["Martin", "Bernard", "Dubois", "Thomas", "Robert", "Petit", "Durand",
              "Leroy", "Moreau", "Simon", "Laurent", "Lefèvre", "Roux", "Vincent"]

# Photos réelles libres de droits hébergées par Unsplash (CDN public),
# curées par type de bien. URLs vérifiées : toutes renvoient HTTP 200.
UNSPLASH = "https://images.unsplash.com/photo-{id}?w=1200&h=800&q=75&auto=format&fit=crop"

PHOTOS_BY_TYPE: dict[PropertyType, list[str]] = {
    PropertyType.HOUSE: [
        "1564013799919-ab600027ffc6",
        "1568605114967-8130f3a36994",
        "1570129477492-45c003edd2be",
        "1512917774080-9991f1c4c750",
        "1583608205776-bfd35f0d9f83",
        "1572120360610-d971b9d7767c",
        "1600596542815-ffad4c1539a9",
        "1605276374104-dee2a0ed3cd6",
        "1580587771525-78b9dba3b914",
        "1576941089067-2de3c901e126",
        "1600585154340-be6161a56a0c",
    ],
    PropertyType.APARTMENT: [
        "1522708323590-d24dbb6b0267",
        "1502672260266-1c1ef2d93688",
        "1545324418-cc1a3fa10c00",
        "1560448204-e02f11c3d0e2",
        "1556909114-f6e7ad7d3136",
        "1502005229762-cf1b2da7c5d6",
        "1505691938895-1758d7feb511",
        "1493809842364-78817add7ffb",
    ],
    PropertyType.LAND: [
        "1500382017468-9049fed747ef",
        "1464822759023-fed622ff2c3b",
        "1559827260-dc66d52bef19",
        "1486304873000-235643847519",
        "1542621334-a254cf47733d",
    ],
    PropertyType.OFFICE: [
        "1497366216548-37526070297c",
        "1497366811353-6870744d04b2",
        "1604328698692-f76ea9498e76",
        "1560185007-c5ca9d2c014d",
    ],
    PropertyType.COMMERCIAL: [
        "1556761175-5973dc0f32e7",
        "1604328698692-f76ea9498e76",
        "1497366216548-37526070297c",
    ],
}


def photos_for(ptype: PropertyType, k: int) -> list[str]:
    pool = PHOTOS_BY_TYPE.get(ptype) or PHOTOS_BY_TYPE[PropertyType.HOUSE]
    sample = random.sample(pool, k=min(k, len(pool)))
    return [UNSPLASH.format(id=image_id) for image_id in sample]


def random_user(role: UserRole, agency_id: int | None = None) -> User:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    email = f"{first.lower()}.{last.lower()}{random.randint(1, 999)}@ymmo.fr"
    user = User(
        email=email,
        first_name=first,
        last_name=last,
        role=role,
        agency_id=agency_id,
        phone=f"06{random.randint(10, 99)}{random.randint(10, 99)}{random.randint(10, 99)}{random.randint(10, 99)}",
    )
    user.set_password("password123")
    return user


def random_property(agent: User, agencies: list[Agency]) -> Property:
    city, postal, base_price, lat, lng = random.choice(CITIES_POOL)
    ptype = random.choices(
        list(PropertyType),
        weights=[5, 4, 1, 1, 1],
        k=1,
    )[0]

    if ptype == PropertyType.APARTMENT:
        surface = random.randint(20, 140)
        rooms = max(1, surface // 22)
    elif ptype == PropertyType.HOUSE:
        surface = random.randint(70, 280)
        rooms = max(3, surface // 30)
    elif ptype == PropertyType.LAND:
        surface = random.randint(200, 2000)
        rooms = 0
    elif ptype == PropertyType.OFFICE:
        surface = random.randint(40, 250)
        rooms = max(1, surface // 25)
    else:
        surface = random.randint(30, 400)
        rooms = max(1, surface // 30)

    bedrooms = max(0, rooms - 1) if rooms else 0
    bathrooms = 1 if rooms <= 3 else 2

    price = int(surface * base_price * random.uniform(0.85, 1.25))
    if ptype == PropertyType.LAND:
        price = int(surface * random.randint(150, 600))

    status = random.choices(
        [
            PropertyStatus.AVAILABLE,
            PropertyStatus.UNDER_OFFER,
            PropertyStatus.SOLD,
        ],
        weights=[7, 1, 2],
        k=1,
    )[0]

    # Léger jitter sur la lat/lng pour que les marqueurs ne se chevauchent pas
    # tous au même endroit dans Leaflet (~1.5 km de variance).
    jitter_lat = random.uniform(-0.015, 0.015)
    jitter_lng = random.uniform(-0.015, 0.015)

    return Property(
        title=f"{ptype.label} {surface} m² {city}",
        description=(
            f"Beau {ptype.label.lower()} de {surface} m² situé à {city}. "
            f"{rooms} pièce(s), exposition agréable, proche commodités."
        ),
        type=ptype,
        status=status,
        price=Decimal(price),
        surface=surface,
        rooms=rooms,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        floor=random.randint(0, 5) if ptype == PropertyType.APARTMENT else None,
        has_parking=random.random() > 0.4,
        has_garden=random.random() > 0.7 if ptype == PropertyType.HOUSE else random.random() > 0.9,
        has_balcony=random.random() > 0.5 if ptype == PropertyType.APARTMENT else False,
        energy_class=random.choice(["A", "B", "C", "D", "E"]),
        year_built=random.randint(1960, 2024),
        address=f"{random.randint(1, 200)} rue {random.choice(['des Lilas', 'Victor Hugo', 'du Parc', 'Pasteur', 'de la République'])}",
        city=city,
        postal_code=postal,
        latitude=round(lat + jitter_lat, 6),
        longitude=round(lng + jitter_lng, 6),
        views_count=random.randint(0, 350),
        agent_id=agent.id,
        agency_id=agent.agency_id or agencies[0].id,
        created_at=utcnow() - timedelta(days=random.randint(0, 200)),
    )


def main() -> None:
    app = create_app()
    # `test_request_context` fournit un contexte HTTP fictif nécessaire à
    # Flask-Babel : nos enums utilisent gettext() pour le label, qui exige
    # une locale. Sans contexte de requête, l'accès à `.label` plante.
    with app.app_context(), app.test_request_context():
        logger.info("DROP + CREATE des tables")
        db.drop_all()
        db.create_all()

        agencies: list[Agency] = []
        for name, city, pc, addr, hq, _lat, _lng in AGENCIES:
            agency = Agency(
                name=name,
                city=city,
                postal_code=pc,
                address=addr,
                phone=f"04{random.randint(10, 99)}{random.randint(10, 99)}{random.randint(10, 99)}{random.randint(10, 99)}",
                email=f"contact.{city.lower().split('-')[0]}@ymmo.fr",
                is_headquarters=hq,
            )
            agencies.append(agency)
        db.session.add_all(agencies)
        db.session.commit()
        logger.info("13 agences créées")

        admin = User(
            email="admin@ymmo.fr",
            first_name="Alice",
            last_name="Admin",
            role=UserRole.ADMIN,
        )
        admin.set_password("admin12345")
        db.session.add(admin)

        agents: list[User] = []
        for agency in agencies:
            for _ in range(random.randint(1, 2)):
                agents.append(random_user(UserRole.AGENT, agency_id=agency.id))

        demo_agent = User(
            email="agent@ymmo.fr",
            first_name="Antoine",
            last_name="Agent",
            role=UserRole.AGENT,
            agency_id=agencies[0].id,
        )
        demo_agent.set_password("agent12345")
        agents.append(demo_agent)

        clients: list[User] = []
        for _ in range(20):
            clients.append(random_user(UserRole.CLIENT))

        demo_client = User(
            email="client@ymmo.fr",
            first_name="Camille",
            last_name="Client",
            role=UserRole.CLIENT,
        )
        demo_client.set_password("client12345")
        clients.append(demo_client)

        db.session.add_all(agents)
        db.session.add_all(clients)
        db.session.commit()
        logger.info("%d agents + %d clients créés", len(agents), len(clients))

        properties: list[Property] = []
        for _ in range(120):
            agent = random.choice(agents)
            properties.append(random_property(agent, agencies))
        db.session.add_all(properties)
        db.session.commit()
        logger.info("%d biens créés", len(properties))

        for prop in properties:
            urls = photos_for(prop.type, random.randint(2, 4))
            for i, url in enumerate(urls):
                db.session.add(
                    PropertyImage(
                        property_id=prop.id,
                        url=url,
                        alt_text=f"Photo {i + 1} — {prop.type.label} à {prop.city}",
                        position=i,
                    )
                )

        for client in clients:
            for prop in random.sample(properties, k=random.randint(0, 4)):
                db.session.add(Favorite(user_id=client.id, property_id=prop.id))

        for _ in range(60):
            prop = random.choice(properties)
            client = random.choice(clients)
            db.session.add(
                VisitRequest(
                    property_id=prop.id,
                    client_id=client.id,
                    requested_at=utcnow() - timedelta(days=random.randint(0, 60)),
                    preferred_date=utcnow() + timedelta(days=random.randint(1, 20)),
                    message="Bonjour, votre bien m'intéresse, pouvons-nous convenir d'une visite ?",
                    status=random.choice(list(VisitStatus)),
                )
            )

        sold_props = [p for p in properties if p.status == PropertyStatus.SOLD]
        for prop in sold_props:
            buyer = random.choice(clients)
            offer_date = utcnow() - timedelta(days=random.randint(60, 200))
            signed_date = offer_date + timedelta(days=random.randint(45, 120))
            offer_amount = Decimal(int(float(prop.price) * random.uniform(0.92, 1.0)))
            db.session.add(
                Transaction(
                    property_id=prop.id,
                    buyer_id=buyer.id,
                    agent_id=prop.agent_id,
                    offer_amount=offer_amount,
                    final_amount=offer_amount,
                    status=TransactionStatus.SIGNED,
                    offer_date=offer_date,
                    compromise_date=offer_date + timedelta(days=20),
                    signed_date=signed_date,
                )
            )

        for prop in [p for p in properties if p.status == PropertyStatus.UNDER_OFFER]:
            buyer = random.choice(clients)
            offer_date = utcnow() - timedelta(days=random.randint(10, 60))
            db.session.add(
                Transaction(
                    property_id=prop.id,
                    buyer_id=buyer.id,
                    agent_id=prop.agent_id,
                    offer_amount=Decimal(int(float(prop.price) * 0.95)),
                    status=TransactionStatus.COMPROMISE,
                    offer_date=offer_date,
                    compromise_date=offer_date + timedelta(days=15),
                )
            )

        db.session.commit()
        logger.info(
            "Terminé : %d agences, %d agents, %d clients, %d biens",
            len(agencies), len(agents), len(clients), len(properties),
        )
        logger.info("Comptes de démo :")
        logger.info("  admin  : admin@ymmo.fr  / admin12345")
        logger.info("  agent  : agent@ymmo.fr  / agent12345")
        logger.info("  client : client@ymmo.fr / client12345")


if __name__ == "__main__":
    main()
