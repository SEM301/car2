from django.contrib.auth.models import User


FLEET_MANAGER_GROUP = "fleet_manager"


def is_fleet_manager(user: User) -> bool:
    """Менеджер автопарка: создание и редактирование автомобилей."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=FLEET_MANAGER_GROUP).exists()
