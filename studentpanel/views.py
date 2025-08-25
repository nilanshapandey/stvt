# studentpanel/views.py  ◆◆ copy-paste everything ◆◆
from datetime import date
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.db.models import Count
from urllib.parse import urljoin
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .forms import TicketForm, BatchSlotForm, RegistrationForm, ProjectRequestForm
from .models import (
    StudentProfile,
    FeeChallan,
    ProjectSelection,
    IDCard,
    Project,
    BatchSlot,
    Certificate,
    ProjectIncharge,
    Director,   # ✅ Added
)
    # Get director info

director = Director.objects.first()

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

    # ✅ Certificate context (NEW)
    certificate = Certificate.objects.filter(student=profile).order_by('-id').first()
    cert_ready = bool(certificate and getattr(certificate, 'certificate_pdf', None))
    # Prefer stored file URL when present; else fall back to your old route (if it streams PDF)
    cert_download_url = None
    if cert_ready and certificate.certificate_pdf:
        cert_download_url = certificate.certificate_pdf.url
    else:
        # optional fallback to old view if you had one:
        try:
            cert_download_url = reverse('studentpanel:certificate')
        except Exception:
            cert_download_url = None

    context = {
        "profile": profile,
        "challan": challan,
        "ticket_form": ticket_form,
        "project_req": project_sel,
        "project": project_sel.project if project_sel else None,
        "available_projects": available_projects,
        "id_card": id_card,
        "lor_is_pdf": bool(profile.lor_file and profile.lor_file.name.lower().endswith(".pdf")),
        "tab": request.GET.get("tab", "profile"),
        "today": date.today(),

        # NEW
        "certificate": certificate,
        "cert_ready": cert_ready,
        "cert_download_url": cert_download_url,
    }
    return render(request, "studentpanel/dashboard.html", context)




# ───────────────────────── Certificate ──────────────────────
@login_required
def certificate(request):
    profile = StudentProfile.objects.filter(user=request.user).first()
    if not profile:
        messages.warning(request, "Student profile not found.")
        return redirect("studentpanel:dashboard")

    project_sel = (
        ProjectSelection.objects
        .filter(student=profile, status="Approved")
        .select_related("project__batch_slot", "project__incharge")
        .first()
    )
    if not project_sel:
        messages.warning(request, "Project not found or not approved yet.")
        return redirect("studentpanel:dashboard")

    project = project_sel.project
    batch_slot = project.batch_slot
    certificate = Certificate.objects.filter(student=profile).first()
    director = Director.objects.first()

    # --- Build absolute URLs so images always load in new tab/print ---
    base = request.build_absolute_uri("/")  # e.g. http://127.0.0.1:8000/
    def abs_url(path_or_none):
        if not path_or_none:
            return None
        # if it's already absolute, return as-is
        if str(path_or_none).startswith("http://") or str(path_or_none).startswith("https://"):
            return path_or_none
        return urljoin(base, str(path_or_none).lstrip("/"))

    # Logo from MEDIA (change to STATIC if you actually serve it from static)
    logo_media_path = getattr(settings, "MEDIA_URL", "/media/") + "cert_assets/word/media/image1.png"
    logo_url = abs_url(logo_media_path)

    photo_url = abs_url(getattr(profile.photo, "url", None))
    incharge_sig_url = abs_url(getattr(getattr(project.incharge, "signature", None), "url", None))
    director_sig_url = abs_url(getattr(getattr(director, "signature", None), "url", None))

    context = {
        "profile": profile,
        "project": project,
        "incharge": project.incharge,
        "director": director,
        "start_date": getattr(batch_slot, "start_date", None),
        "end_date": getattr(batch_slot, "end_date", None),
        "today": date.today(),
        "issue_date": getattr(batch_slot, "start_date", date.today()),
        "certificate": certificate,

        # absolute URLs used by the template
        "logo_url": logo_url,
        "photo_url": photo_url,
        "incharge_sig_url": incharge_sig_url,
        "director_sig_url": director_sig_url,
    }
    return render(request, "studentpanel/certificate.html", context)


