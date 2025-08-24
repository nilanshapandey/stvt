from django.urls import path
from . import views

app_name = "studentpanel"

urlpatterns = [
    path("",          views.dashboard,  name="dashboard"),   # default home
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Batch Allotment – Step 1: Select Date
     path("batch/", views.batch_allotment, name="batch_allotment"),

    # Batch Allotment – Step 2: Choose Week + Project
   # path('batch/week/', views.choose_week, name='choose_week'),

    # View Admit Card (ID Slip)
    path('admit-card/', views.admit_card, name='admit_card'),

    # View Certificate
    path('certificate/', views.certificate, name='certificate'),
    path('admin/studentpanel/certificates/view_all/', views.view_all_certificates, name='view_all_certificates'),
    path("certificates/download-selected/", views.download_selected_certificates, name="download_selected_certificates"),

    # Challan view
    path('challan/', views.challan_view, name='challan'),

]