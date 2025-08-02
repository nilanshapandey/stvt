# studentpanel/views.py  ◆◆ copy‑paste everything ◆◆
from datetime import date
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.db.models import Count
from .forms import TicketForm  # ✅ Add this
from .forms import BatchSlotForm
from .models import BatchSlot, Certificate 
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
    profile = StudentProfile.objects.filter(user=request.user).first()
    if not profile:
        messages.warning(request, "Student profile not found. Please register first.")
        return redirect("studentpanel:register")

    challan = FeeChallan.objects.filter(student=profile).first()
    project_sel = ProjectSelection.objects.filter(student=profile).first()
    id_card = IDCard.objects.filter(student=profile).first()

    # ✅ Ticket Form Logic
    ticket_form = None
    if challan and not challan.ticket_number:
        ticket_form = TicketForm(instance=challan)

    if request.method == "POST" and "ticket_submit" in request.POST:
        ticket_form = TicketForm(request.POST, instance=challan)
        if ticket_form.is_valid():
            ticket_form.save()
            messages.success(request, "Ticket number submitted successfully!")
            return redirect("/dashboard/?tab=batch")

    # ✅ Project Request Logic
    if request.method == "POST" and "project_id" in request.POST and profile.payment_verified:
        form = ProjectRequestForm(profile.branch, request.POST)
        if form.is_valid() and not project_sel:
            proj = form.cleaned_data["project_id"]
            ProjectSelection.objects.create(student=profile, project=proj, status="Pending")
            proj.slots_taken = F("slots_taken") + 1
            proj.save(update_fields=["slots_taken"])
            messages.success(request, "Project request submitted. Await admin approval.")
            return redirect("/dashboard/?tab=batch")

    available_projects = None
    if profile.payment_verified and not project_sel:
        available_projects = (
            Project.objects
            .filter(branch=profile.branch)
            .annotate(available=F("slots") - F("slots_taken"))
            .filter(available__gt=0)
        )

    context = {
        "profile": profile,
        "challan": challan,
        "ticket_form": ticket_form,  # ✅ Added
        "project_req": project_sel,
        "project": project_sel.project if project_sel else None,
        "available_projects": available_projects,
        "id_card": id_card,
        "lor_is_pdf": bool(profile.lor_file and profile.lor_file.name.lower().endswith(".pdf")),
        "tab": request.GET.get("tab", "profile"),
        "today": date.today(),
    }
    return render(request, "studentpanel/dashboard.html", context)




#----------------------------


@login_required
def admit_card(request):
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




# --- 3. New view function in views.py ---

@login_required
def certificate(request):
    profile = StudentProfile.objects.filter(user=request.user).first()
    if not profile:
        messages.warning(request, "Student profile not found.")
        return redirect("studentpanel:dashboard")

    project_sel = ProjectSelection.objects.filter(student=profile, status="Approved").first()
    if not project_sel:
        messages.warning(request, "Project not found or not approved yet.")
        return redirect("studentpanel:dashboard")

    project = project_sel.project
    batch_slot = project_sel.batch_slot 
    today = date.today()
    certificate = Certificate.objects.filter(student=profile).first()

    context = {
        "profile": profile,
        "project": project,
        "start_date": batch_slot.start_date if batch_slot else None,
        "end_date": batch_slot.end_date if batch_slot else None,
        "today": today,
        "certificate": certificate,
    }
    return render(request, "studentpanel/certificate_tab.html", context)


# ✅ Admin view: All Verified Certificates

def view_all_certificates(request):
    certificates = Certificate.objects.filter(is_verified=True).select_related("student")
    return render(request, "studentpanel/certificate_all.html", {
        "certificates": certificates,
        "today": date.today()
    })











# ───────── Batch Allotment Step 1 ─────────
# views.py
@login_required
def batch_allotment(request):
    profile = StudentProfile.objects.get(user=request.user)
    batch_slots = BatchSlot.objects.all().order_by("start_date")

    # If project already selected, show message only (no form)
    already_selected = ProjectSelection.objects.filter(student=profile).first()
    if already_selected:
        return render(request, "studentpanel/select_project.html", {
            "already_selected": True,
            "project": already_selected.project,
            "slot": already_selected.project.batch_slot,
        })

    selected_slot = None
    projects = []

    if request.method == "POST":
        slot_id = request.POST.get("batch_slot")
        if slot_id:
            selected_slot = BatchSlot.objects.filter(id=slot_id).first()

        # If project selection step
        if "project_id" in request.POST:
            project_id = request.POST.get("project_id")
            if project_id:
                project = Project.objects.get(id=project_id)
                if project.slots_taken >= project.slots:
                    messages.error(request, "This project is already full.")
                else:
                    ProjectSelection.objects.create(student=profile, project=project, status="Pending")
                    project.slots_taken = F("slots_taken") + 1
                    project.save(update_fields=["slots_taken"])
                    messages.success(request, "Project request submitted successfully!")
                    return redirect("/dashboard/?tab=batch")

        # Only fetch projects if slot is selected but no project yet
        if selected_slot:
            projects = (
                Project.objects
                .filter(batch_slot=selected_slot, branch=profile.branch)
                .annotate(available=F("slots") - F("slots_taken"))
                .order_by("project_code")
            )

    return render(request, "studentpanel/select_project.html", {
        "batch_slots": batch_slots,
        "selected_slot": selected_slot,
        "projects": projects,
    })

@login_required
def fill_ticket(request):
    challan = FeeChallan.objects.filter(student__user=request.user).first()
    if not challan:
        messages.error(request, "Challan not found.")
        return redirect("studentpanel:dashboard")

    if request.method == "POST":
        challan.ticket_number = request.POST.get("ticket_number")
        challan.status = "Submitted"  # ✅ जैसे ही ticket भरेंगे, Submitted हो जाएगा
        challan.save()
        messages.success(request, "Ticket number submitted successfully.")
        return redirect("studentpanel:dashboard")

    return render(request, "studentpanel/fill_ticket.html", {"challan": challan})
