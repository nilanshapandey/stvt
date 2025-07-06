# studentpanel/urls.py
from django.urls import path
from . import views

app_name = "studentpanel"

urlpatterns = [
    path("",          views.dashboard,  name="dashboard"),   # default home
     path("dashboard/", views.dashboard),  
    path("register/", views.register,   name="register"),
    path("login/",    views.login_view, name="login"),
    path("logout/",   views.logout_view, name="logout"),
    # ❌ select_project path हटाया गया – अब ज़रूरत नहीं
    path("admit-card/", views.view_admit_card, name="admit_card"),
]
