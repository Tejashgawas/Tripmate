# services/rule_engine.py

from collections import defaultdict
from typing import List
from app.models import Service
from app.schemas.recommendation.recommendation import RecommendedService, RecommendationResponse


def group_and_select_top_services(services: List[Service], top_n: int = 3) -> RecommendationResponse:
    grouped_services = defaultdict(list)

    # 1. Group by service type
    for service in services:
        grouped_services[service.type].append(service)

    # 2. Sort each group and pick top N
    response_data = {
        "hotels": [],
        "buses": [],
        "rentals": [],
        "packages": []
    }

    for service_type, items in grouped_services.items():
        # 3. Sort: rating (desc) > price (asc)
        sorted_items = sorted(
            items,
            key=lambda s: (  # ensure rating None = 0
                s.price or float('inf')
            )
        )

        # 4. Map to schema and slice top N
        recommended = [
            RecommendedService(
                id=svc.id,
                title=svc.title,
                type=svc.type,
                price=svc.price,
                rating=svc.rating,
                provider_id=svc.provider.id,
                provider_name=svc.provider.name,
                location=svc.location,
                is_available=svc.is_available,
                source="internal",
                features=svc.features
            )
            for svc in sorted_items[:top_n]
        ]

        # 5. Insert into correct response key
        key = service_type.lower() + "s"  # hotel -> hotels, rental -> rentals
        if key in response_data:
            response_data[key] = recommended

    return RecommendationResponse(**response_data)
