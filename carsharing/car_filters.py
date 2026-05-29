"""Фильтрация и сортировка автомобилей (веб и API)."""

from decimal import Decimal
from typing import Any

from django.db.models import QuerySet

from carsharing.models import Car

SORT_CHOICES = {
    "brand": ("brand", "model"),
    "-price": ("-price_per_minute", "brand"),
    "price": ("price_per_minute", "brand"),
    "-year": ("-year", "brand"),
    "year": ("year", "brand"),
}


def apply_car_filters(
    queryset: QuerySet[Car],
    *,
    available_only: bool = True,
    brand: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    price_min: Decimal | None = None,
    price_max: Decimal | None = None,
    sort: str = "brand",
) -> QuerySet[Car]:
    if available_only:
        queryset = queryset.filter(is_available=True)
    if brand:
        queryset = queryset.filter(brand__iexact=brand.strip())
    if year_min is not None:
        queryset = queryset.filter(year__gte=year_min)
    if year_max is not None:
        queryset = queryset.filter(year__lte=year_max)
    if price_min is not None:
        queryset = queryset.filter(price_per_minute__gte=price_min)
    if price_max is not None:
        queryset = queryset.filter(price_per_minute__lte=price_max)

    order = SORT_CHOICES.get(sort, SORT_CHOICES["brand"])
    return queryset.order_by(*order)


def parse_filter_params(params: dict[str, Any], available_only: bool = True) -> dict[str, Any]:
    """Парсинг GET/query-параметров фильтров."""
    brand = params.get("brand") or None
    if brand == "":
        brand = None

    def _int(key: str) -> int | None:
        val = params.get(key)
        if val in (None, ""):
            return None
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    def _decimal(key: str) -> Decimal | None:
        val = params.get(key)
        if val in (None, ""):
            return None
        try:
            return Decimal(str(val))
        except Exception:
            return None

    sort = params.get("sort") or "brand"
    if sort not in SORT_CHOICES:
        sort = "brand"

    return {
        "available_only": available_only,
        "brand": brand,
        "year_min": _int("year_min"),
        "year_max": _int("year_max"),
        "price_min": _decimal("price_min"),
        "price_max": _decimal("price_max"),
        "sort": sort,
    }


def get_brand_choices() -> list[tuple[str, str]]:
    brands = (
        Car.objects.order_by("brand")
        .values_list("brand", flat=True)
        .distinct()
    )
    return [("", "Все марки")] + [(b, b) for b in brands]
