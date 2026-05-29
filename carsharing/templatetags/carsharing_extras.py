from django import template
from django.templatetags.static import static

from carsharing.models import Car

register = template.Library()


@register.simple_tag
def car_image(car: Car) -> str:
    if car.image:
        return car.image.url
    return static("carsharing/img/car-placeholder.svg")
