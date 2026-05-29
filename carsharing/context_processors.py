from django.http import HttpRequest

from carsharing.permissions import is_fleet_manager


def site_roles(request: HttpRequest) -> dict[str, bool]:
    return {
        "is_fleet_manager": is_fleet_manager(request.user),
    }
