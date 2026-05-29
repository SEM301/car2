from django.contrib.auth import views as auth_views
from django.urls import path

from carsharing import views

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("cars/<int:pk>/", views.CarDetailView.as_view(), name="car_detail"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("rent/<int:car_id>/", views.rent_car, name="rent_car"),
    path("rental/<int:rental_id>/", views.RentalStopView.as_view(), name="rental_stop"),
    path("fleet/", views.FleetCarListView.as_view(), name="fleet_car_list"),
    path("fleet/add/", views.FleetCarCreateView.as_view(), name="fleet_car_add"),
    path("fleet/<int:pk>/edit/", views.FleetCarUpdateView.as_view(), name="fleet_car_edit"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
