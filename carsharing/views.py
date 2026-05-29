from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.conf import settings
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from carsharing.car_filters import apply_car_filters, parse_filter_params
from carsharing.forms import CarFilterForm, CarForm, RegistrationForm, TopupForm
from carsharing.mixins import FleetManagerRequiredMixin
from carsharing.models import Car, Rental
from carsharing.services import start_rental, stop_rental, topup_balance


class HomeView(ListView):
    model = Car
    template_name = "carsharing/home.html"
    context_object_name = "cars"
    paginate_by = settings.CATALOG_PAGE_SIZE

    def get_queryset(self):
        filters = parse_filter_params(self.request.GET, available_only=True)
        return apply_car_filters(Car.objects.all(), **filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = CarFilterForm(self.request.GET or None)
        user = self.request.user
        if user.is_authenticated:
            context["active_rental"] = (
                Rental.objects.filter(user=user, is_active=True)
                .select_related("car")
                .first()
            )
        query = self.request.GET.copy()
        query.pop("page", None)
        context["filter_query"] = query.urlencode()
        return context


class CarDetailView(DetailView):
    model = Car
    template_name = "carsharing/car_detail.html"
    context_object_name = "car"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated:
            context["active_rental"] = (
                Rental.objects.filter(user=user, is_active=True)
                .select_related("car")
                .first()
            )
        return context


class ProfileView(LoginRequiredMixin, View):
    template_name = "carsharing/profile.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        profile = request.user.profile
        rentals = Rental.objects.filter(user=request.user).select_related("car")
        return render(
            request,
            self.template_name,
            {
                "profile": profile,
                "rentals": rentals,
                "topup_form": TopupForm(),
            },
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        form = TopupForm(request.POST)
        if form.is_valid():
            amount: Decimal = form.cleaned_data["amount"]
            profile, err = topup_balance(request.user.pk, amount)
            if err:
                messages.error(request, err.message)
            else:
                messages.success(
                    request,
                    f"Баланс пополнен на {amount} руб. Текущий: {profile.balance} руб.",
                )
            return redirect("profile")
        profile = request.user.profile
        rentals = Rental.objects.filter(user=request.user).select_related("car")
        return render(
            request,
            self.template_name,
            {
                "profile": profile,
                "rentals": rentals,
                "topup_form": form,
            },
        )


@login_required
def rent_car(request: HttpRequest, car_id: int) -> HttpResponse:
    rental, err = start_rental(request.user.pk, car_id)
    if err:
        messages.error(request, err.message)
        return redirect("car_detail", pk=car_id)
    messages.success(
        request,
        f"Аренда начата: {rental.car}. Управление поездкой — на странице аренды.",
    )
    return redirect("rental_stop", rental_id=rental.pk)


class RentalStopView(LoginRequiredMixin, View):
    template_name = "carsharing/rental_stop.html"

    def get(self, request: HttpRequest, rental_id: int) -> HttpResponse:
        rental = get_object_or_404(
            Rental.objects.select_related("car"),
            pk=rental_id,
            user=request.user,
        )
        return render(request, self.template_name, {"rental": rental})

    def post(self, request: HttpRequest, rental_id: int) -> HttpResponse:
        rental = get_object_or_404(Rental, pk=rental_id, user=request.user)
        rental, err = stop_rental(rental.pk)
        if err:
            messages.error(request, err.message)
            return redirect("rental_stop", rental_id=rental_id)
        messages.success(
            request,
            f"Аренда завершена. Списано: {rental.total_cost} руб.",
        )
        return redirect("profile")


class FleetCarListView(FleetManagerRequiredMixin, ListView):
    model = Car
    template_name = "carsharing/fleet/car_list.html"
    context_object_name = "cars"
    paginate_by = settings.FLEET_PAGE_SIZE

    def get_queryset(self):
        filters = parse_filter_params(self.request.GET, available_only=False)
        return apply_car_filters(Car.objects.all(), **filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = CarFilterForm(self.request.GET or None)
        query = self.request.GET.copy()
        query.pop("page", None)
        context["filter_query"] = query.urlencode()
        return context


class FleetCarCreateView(FleetManagerRequiredMixin, CreateView):
    model = Car
    form_class = CarForm
    template_name = "carsharing/fleet/car_form.html"
    success_url = reverse_lazy("fleet_car_list")

    def form_valid(self, form):
        messages.success(self.request, "Автомобиль добавлен в автопарк.")
        return super().form_valid(form)


class FleetCarUpdateView(FleetManagerRequiredMixin, UpdateView):
    model = Car
    form_class = CarForm
    template_name = "carsharing/fleet/car_form.html"
    success_url = reverse_lazy("fleet_car_list")

    def form_valid(self, form):
        messages.success(self.request, "Данные автомобиля обновлены.")
        return super().form_valid(form)


class RegisterView(CreateView):
    form_class = RegistrationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("home")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        messages.success(
            self.request,
            f"Аккаунт {self.object.username} создан. Войдите и пополните баланс.",
        )
        return redirect("login")
