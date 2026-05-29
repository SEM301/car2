from decimal import Decimal

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from carsharing.models import Car
from carsharing.services import register_user

BOOTSTRAP = "form-control"


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=False,
        label="E-mail",
        widget=forms.EmailInput(attrs={"class": BOOTSTRAP}),
    )
    phone = forms.CharField(
        max_length=20,
        label="Телефон",
        widget=forms.TextInput(attrs={"class": BOOTSTRAP, "placeholder": "+79001234567"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "phone", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("username", "password1", "password2"):
            self.fields[name].widget.attrs.setdefault("class", BOOTSTRAP)

    def save(self, commit: bool = True) -> User:
        user, err = register_user(
            username=self.cleaned_data["username"],
            password=self.cleaned_data["password1"],
            phone=self.cleaned_data["phone"],
            email=self.cleaned_data.get("email", ""),
        )
        if err:
            raise forms.ValidationError(err.message)
        assert user is not None
        return user


class CarFilterForm(forms.Form):
    brand = forms.ChoiceField(
        label="Марка",
        required=False,
        choices=[],
        widget=forms.Select(attrs={"class": BOOTSTRAP}),
    )
    year_min = forms.IntegerField(
        label="Год от",
        required=False,
        min_value=1990,
        max_value=2030,
        widget=forms.NumberInput(attrs={"class": BOOTSTRAP, "placeholder": "2018"}),
    )
    year_max = forms.IntegerField(
        label="Год до",
        required=False,
        min_value=1990,
        max_value=2030,
        widget=forms.NumberInput(attrs={"class": BOOTSTRAP, "placeholder": "2024"}),
    )
    price_min = forms.DecimalField(
        label="Цена от (руб./мин)",
        required=False,
        min_value=Decimal("0"),
        widget=forms.NumberInput(attrs={"class": BOOTSTRAP, "step": "0.01"}),
    )
    price_max = forms.DecimalField(
        label="Цена до (руб./мин)",
        required=False,
        min_value=Decimal("0"),
        widget=forms.NumberInput(attrs={"class": BOOTSTRAP, "step": "0.01"}),
    )
    sort = forms.ChoiceField(
        label="Сортировка",
        required=False,
        choices=[
            ("brand", "По марке"),
            ("price", "Цена ↑"),
            ("-price", "Цена ↓"),
            ("-year", "Год ↓"),
            ("year", "Год ↑"),
        ],
        widget=forms.Select(attrs={"class": BOOTSTRAP}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from carsharing.car_filters import get_brand_choices

        self.fields["brand"].choices = get_brand_choices()


class TopupForm(forms.Form):
    amount = forms.DecimalField(
        label="Сумма пополнения",
        min_value=Decimal("0.01"),
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": BOOTSTRAP, "step": "0.01"}),
    )


class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = [
            "brand",
            "model",
            "year",
            "license_plate",
            "description",
            "image",
            "price_per_minute",
            "is_available",
            "latitude",
            "longitude",
        ]
        widgets = {
            "brand": forms.TextInput(attrs={"class": BOOTSTRAP}),
            "model": forms.TextInput(attrs={"class": BOOTSTRAP}),
            "year": forms.NumberInput(attrs={"class": BOOTSTRAP}),
            "license_plate": forms.TextInput(attrs={"class": BOOTSTRAP}),
            "description": forms.Textarea(attrs={"class": BOOTSTRAP, "rows": 4}),
            "image": forms.FileInput(attrs={"class": "form-control-file"}),
            "price_per_minute": forms.NumberInput(
                attrs={"class": BOOTSTRAP, "step": "0.01"}
            ),
            "is_available": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "latitude": forms.NumberInput(attrs={"class": BOOTSTRAP, "step": "any"}),
            "longitude": forms.NumberInput(attrs={"class": BOOTSTRAP, "step": "any"}),
        }
