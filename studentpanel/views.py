from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .forms import RegistrationForm
from .models import StudentProfile, FeeChallan, ProjectSelection, IDCard


# ─────────────────────────
#  Register
# ─────────────────────────
def register(request):
    form = RegistrationForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Registration successful. Please log in.")
        return redirect("studentpanel:login")

    return render(request, "studentpanel/register.html", {"form": form})


# ─────────────────────────
#  Login
# ─────────────────────────
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            # Preserve ?next= if present
            return redirect(request.GET.get("next", "studentpanel:dashboard"))
        messages.error(request, "Invalid credentials")

    return render(request, "studentpanel/login.html")


# ─────────────────────────
#  Logout
# ─────────────────────────
def logout_view(request):
    logout(request)
    return redirect("studentpanel:login")


# ─────────────────────────
#  Dashboard
# ─────────────────────────
@login_required
def dashboard(request):
    # fetch profile or force registration
    profile = StudentProfile.objects.filter(user=request.user).first()
    if not profile:
        messages.warning(request, "Student profile not found. Please register first.")
        return redirect("studentpanel:register")

    challan   = FeeChallan.objects.filter(student=profile).first()
    project   = ProjectSelection.objects.filter(student=profile).first()
    id_card   = IDCard.objects.filter(student=profile).first()

    active_tab = request.GET.get("tab", "profile")  # 'profile' default

    context = {
        "profile":  profile,
        "challan":  challan,
        "project":  project,
        "id_card":  id_card,
        "tab":      active_tab,
    }
    return render(request, "studentpanel/dashboard.html", context)
