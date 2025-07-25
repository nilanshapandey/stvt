from datetime import datetime, date
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils.html import format_html

from studentpanel.views import view_all_certificates
from .models import (
    StudentProfile, FeeChallan, Project, ProjectSelection,
    IDCard, Certificate, BatchSlot
)

# ───────────────────────────────────────────────
FEE_AMOUNT = 2500
DUE_DAYS   = 7
# ───────────────────────────────────────────────

# ---------- StudentProfile ----------
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("student_name", "unique_id", "branch", "college", "is_selected", "payment_verified")
    list_filter = ("branch", "is_selected", "payment_verified")
    search_fields = ("student_name", "user__username", "unique_id")
    readonly_fields = ("unique_id",)
    exclude = ("lor_file",)

    def save_model(self, request, obj, form, change):
        first_select = obj.is_selected and not obj.unique_id
        super().save_model(request, obj, form, change)

        if first_select:
            year = datetime.now().year % 100
            seq = StudentProfile.objects.filter(is_selected=True).exclude(pk=obj.pk).count() + 1
            obj.unique_id = f"STVT{year}/{seq:02d}"
            obj.save(update_fields=["unique_id"])
            FeeChallan.objects.get_or_create(student=obj)


# ---------- BatchSlot ----------
@admin.register(BatchSlot)
class BatchSlotAdmin(admin.ModelAdmin):
    list_display = ("start_date", "end_date")


# ---------- Project ----------
class ProjectAdminForm(forms.ModelForm):
    branch = forms.ChoiceField(choices=[])

    class Meta:
        model = Project
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        branches = StudentProfile.objects.values_list("branch", flat=True).distinct().order_by("branch")
        self.fields["branch"].choices = [(b, b) for b in branches]

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    form = ProjectAdminForm
    list_display = ("title", "branch", "duration_weeks", "slots", "slots_taken")
    list_filter = ("branch", "duration_weeks")
    search_fields = ("title", "teacher")


# ---------- ProjectSelection ----------
@admin.register(ProjectSelection)
class ProjectSelectionAdmin(admin.ModelAdmin):
    list_display = ("student", "project", "status", "action_btn")
    list_filter = ("status", "project__branch")

    def get_urls(self):
        base = super().get_urls()
        extra = [
            path("approve/<int:pk>/", self.admin_site.admin_view(self._approve), name="psel_approve"),
            path("admit/<int:pk>/", self.admin_site.admin_view(self._send_admit), name="psel_send_admit"),
        ]
        return extra + base

    def action_btn(self, obj):
        if obj.status == "Pending":
            url = reverse("admin:psel_approve", args=[obj.pk])
            return format_html('<a class="button" href="{}">Approve</a>', url)
        elif obj.status == "Approved" and not hasattr(obj, "idcard"):
            url = reverse("admin:psel_send_admit", args=[obj.pk])
            return format_html('<a class="button" href="{}">Send Admit Card</a>', url)
        return "✔️"
    action_btn.short_description = "Action"

    def _approve(self, request, pk):
        sel = get_object_or_404(ProjectSelection, pk=pk)
        if sel.status != "Pending":
            self.message_user(request, "Already approved.", level=messages.WARNING)
            return redirect("..")
        sel.status = "Approved"
        sel.save(update_fields=["status"])

        profile = sel.student
        if not hasattr(profile, 'certificate'):
            year = datetime.now().year % 100
            count = Certificate.objects.filter(serial_number__startswith=f"CERT{year}/").count() + 1
            serial = f"CERT{year}/{count:02d}"
            Certificate.objects.create(student=profile, serial_number=serial)

        self.message_user(request, "Project approved & certificate created.", level=messages.SUCCESS)
        return redirect("..")

    def _send_admit(self, request, pk):
        sel = get_object_or_404(ProjectSelection, pk=pk)
        if sel.status != "Approved":
            self.message_user(request, "Project not approved.", level=messages.WARNING)
            return redirect("..")

        profile = sel.student
        project = sel.project
        ctx = {"profile": profile, "project": project}

        admit_html = render_to_string("studentpanel/admit_card.html", ctx)
        idcard, _ = IDCard.objects.get_or_create(student=profile)
        idcard.id_pdf.save(f"admit_{profile.unique_id}.html", ContentFile(admit_html.encode("utf-8")))
        idcard.save()

        link = request.build_absolute_uri("/dashboard/?tab=admit")
        send_mail(
            "Your Admit Card is Ready",
            f"Dear {profile.student_name},\n\nDownload your admit card:\n{link}",
            settings.DEFAULT_FROM_EMAIL,
            [profile.user.email],
            fail_silently=True,
        )

        self.message_user(request, "Admit card sent.", level=messages.SUCCESS)
        return redirect("..")


# ---------- Certificate ----------
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("student", "serial_number", "is_verified", "issued_on", "verify_btn")
    list_filter = ("is_verified",)
    readonly_fields = ("issued_on",)
    change_list_template = "admin/cert_change_list.html"

    def get_urls(self):
        base = super().get_urls()
        extra = [
            path("verify/<int:pk>/", self.admin_site.admin_view(self._verify), name="verify_certificate"),
            path("certified/", self.admin_site.admin_view(self._certified_students), name="certified_students"),
            path('certified/view_all/', self.admin_site.admin_view(view_all_certificates), name="cert_view_all_certificates"),

    ]
        
        return extra + base

    def verify_btn(self, obj):
        if not obj.is_verified:
            url = reverse("admin:verify_certificate", args=[obj.pk])
            return format_html('<a class="button" href="{}">Verify</a>', url)
        return "✔️"
    verify_btn.short_description = "Verify"

    def _verify(self, request, pk):
        cert = get_object_or_404(Certificate, pk=pk)
        cert.is_verified = True
        cert.issued_on = date.today()

        profile = cert.student
        project = ProjectSelection.objects.get(student=profile).project

        html = render_to_string("studentpanel/certificate.html", {
            "profile": profile,
            "project": project,
            "certificate": cert,
            "today": date.today(),
        })

        fname = f"certificate_{profile.unique_id}.html"
        cert.certificate_pdf.save(fname, ContentFile(html.encode("utf-8")))
        cert.save()

        link = request.build_absolute_uri(cert.certificate_pdf.url)
        send_mail(
            "Your Internship Certificate is Ready",
            f"Dear {profile.student_name},\n\nDownload your certificate:\n{link}",
            settings.DEFAULT_FROM_EMAIL,
            [profile.user.email],
        )

        self.message_user(request, "Certificate verified and sent.", level=messages.SUCCESS)
        return redirect("..")

  

    def _certified_students(self, request):
      certified = Certificate.objects.filter(is_verified=True).select_related('student')
      html = "<h2>Certified Students List</h2>"
      html += "<a href='view_all/' target='_blank'><button>View All Certificates</button></a>"
      html += "<table border='1' cellpadding='5'><tr><th>Name</th><th>ID</th><th>Serial</th><th>Date</th><th>Certificate</th></tr>"
      for cert in certified:
        url = cert.certificate_pdf.url if cert.certificate_pdf else "#"
        html += f"<tr><td>{cert.student.student_name}</td><td>{cert.student.unique_id}</td><td>{cert.serial_number}</td><td>{cert.issued_on}</td><td><a href='{url}' target='_blank'>Download</a></td></tr>"
      html += "</table>"
      return HttpResponse(html)

    def _cert_view_all(self, request):
      certified = Certificate.objects.filter(is_verified=True).select_related('student')
      context = {
        "certified": certified,
        "request": request,
    }
      return HttpResponse(render_to_string("studentpanel/certificate_all.html", context))

