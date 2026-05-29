"""Бизнес-логика аренды (общая для API и веб-интерфейса)."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from carsharing.models import Car, Rental, UserProfile


@dataclass
class ServiceError:
    message: str
    status: int = 400


def get_user_profile(user: User) -> Optional[UserProfile]:
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        return None


def minimum_balance_for_car(car: Car) -> Decimal:
    minutes = getattr(settings, "MIN_RENTAL_MINUTES", 15)
    return car.price_per_minute * Decimal(minutes)


def calculate_rental_cost(rental: Rental, end_time=None) -> Decimal:
    end = end_time or timezone.now()
    delta = end - rental.start_time
    total_seconds = delta.total_seconds()
    if total_seconds <= 0:
        minutes = 1
    else:
        minutes = int(total_seconds // 60)
        if total_seconds % 60 > 0:
            minutes += 1
        minutes = max(1, minutes)
    return (rental.car.price_per_minute * Decimal(minutes)).quantize(Decimal("0.01"))


@transaction.atomic
def start_rental(user_id: int, car_id: int) -> tuple[Optional[Rental], Optional[ServiceError]]:
    try:
        user = User.objects.select_for_update().get(pk=user_id)
    except User.DoesNotExist:
        return None, ServiceError("Пользователь не найден", 404)

    profile = get_user_profile(user)
    if profile is None:
        return None, ServiceError("У пользователя нет профиля", 400)

    if profile.balance < Decimal("0"):
        return None, ServiceError("Отрицательный баланс: пополните счёт", 400)

    try:
        car = Car.objects.select_for_update().get(pk=car_id)
    except Car.DoesNotExist:
        return None, ServiceError("Автомобиль не найден", 404)

    if not car.is_available:
        return None, ServiceError("Автомобиль уже в аренде или недоступен", 400)

    if Rental.objects.filter(car=car, is_active=True).exists():
        return None, ServiceError("Автомобиль уже в аренде", 400)

    min_balance = minimum_balance_for_car(car)
    if profile.balance < min_balance:
        return None, ServiceError(
            f"Недостаточно средств. Нужно минимум {min_balance} ₽ на {settings.MIN_RENTAL_MINUTES} мин.",
            400,
        )

    if Rental.objects.filter(user=user, is_active=True).exists():
        return None, ServiceError("У вас уже есть активная аренда", 400)

    car.is_available = False
    car.save(update_fields=["is_available"])

    rental = Rental.objects.create(
        user=user,
        car=car,
        start_time=timezone.now(),
        is_active=True,
    )
    return rental, None


@transaction.atomic
def stop_rental(rental_id: int) -> tuple[Optional[Rental], Optional[ServiceError]]:
    try:
        rental = Rental.objects.select_for_update().select_related(
            "car", "user", "user__profile"
        ).get(pk=rental_id)
    except Rental.DoesNotExist:
        return None, ServiceError("Аренда не найдена", 404)

    if not rental.is_active:
        return None, ServiceError("Аренда уже завершена", 400)

    profile = get_user_profile(rental.user)
    if profile is None:
        return None, ServiceError("У пользователя нет профиля", 400)

    end_time = timezone.now()
    total_cost = calculate_rental_cost(rental, end_time)

    rental.end_time = end_time
    rental.total_cost = total_cost
    rental.is_active = False
    rental.save(update_fields=["end_time", "total_cost", "is_active"])

    profile.balance -= total_cost
    profile.save(update_fields=["balance"])

    car = rental.car
    car.is_available = True
    car.save(update_fields=["is_available"])

    return rental, None


@transaction.atomic
def topup_balance(user_id: int, amount: Decimal) -> tuple[Optional[UserProfile], Optional[ServiceError]]:
    if amount <= Decimal("0"):
        return None, ServiceError("Сумма пополнения должна быть больше нуля", 400)

    try:
        user = User.objects.select_for_update().get(pk=user_id)
    except User.DoesNotExist:
        return None, ServiceError("Пользователь не найден", 404)

    profile = get_user_profile(user)
    if profile is None:
        return None, ServiceError("У пользователя нет профиля", 400)

    profile.balance += amount
    profile.save(update_fields=["balance"])
    return profile, None


@transaction.atomic
def register_user(
    username: str,
    password: str,
    phone: str,
    email: str = "",
) -> tuple[Optional[User], Optional[ServiceError]]:
    username = username.strip()
    if not username:
        return None, ServiceError("Укажите имя пользователя", 400)
    if User.objects.filter(username=username).exists():
        return None, ServiceError("Имя пользователя уже занято", 400)
    if len(password) < 8:
        return None, ServiceError("Пароль должен быть не короче 8 символов", 400)
    try:
        validate_password(password)
    except ValidationError as exc:
        return None, ServiceError("; ".join(exc.messages), 400)

    user = User.objects.create_user(
        username=username,
        email=email.strip(),
        password=password,
    )
    UserProfile.objects.create(
        user=user,
        phone=phone.strip(),
        balance=Decimal("0.00"),
    )
    return user, None


@transaction.atomic
def create_car(data: dict[str, Any]) -> tuple[Optional[Car], Optional[ServiceError]]:
    plate = str(data.get("license_plate", "")).strip()
    if Car.objects.filter(license_plate=plate).exists():
        return None, ServiceError("Автомобиль с таким госномером уже существует", 400)
    car = Car.objects.create(**data)
    return car, None


@transaction.atomic
def update_car(
    car_id: int,
    data: dict[str, Any],
) -> tuple[Optional[Car], Optional[ServiceError]]:
    try:
        car = Car.objects.select_for_update().get(pk=car_id)
    except Car.DoesNotExist:
        return None, ServiceError("Автомобиль не найден", 404)

    if "license_plate" in data:
        plate = str(data["license_plate"]).strip()
        if (
            Car.objects.filter(license_plate=plate)
            .exclude(pk=car_id)
            .exists()
        ):
            return None, ServiceError("Автомобиль с таким госномером уже существует", 400)

    for field, value in data.items():
        setattr(car, field, value)
    car.save()
    return car, None


@transaction.atomic
def delete_car(car_id: int) -> Optional[ServiceError]:
    try:
        car = Car.objects.select_for_update().get(pk=car_id)
    except Car.DoesNotExist:
        return ServiceError("Автомобиль не найден", 404)

    if Rental.objects.filter(car=car, is_active=True).exists():
        return ServiceError("Нельзя удалить автомобиль с активной арендой", 400)

    car.delete()
    return None