# ───────── Admin: All Verified Certificates ─────────
def view_all_certificates(request):
    certificates = Certificate.objects.filter(is_verified=True).select_related("student")
    return render(request, "studentpanel/certificate_all.html", {
        "certificates": certificates,
        "today": date.today()
    })


# ───────── Batch Allotment ─────────
@login_required
def batch_allotment(request):
    profile = StudentProfile.objects.get(user=request.user)
    batch_slots = BatchSlot.objects.all().order_by("start_date")

    already_selected = ProjectSelection.objects.filter(student=profile).first()
    if already_selected:
        return render(request, "studentpanel/select_project.html", {
            "already_selected": True,
            "project": already_selected.project,
            "slot": already_selected.project.batch_slot,
        })

    selected_slot = None
    available_projects = []

    if request.method == "POST":
        slot_id = request.POST.get("batch_slot")
        if slot_id:
            selected_slot = BatchSlot.objects.filter(id=slot_id).first()

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
                    messages.success(request, "✅ Project request submitted successfully!")
                    return redirect("/dashboard/?tab=batch")

        if selected_slot:
            available_projects = (
                Project.objects
                .filter(batch_slot=selected_slot, branch=profile.branch)
                .select_related("incharge")
                .annotate(available=F("slots") - F("slots_taken"))
                .filter(available__gt=0)
                .order_by("project_code")
            )

    return render(request, "studentpanel/select_project.html", {
        "batch_slots": batch_slots,
        "selected_slot": selected_slot,
        "projects": available_projects,
    })


@login_required
def fill_ticket(request):
    challan = FeeChallan.objects.filter(student__user=request.user).first()
    if not challan:
        messages.error(request, "Challan not found.")
        return redirect("studentpanel:dashboard")

    if request.method == "POST":
        challan.ticket_number = request.POST.get("ticket_number")
        challan.status = "Submitted"
        challan.save()
        messages.success(request, "Ticket number submitted successfully.")
        return redirect("studentpanel:dashboard")

    return render(request, "studentpanel/fill_ticket.html", {"challan": challan})


@login_required
def download_selected_certificates(request):
    if request.method == "POST":
        selected_ids = request.POST.getlist("selected_ids")

        if not selected_ids:
            messages.warning(request, "No students selected!")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        certificates = Certificate.objects.filter(pk__in=selected_ids).select_related("student")

        return render(request, "studentpanel/selected_certificates_print.html", {
            "certificates": certificates
        })

# ───────────────────────── Challan View ───────────────────────
@login_required
def challan_view(request):
    profile = StudentProfile.objects.filter(user=request.user).first()
    if not profile:
        messages.warning(request, "Student profile not found. Please register first.")
        return redirect("studentpanel:register")

    challan = FeeChallan.objects.filter(student=profile).first()
    if not challan:
        messages.warning(request, "Fee Challan not generated yet.")
        return redirect("studentpanel:dashboard")

    # Director singleton fetch karo
    director = Director.objects.first()

    context = {
        "profile": profile,
        "challan": challan,
        "director": director,
        "student_name": profile.user.get_full_name() or profile.user.username,  
        "unique_id": profile.unique_id,
        "date": challan.sent_on.strftime('%d-%m-%Y') if challan.sent_on else challan.created_on.strftime('%d-%m-%Y'),
    }
    return render(request, "studentpanel/challan.html", context)


# ───────────────────────── Admit Card ───────────────────────
@login_required
def admit_card(request):
    profile = StudentProfile.objects.filter(user=request.user).first()
    if not profile:
        messages.warning(request, "Profile not found.")
        return redirect("studentpanel:dashboard")

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
        "director": director,
    }
    return render(request, "studentpanel/admit_card.html", context)
