from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from carsharing.models import Car, Rental, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = (
        "brand",
        "model",
        "year",
        "license_plate",
        "price_per_minute",
        "is_available",
        "has_image",
    )
    list_filter = ("is_available", "brand", "year")
    search_fields = ("brand", "model", "license_plate")
    readonly_fields = ("image_preview",)

    @admin.display(boolean=True, description="Фото")
    def has_image(self, obj: Car) -> bool:
        return bool(obj.image)

    @admin.display(description="Превью")
    def image_preview(self, obj: Car) -> str:
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:120px"/>', obj.image.url
            )
        return "—"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "balance")
    search_fields = ("user__username", "phone", "user__email")


@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "car",
        "start_time",
        "end_time",
        "total_cost",
        "is_active",
    )
    list_filter = ("is_active", "start_time", "end_time")
    search_fields = ("user__username", "car__license_plate", "car__brand")
    date_hierarchy = "start_time"
    raw_id_fields = ("user", "car")
