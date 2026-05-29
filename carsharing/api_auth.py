from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import HttpRequest
from ninja.errors import HttpError
from ninja.security import HttpBasicAuth

from carsharing.permissions import is_fleet_manager


class FleetManagerBasicAuth(HttpBasicAuth):
    """Basic Auth для операций менеджера автопарка в API."""

    def authenticate(self, request: HttpRequest, username: str, password: str) -> User | None:
        user = authenticate(request, username=username, password=password)
        if user is not None and is_fleet_manager(user):
            return user
        return None


fleet_auth = FleetManagerBasicAuth()


def require_fleet_manager(request: HttpRequest) -> User:
    user = getattr(request, "auth", None)
    if not isinstance(user, User) or not is_fleet_manager(user):
        raise HttpError(403, "Доступ только для менеджера автопарка")
    return user
