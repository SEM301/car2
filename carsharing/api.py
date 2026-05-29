"""REST API на Django Ninja."""

from django.conf import settings
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.http import HttpRequest
from ninja import NinjaAPI, Query, Router
from ninja.errors import HttpError

from carsharing.api_auth import fleet_auth, require_fleet_manager
from carsharing.api_schemas import (
    CarCreateIn,
    CarOut,
    CarUpdateIn,
    CarsPageOut,
    ErrorOut,
    RegisterIn,
    RentalOut,
    RentalStartIn,
    TopupIn,
    TopupOut,
    UserOut,
)
from carsharing.car_filters import apply_car_filters, parse_filter_params
from carsharing.models import Car, Rental
from carsharing.services import (
    ServiceError,
    create_car,
    delete_car,
    register_user,
    start_rental,
    stop_rental,
    topup_balance,
    update_car,
)

api = NinjaAPI(
    title="Carsharing API",
    version="1.1.0",
    description="API сервиса каршеринга",
)

auth_router = Router(tags=["auth"])
fleet_router = Router(tags=["fleet"])


def _car_to_schema(request: HttpRequest, car: Car) -> CarOut:
    image_url = None
    if car.image:
        image_url = request.build_absolute_uri(car.image.url)
    return CarOut(
        id=car.pk,
        brand=car.brand,
        model=car.model,
        year=car.year,
        license_plate=car.license_plate,
        description=car.description or "",
        image_url=image_url,
        price_per_minute=car.price_per_minute,
        is_available=car.is_available,
        latitude=car.latitude,
        longitude=car.longitude,
    )


def _rental_to_schema(rental: Rental) -> RentalOut:
    return RentalOut(
        id=rental.pk,
        user_id=rental.user_id,
        car_id=rental.car_id,
        start_time=rental.start_time,
        end_time=rental.end_time,
        total_cost=rental.total_cost,
        is_active=rental.is_active,
    )


def _user_to_schema(user: User) -> UserOut:
    profile = user.profile
    return UserOut(
        id=user.pk,
        username=user.username,
        email=user.email or "",
        phone=profile.phone,
        balance=profile.balance,
    )


def _raise_service_error(err: ServiceError) -> None:
    raise HttpError(err.status, err.message)


@api.get("/cars", response={200: CarsPageOut})
def list_cars(
    request: HttpRequest,
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.API_CARS_PAGE_SIZE, ge=1, le=50),
    brand: str | None = Query(None),
    year_min: int | None = Query(None),
    year_max: int | None = Query(None),
    price_min: float | None = Query(None),
    price_max: float | None = Query(None),
    sort: str = Query("brand"),
) -> CarsPageOut:
    """Список доступных автомобилей с фильтрами и пагинацией."""
    filters = parse_filter_params(
        {
            "brand": brand or "",
            "year_min": year_min,
            "year_max": year_max,
            "price_min": price_min,
            "price_max": price_max,
            "sort": sort,
        },
        available_only=True,
    )
    queryset = apply_car_filters(Car.objects.all(), **filters)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    return CarsPageOut(
        items=[_car_to_schema(request, car) for car in page_obj.object_list],
        count=paginator.count,
        page=page_obj.number,
        page_size=page_size,
        pages=paginator.num_pages,
    )

@api.get("/cars/{car_id}", response={200: CarOut, 404: ErrorOut})
def get_car(request: HttpRequest, car_id: int) -> CarOut:
    """Детали автомобиля."""
    try:
        car = Car.objects.get(pk=car_id)
    except Car.DoesNotExist:
        raise HttpError(404, "Автомобиль не найден")
    return _car_to_schema(request, car)

@auth_router.post(
    "/register",
    response={201: UserOut, 400: ErrorOut},
    summary="Регистрация нового пользователя",
)
def api_register(request: HttpRequest, payload: RegisterIn) -> tuple[int, UserOut]:
    user, err = register_user(
        username=payload.username,
        password=payload.password,
        phone=payload.phone,
        email=payload.email,
    )
    if err:
        _raise_service_error(err)
    assert user is not None
    return 201, _user_to_schema(user)


