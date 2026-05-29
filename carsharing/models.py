from decimal import Decimal
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

if TYPE_CHECKING:
    pass


class UserProfile(models.Model):
    """Расширение стандартного пользователя Django."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Пользователь",
    )
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Баланс",
    )

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

    def __str__(self) -> str:
        return f"{self.user.username} ({self.phone})"


class Car(models.Model):
    brand = models.CharField(max_length=100, verbose_name="Марка")
    model = models.CharField(max_length=100, verbose_name="Модель")
    year = models.IntegerField(verbose_name="Год выпуска")
    license_plate = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Госномер",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Описание",
        help_text="Краткое описание для страницы автомобиля",
    )
    image = models.ImageField(
        upload_to="cars/",
        blank=True,
        null=True,
        verbose_name="Фото",
    )
    price_per_minute = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Цена за минуту",
    )
    is_available = models.BooleanField(default=True, verbose_name="Доступна")
    latitude = models.FloatField(verbose_name="Широта")
    longitude = models.FloatField(verbose_name="Долгота")

    class Meta:
        verbose_name = "Автомобиль"
        verbose_name_plural = "Автомобили"
        ordering = ["brand", "model"]

    def __str__(self) -> str:
        return f"{self.brand} {self.model} ({self.license_plate})"

    @property
    def min_start_balance(self) -> Decimal:
        minutes = getattr(settings, "MIN_RENTAL_MINUTES", 15)
        return self.price_per_minute * Decimal(minutes)

    @property
    def display_name(self) -> str:
        return f"{self.brand} {self.model}"


class Rental(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="rentals",
        verbose_name="Пользователь",
    )
    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        related_name="rentals",
        verbose_name="Автомобиль",
    )
    start_time = models.DateTimeField(verbose_name="Начало аренды")
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Окончание аренды",
    )
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Итоговая стоимость",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    class Meta:
        verbose_name = "Аренда"
        verbose_name_plural = "Аренды"
        ordering = ["-start_time"]

    def __str__(self) -> str:
        status = "активна" if self.is_active else "завершена"
        return f"Аренда #{self.pk} — {self.car} ({status})"
