from decimal import Decimal
from io import BytesIO
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw

from carsharing.data.cars_seed import CARS_SEED_DATA
from carsharing.models import Car, UserProfile
from carsharing.permissions import FLEET_MANAGER_GROUP

IMAGE_COLORS = [
    (26, 26, 26),
    (20, 35, 60),
    (45, 25, 35),
    (25, 50, 40),
    (55, 30, 20),
    (35, 35, 55),
    (40, 45, 25),
    (30, 30, 30),
    (15, 45, 55),
    (50, 25, 25),
    (28, 42, 48),
    (38, 28, 48),
    (32, 38, 28),
    (48, 38, 22),
    (22, 48, 38),
    (42, 22, 32),
    (33, 33, 42),
    (44, 36, 28),
    (26, 40, 44),
    (18, 22, 32),
]


class Command(BaseCommand):
    help = "Наполняет БД 20 автомобилями с фото и тестовыми пользователями"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--force-images",
            action="store_true",
            help="Пересоздать фото для всех автомобилей",
        )

    def _setup_fleet_manager_group(self) -> Group:
        ct = ContentType.objects.get_for_model(Car)
        perms = Permission.objects.filter(
            content_type=ct,
            codename__in=["add_car", "change_car", "view_car", "delete_car"],
        )
        group, _ = Group.objects.get_or_create(name=FLEET_MANAGER_GROUP)
        group.permissions.set(perms)
        return group

    def _generate_placeholder_image(self, title: str, color_index: int) -> ContentFile:
        base = IMAGE_COLORS[color_index % len(IMAGE_COLORS)]
        img = Image.new("RGB", (800, 500), color=base)
        draw = ImageDraw.Draw(img)
        accent = (201, 162, 39)
        draw.rectangle([(0, 420), (800, 500)], fill=accent)
        draw.rectangle([(40, 40), (760, 380)], outline=accent, width=3)
        draw.text((400, 200), title, fill=(255, 255, 255), anchor="mm")
        draw.text((400, 250), "Impel CarShare", fill=(180, 180, 180), anchor="mm")
        draw.text((400, 455), "Premium Fleet", fill=(20, 20, 20), anchor="mm")
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=88)
        buffer.seek(0)
        safe_name = "".join(c if c.isalnum() else "_" for c in title[:24])
        return ContentFile(buffer.read(), name=f"{safe_name}.jpg")

    def _download_car_image(self, seed: str, title: str, color_index: int) -> ContentFile:
        url = f"https://picsum.photos/seed/{seed}/800/500"
        try:
            with urlopen(url, timeout=12) as response:
                data = response.read()
            if len(data) > 1000:
                return ContentFile(data, name=f"{seed}.jpg")
        except (URLError, OSError):
            pass
        return self._generate_placeholder_image(title, color_index)

    def _save_car_image(
        self, car: Car, seed: str, title: str, color_index: int, force: bool
    ) -> None:
        if car.image and not force:
            return
        if car.image and force:
            car.image.delete(save=False)
        image_file = self._download_car_image(seed, title, color_index)
        car.image.save(image_file.name, image_file, save=True)

    def handle(self, *args: Any, **options: Any) -> None:
        force_images: bool = options["force_images"]
        fleet_group = self._setup_fleet_manager_group()

        seed_plates = [c["license_plate"] for c in CARS_SEED_DATA]
        removed, _ = Car.objects.exclude(license_plate__in=seed_plates).delete()
        if removed:
            self.stdout.write(f"Удалено устаревших записей: {removed}")

        for raw in CARS_SEED_DATA:
            data = raw.copy()
            image_seed = data.pop("image_seed")
            color_index = data.pop("color_index")
            is_available = data.pop("is_available", True)
            data.setdefault("is_available", is_available)

            car, created = Car.objects.update_or_create(
                license_plate=data["license_plate"],
                defaults=data,
            )
            title = f"{car.brand} {car.model}"
            self._save_car_image(car, image_seed, title, color_index, force_images)
            action = "Создан" if created else "Обновлён"
            self.stdout.write(f"{action}: {car}")

        self.stdout.write(self.style.SUCCESS(f"Автомобилей в базе: {Car.objects.count()}"))

        users_data = [
            {
                "username": "ivan",
                "email": "ivan@example.com",
                "phone": "+79001112233",
                "balance": Decimal("500.00"),
                "is_fleet": False,
            },
            {
                "username": "maria",
                "email": "maria@example.com",
                "phone": "+79004445566",
                "balance": Decimal("300.00"),
                "is_fleet": False,
            },
            {
                "username": "fleet_admin",
                "email": "fleet@example.com",
                "phone": "+79007778899",
                "balance": Decimal("0.00"),
                "is_fleet": True,
            },
        ]

        password = "password123"
        for data in users_data:
            is_fleet = data.pop("is_fleet")
            user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={"email": data["email"]},
            )
            if created or is_fleet:
                user.set_password(password)
                user.save()
            profile, _ = UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "phone": data["phone"],
                    "balance": data["balance"],
                },
            )
            if is_fleet:
                user.groups.add(fleet_group)
                self.stdout.write(
                    f"Менеджер автопарка: {user.username} (пароль: {password})"
                )
            else:
                action = "Создан" if created else "Обновлён"
                self.stdout.write(
                    f"{action} клиент: {user.username} "
                    f"(баланс {profile.balance} руб., пароль: {password})"
                )

        self.stdout.write(self.style.SUCCESS("Тестовые данные загружены."))
