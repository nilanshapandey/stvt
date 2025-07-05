from django.urls import path
from . import views

app_name = "studentpanel"

urlpatterns = [
    # --- Root now shows the registration form ---
    path("",                   views.register,    name="register"),

    # Authentication
    path("login/",             views.login_view,  name="login"),
    path("logout/",            views.logout_view, name="logout"),
    path("accounts/login/",    views.login_view),          # alias for Django redirects

    # Dashboard lives here
    path("dashboard/",         views.dashboard,   name="dashboard"),
]
