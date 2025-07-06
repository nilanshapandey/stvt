# studentpanel/views.py  ◆◆ copy‑paste everything ◆◆
from datetime import date
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.shortcuts import redirect, render

from .forms import RegistrationForm, ProjectRequestForm
from .models import (
    StudentProfile,
    FeeChallan,
    ProjectSelection,
    IDCard,
    Project,
)

# ───────────────────────── Register ─────────────────────────
def register(request):
    form = RegistrationForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Registration successful. Please log in.")
        return redirect("studentpanel:login")

    return render(request, "studentpanel/register.html", {"form": form})


# ───────────────────────── Login ────────────────────────────
def login_view(request):
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password"),
        )
        if user:
            login(request, user)
            return redirect(request.GET.get("next", "studentpanel:dashboard"))
        messages.error(request, "Invalid credentials")
    return render(request, "studentpanel/login.html")


# ───────────────────────── Logout ───────────────────────────
def logout_view(request):
    logout(request)
    return redirect("studentpanel:login")


# ───────────────────────── Dashboard ────────────────────────
@login_required
def dashboard(request):
    # 1️⃣  fetch student profile
    profile = StudentProfile.objects.filter(user=request.user).first()
    if not profile:
        messages.warning(request, "Student profile not found. Please register first.")
        return redirect("studentpanel:register")
    

    # 2️⃣  related objects
    challan     = FeeChallan.objects.filter(student=profile).first()
    project_sel = ProjectSelection.objects.filter(student=profile).first()
    id_card     = IDCard.objects.filter(student=profile).first()

    # 3️⃣  handle inline project‑request POST
    if request.method == "POST" and "project_id" in request.POST and profile.payment_verified:
        form = ProjectRequestForm(profile.branch, request.POST)
        if form.is_valid() and not project_sel:
            proj = form.cleaned_data["project_id"]
            ProjectSelection.objects.create(student=profile, project=proj, status="Pending")
            proj.slots_taken = F("slots_taken") + 1
            proj.save(update_fields=["slots_taken"])
            messages.success(request, "Project request submitted. Await admin approval.")
            return redirect("/dashboard/?tab=batch")

    # 4️⃣  helpers for template
    lor_is_pdf  = bool(profile.lor_file and profile.lor_file.name.lower().endswith(".pdf"))
    active_tab  = request.GET.get("tab", "profile")

    available_projects = None
    if profile.payment_verified and not project_sel:
        available_projects = (
            Project.objects
            .filter(branch=profile.branch)
            .annotate(available=F("slots") - F("slots_taken"))
            .filter(available__gt=0)
        )

    context = {
        "profile":            profile,
        "challan":            challan,
        "project_req":        project_sel,
        "project":            project_sel.project if project_sel else None,
        "available_projects": available_projects,
        "id_card":            id_card,
        "lor_is_pdf":         lor_is_pdf,
        "tab":                active_tab,
        "today":              date.today(),
    }
    return render(request, "studentpanel/dashboard.html", context)
@login_required
def view_admit_card(request):
    """
    Renders a REAL‑TIME admit card for the logged‑in student.
    It uses exactly the same context (`profile`, `project`) that the
    admin action used when it created the file.
    """
    profile = StudentProfile.objects.filter(user=request.user).first()
    if not profile:
        messages.warning(request, "Profile not found.")
        return redirect("studentpanel:dashboard")

    # The student's approved project (if any)
    psel = (
        ProjectSelection.objects
        .filter(student=profile, status="Approved")
        .select_related("project")
        .first()
    )
    if not psel:
        messages.warning(request, "Project not approved yet.")
        return redirect("studentpanel:dashboard")

    context = {
        "profile": profile,
        "project": psel.project,
    }
    return render(request, "studentpanel/admit_card.html", context)


