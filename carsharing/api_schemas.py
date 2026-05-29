from datetime import datetime
from decimal import Decimal

from ninja import Schema


class CarOut(Schema):
    id: int
    brand: str
    model: str
    year: int
    license_plate: str
    description: str
    image_url: str | None
    price_per_minute: Decimal
    is_available: bool
    latitude: float
    longitude: float


class CarCreateIn(Schema):
    brand: str
    model: str
    year: int
    license_plate: str
    price_per_minute: Decimal
    latitude: float
    longitude: float
    description: str = ""
    is_available: bool = True


class CarUpdateIn(Schema):
    brand: str | None = None
    model: str | None = None
    year: int | None = None
    license_plate: str | None = None
    description: str | None = None
    price_per_minute: Decimal | None = None
    is_available: bool | None = None
    latitude: float | None = None
    longitude: float | None = None


class RentalStartIn(Schema):
    car_id: int
    user_id: int


class RentalOut(Schema):
    id: int
    user_id: int
    car_id: int
    start_time: datetime
    end_time: datetime | None
    total_cost: Decimal | None
    is_active: bool


class TopupIn(Schema):
    user_id: int
    amount: Decimal


class TopupOut(Schema):
    user_id: int
    balance: Decimal


class RegisterIn(Schema):
    username: str
    password: str
    phone: str
    email: str = ""


class UserOut(Schema):
    id: int
    username: str
    email: str
    phone: str
    balance: Decimal


class ErrorOut(Schema):
    detail: str


class CarsPageOut(Schema):
    items: list[CarOut]
    count: int
    page: int
    page_size: int
    pages: int