# --- Управление автопарком (менеджер, Basic Auth) ---


@fleet_router.get(
    "/cars",
    response={200: list[CarOut], 403: ErrorOut},
    auth=fleet_auth,
    summary="Список всех автомобилей (менеджер)",
)
def fleet_list_cars(request: HttpRequest) -> list[CarOut]:
    require_fleet_manager(request)
    cars = Car.objects.all()
    return [_car_to_schema(request, car) for car in cars]


@fleet_router.post(
    "/cars",
    response={201: CarOut, 400: ErrorOut, 403: ErrorOut},
    auth=fleet_auth,
    summary="Добавить автомобиль",
)
def fleet_create_car(request: HttpRequest, payload: CarCreateIn) -> tuple[int, CarOut]:
    require_fleet_manager(request)
    car, err = create_car(payload.model_dump())
    if err:
        _raise_service_error(err)
    assert car is not None
    return 201, _car_to_schema(request, car)


@fleet_router.put(
    "/cars/{car_id}",
    response={200: CarOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=fleet_auth,
    summary="Редактировать автомобиль",
)
def fleet_update_car(
    request: HttpRequest, car_id: int, payload: CarUpdateIn
) -> CarOut:
    require_fleet_manager(request)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HttpError(400, "Нет данных для обновления")
    car, err = update_car(car_id, data)
    if err:
        _raise_service_error(err)
    assert car is not None
    return _car_to_schema(request, car)


@fleet_router.delete(
    "/cars/{car_id}",
    response={200: dict, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=fleet_auth,
    summary="Удалить автомобиль",
)
def fleet_delete_car(request: HttpRequest, car_id: int) -> dict[str, str]:
    require_fleet_manager(request)
    err = delete_car(car_id)
    if err:
        _raise_service_error(err)
    return {"detail": "Автомобиль удалён"}


# --- Аренда и пользователи ---


@api.post("/rentals/start", response={200: RentalOut, 400: ErrorOut, 404: ErrorOut})
def rental_start(request: HttpRequest, payload: RentalStartIn) -> RentalOut:
    """Начать аренду."""
    rental, err = start_rental(payload.user_id, payload.car_id)
    if err:
        _raise_service_error(err)
    assert rental is not None
    return _rental_to_schema(rental)


@api.post(
    "/rentals/stop/{rental_id}",
    response={200: RentalOut, 400: ErrorOut, 404: ErrorOut},
)
def rental_stop(request: HttpRequest, rental_id: int) -> RentalOut:
    """Завершить аренду."""
    rental, err = stop_rental(rental_id)
    if err:
        _raise_service_error(err)
    assert rental is not None
    return _rental_to_schema(rental)


@api.post("/users/topup", response={200: TopupOut, 400: ErrorOut, 404: ErrorOut})
def user_topup(request: HttpRequest, payload: TopupIn) -> TopupOut:
    """Пополнение баланса."""
    profile, err = topup_balance(payload.user_id, payload.amount)
    if err:
        _raise_service_error(err)
    assert profile is not None
    return TopupOut(user_id=profile.user_id, balance=profile.balance)


@api.get(
    "/rentals/history/{user_id}",
    response={200: list[RentalOut], 404: ErrorOut},
)
def rental_history(request: HttpRequest, user_id: int) -> list[RentalOut]:
    """История аренд пользователя."""
    if not User.objects.filter(pk=user_id).exists():
        raise HttpError(404, "Пользователь не найден")
    rentals = Rental.objects.filter(user_id=user_id).select_related("car")
    return [_rental_to_schema(r) for r in rentals]


api.add_router("/auth", auth_router)
api.add_router("/fleet", fleet_router)
