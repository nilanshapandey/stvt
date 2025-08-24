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
#from .models import CertificateSettings
from studentpanel.views import view_all_certificates
from .models import (
    StudentProfile, FeeChallan, Project, ProjectSelection,
    IDCard, Certificate, BatchSlot, ProjectIncharge, Director
)


# ──────────────────────────────
FEE_AMOUNT = 2500
DUE_DAYS = 7
# ──────────────────────────────


# ---------- Student Profile ----------
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


# ---------- Batch Slot ----------
@admin.register(BatchSlot)
class BatchSlotAdmin(admin.ModelAdmin):
    list_display = ("start_date", "end_date")


# ---------- Fee Challan ----------
@admin.register(FeeChallan)
class FeeChallanAdmin(admin.ModelAdmin):
    list_display = ("student", "status", "ticket_number", "created_on", "sent_on", "send_btn", "verify_btn")
    list_filter = ("status",)

    def get_urls(self):
        base = super().get_urls()
        extra = [
            path("send/<int:pk>/", self.admin_site.admin_view(self._send_single), name="fee_send_single"),
            path("verify/<int:pk>/", self.admin_site.admin_view(self._verify_single), name="fee_verify_single"),
        ]
        return extra + base

    def send_btn(self, obj):
        if obj.status == "Pending":
            url = reverse("admin:fee_send_single", args=[obj.pk])
            return format_html('<a class="button" href="{}">Send Challan</a>', url)
        return "✔️"
    send_btn.short_description = "Send"

    def verify_btn(self, obj):
        if obj.status == "Sent":
            url = reverse("admin:fee_verify_single", args=[obj.pk])
            return format_html('<a class="button" href="{}">Verify Payment</a>', url)
        return "✔️" if obj.status == "Verified" else "-"
    verify_btn.short_description = "Payment"

    def _send_single(self, request, pk):
        challan = get_object_or_404(FeeChallan, pk=pk)
        if challan.status != "Pending":
            self.message_user(request, "Already processed.", level=messages.WARNING)
            return redirect("..")
        self._generate_and_email_challan(request, challan)
        self.message_user(request, "Challan sent.", level=messages.SUCCESS)
        return redirect("..")

    def _verify_single(self, request, pk):
        challan = get_object_or_404(FeeChallan, pk=pk)
        if challan.status != "Sent":
            self.message_user(request, "Challan not in 'Sent' state.", level=messages.WARNING)
            return redirect("..")
        challan.status = "Verified"
        challan.save(update_fields=["status"])
        profile = challan.student
        profile.payment_verified = True
        profile.save(update_fields=["payment_verified"])
        link = request.build_absolute_uri("/dashboard/?tab=batch")
        send_mail(
            "Payment Verified – Select Your Project",
            f"Dear {profile.student_name},\n\nYour fee payment is verified. "
            f"Please log in to your dashboard and choose your project:\n{link}\n\nRegards,\nTraining Centre",
            settings.DEFAULT_FROM_EMAIL,
            [profile.user.email],
            fail_silently=True,
        )
        self.message_user(request, "Payment verified & student notified.", level=messages.SUCCESS)
        return redirect("..")

    def _generate_and_email_challan(self, request, challan):
        profile = challan.student
        html = render_to_string("studentpanel/challan.html", {
            "student_name": profile.student_name,
            "unique_id": profile.unique_id,
            "date": date.today().strftime("%d-%m-%Y"),
        })
        fname = f"challan_{profile.unique_id}.html"
        challan.challan_pdf.save(fname, ContentFile(html.encode("utf-8")))
        challan.status = "Sent"
        challan.sent_on = datetime.now()
        challan.save(update_fields=["challan_pdf", "status", "sent_on"])

        dash_link = request.build_absolute_uri("/dashboard/?tab=challan")
        send_mail(
            "Your Fee Challan is Ready",
            "",
            settings.DEFAULT_FROM_EMAIL,
            [profile.user.email],
            html_message=render_to_string("studentpanel/email_challan.html", {
                "student": profile.student_name,
                "link": dash_link,
            }),
            fail_silently=True,
        )


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
    list_display = ("title", "branch", "duration_weeks", "slots", "slots_taken",  "incharge", "concerd_shop", "pdf_btn")
    list_filter = ("branch", "duration_weeks","incharge")
    search_fields = ("title", "project_code", "incharge__name", "concerd_shop")
    fieldsets = (
        ("Project Info", {
            "fields": ("project_code", "title", "branch", "incharge", "slots", "slots_taken", "batch_slot", "concerd_shop")
        }),
    )
    # ✅ Add button to view project PDF
    def get_urls(self):
        base = super().get_urls()
        extra = [
            path("project-pdf/<int:pk>/", self.admin_site.admin_view(self.view_project_pdf), name="project_pdf"),
        ]
        return extra + base

    def pdf_btn(self, obj):
        url = reverse("admin:project_pdf", args=[obj.pk])
        return format_html(f'<a class="button" target="_blank" href="{url}">📄 View PDF</a>')
    pdf_btn.short_description = "Project PDF"

    def view_project_pdf(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        students = ProjectSelection.objects.filter(project=project, status="Approved").select_related("student")
        html = render_to_string("studentpanel/batch_pdf.html", {"project": project, "students": students})
        return HttpResponse(html)


# Custom Filter for ProjectIncharge
class ProjectInchargeFilter(admin.SimpleListFilter):
    title = "Project Incharge"
    parameter_name = "project_incharge"

    def lookups(self, request, model_admin):
        incharges = ProjectIncharge.objects.all()
        return [(incharge.id, incharge.name) for incharge in incharges]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(project__Guide_By__id=self.value())
        return queryset




# ---------- Project Selection ----------
@admin.register(ProjectSelection)
class ProjectSelectionAdmin(admin.ModelAdmin):
    list_display = ("student", "project", "status", "action_btn")
    list_filter = ("status", "project", ProjectInchargeFilter)

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

    # Fields shown in the admin form
    fieldsets = (
        ("Certificate Info", {
            "fields": ("student", "serial_number", "is_verified", "issued_on")
        }),
        ("Training Incharge", {
            "fields": ("training_incharge_name", "training_incharge_signature")
        }),
        ("Director", {
            "fields": ("director_name", "director_signature")
        }),
    )

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

        # Render certificate HTML with dynamic signatures/names
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
        html = render_to_string("studentpanel/certificate_students.html", {"certified": certified})
        return HttpResponse(html)

'''@admin.register(CertificateSettings)
class CertificateSettingsAdmin(admin.ModelAdmin):
    list_display = ('training_incharge_name', 'director_name')'''


# ---------- Project Incharge ----------
@admin.register(ProjectIncharge)
class ProjectInchargeAdmin(admin.ModelAdmin):
    list_display = ("name", "signature_preview")

    def signature_preview(self, obj):
        if obj.signature:
            return format_html('<img src="{}" style="height:50px;"/>', obj.signature.url)
        return "No signature"
    signature_preview.short_description = "Signature"


# ---------- Director ----------
@admin.register(Director)
class DirectorAdmin(admin.ModelAdmin):
    list_display = ("name", "signature_preview")

    def has_add_permission(self, request):
        # ✅ Allow only 1 director (singleton)
        if Director.objects.exists():
            return False
        return True

    def signature_preview(self, obj):
        if obj.signature:
            return format_html('<img src="{}" style="height:50px;"/>', obj.signature.url)
        return "No signature"
    signature_preview.short_description = "Signature"
