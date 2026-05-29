from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpRequest

from carsharing.permissions import is_fleet_manager


class FleetManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Доступ только для менеджера автопарка."""

    def test_func(self) -> bool:
        return is_fleet_manager(self.request.user)

    def handle_no_permission(self) -> Any:
        if self.request.user.is_authenticated:
            self.raise_exception = True
        return super().handle_no_permission()
