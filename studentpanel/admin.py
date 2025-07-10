from datetime import datetime, date
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.db.models import F
from django.shortcuts import redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils.html import format_html

from .models import (
    StudentProfile, FeeChallan, Project, ProjectSelection,
    IDCard, Certificate
)

# ───────────────────────────────────────────────
FEE_AMOUNT = 2500
DUE_DAYS   = 7
# ───────────────────────────────────────────────


# ========== StudentProfile Admin ==========
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display    = ("student_name", "unique_id", "branch", "college", "is_selected", "payment_verified")
    list_filter     = ("branch", "is_selected", "payment_verified")
    search_fields   = ("student_name", "user__username", "unique_id")
    readonly_fields = ("unique_id",)
    exclude         = ("lor_file",)  # ⛔ removes "Choose File" for LOR

    def save_model(self, request, obj, form, change):
        first_select = obj.is_selected and not obj.unique_id
        super().save_model(request, obj, form, change)

        if first_select:
            year = datetime.now().year % 100
            seq  = StudentProfile.objects.filter(is_selected=True).exclude(pk=obj.pk).count() + 1
            obj.unique_id = f"STVT{year}/{seq:02d}"
            obj.save(update_fields=["unique_id"])
            FeeChallan.objects.get_or_create(student=obj)


# ========== FeeChallan Admin ==========
@admin.register(FeeChallan)
class FeeChallanAdmin(admin.ModelAdmin):
    list_display = ("student", "status", "created_on", "sent_on", "send_btn", "verify_btn")
    list_filter  = ("status",)

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


# ========== ProjectSelection Admin ==========
@admin.register(ProjectSelection)
class ProjectSelectionAdmin(admin.ModelAdmin):
    list_display = ("student", "project", "status", "action_btn")
    list_filter  = ("status", "project__branch")

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
    action_btn.allow_tags = True

    def _approve(self, request, pk):
        sel = get_object_or_404(ProjectSelection, pk=pk)
        if sel.status != "Pending":
            self.message_user(request, "Already processed.", level=messages.WARNING)
            return redirect("..")
        sel.status = "Approved"
        sel.save(update_fields=["status"])

        profile = sel.student
        if not hasattr(profile, 'certificate'):
            year = datetime.now().year % 100
            count = Certificate.objects.filter(serial_number__startswith=f"CERT{year}/").count() + 1
            serial = f"CERT{year}/{count:02d}"
            Certificate.objects.create(student=profile, serial_number=serial)

        self.message_user(request, "Project approved & certificate initialized.", level=messages.SUCCESS)
        return redirect("..")

    def _send_admit(self, request, pk):
        sel = get_object_or_404(ProjectSelection, pk=pk)
        if sel.status != "Approved":
            self.message_user(request, "Selection not approved yet.", level=messages.WARNING)
            return redirect("..")

        profile = sel.student
        project = sel.project
        ctx = {"profile": profile, "project": project}

        admit_html = render_to_string("studentpanel/admit_card.html", ctx)
        idcard, _ = IDCard.objects.get_or_create(student=profile)
        idcard.id_pdf.save(f"admit_{profile.unique_id}.html", ContentFile(admit_html.encode("utf-8")))
        idcard.save()

        dash_link = request.build_absolute_uri("/dashboard/?tab=admit")
        send_mail(
            "Batch Allotted – Download Your Admit Card",
            f"Dear {profile.student_name},\n\nYour batch has been confirmed. "
            f"Download your admit card from the dashboard:\n{dash_link}\n\nRegards,\nTraining Centre",
            settings.DEFAULT_FROM_EMAIL,
            [profile.user.email],
            fail_silently=True,
        )

        self.message_user(request, "Admit card generated & e-mailed.", level=messages.SUCCESS)
        return redirect("..")


# ========== Project Admin ==========
class ProjectAdminForm(forms.ModelForm):
    branch = forms.ChoiceField(choices=[])

    class Meta:
        model = Project
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        branches = (
            StudentProfile.objects
            .values_list("branch", flat=True)
            .distinct()
            .order_by("branch")
        )
        self.fields["branch"].choices = [(b, b) for b in branches]

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    form = ProjectAdminForm
    list_display = ("title", "branch", "duration_weeks", "slots", "slots_taken")
    list_filter = ("branch", "duration_weeks")
    search_fields = ("title", "teacher")


# ========== Certificate Admin ==========
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("student", "serial_number", "is_verified", "issued_on", "verify_btn", "send_btn")
    list_filter = ("is_verified",)
    readonly_fields = ("issued_on",)

    def verify_btn(self, obj):
        if not obj.is_verified:
            url = reverse("admin:verify_certificate", args=[obj.pk])
            return format_html('<a class="button" href="{}">Verify</a>', url)
        return "✔️"
    verify_btn.short_description = "Verify"

    def send_btn(self, obj):
        if obj.is_verified:
            url = reverse("admin:send_certificate", args=[obj.pk])
            return format_html('<a class="button" href="{}">Send</a>', url)
        return "-"
    send_btn.short_description = "Send"

    def get_urls(self):
        base = super().get_urls()
        extra = [
            path("verify/<int:pk>/", self.admin_site.admin_view(self._verify), name="verify_certificate"),
            path("send/<int:pk>/", self.admin_site.admin_view(self._send), name="send_certificate"),
        ]
        return extra + base

    def _verify(self, request, pk):
        cert = get_object_or_404(Certificate, pk=pk)
        cert.is_verified = True
        cert.save()
        self.message_user(request, "Certificate verified successfully.", level=messages.SUCCESS)
        return redirect("..")

    def _send(self, request, pk):
        cert = get_object_or_404(Certificate, pk=pk)
        if not cert.is_verified:
            self.message_user(request, "Certificate not verified.", level=messages.WARNING)
            return redirect("..")

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
            f"Dear {profile.student_name},\n\nYour certificate has been approved.\nDownload here:\n{link}\n\nRegards,\nSTC Charbagh",
            settings.DEFAULT_FROM_EMAIL,
            [profile.user.email],
            fail_silently=True,
        )

        self.message_user(request, "Certificate sent to student.", level=messages.SUCCESS)
        return redirect("..")


        

# ========== allow_tags ================
FeeChallanAdmin.send_btn.allow_tags = True
FeeChallanAdmin.verify_btn.allow_tags = True
ProjectSelectionAdmin.action_btn.allow_tags = True
