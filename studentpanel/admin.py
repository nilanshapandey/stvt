from datetime import datetime, date, timedelta

from django.contrib import admin, messages
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import StudentProfile, FeeChallan, Project, ProjectSelection, IDCard

# ── constants ──────────────────────────────────────
FEE_AMOUNT   = 2500
DUE_DAYS     = 7


# ── StudentProfile admin ───────────────────────────
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display    = ("student_name", "unique_id", "branch", "college", "is_selected", "payment_verified")
    list_filter     = ("branch", "is_selected", "payment_verified")
    search_fields   = ("student_name", "user__username", "unique_id")
    readonly_fields = ("unique_id",)

    def save_model(self, request, obj, form, change):
        first_time_select = obj.is_selected and not obj.unique_id
        super().save_model(request, obj, form, change)

        if first_time_select:
            # 1. create unique ID
            year_suffix = datetime.now().year % 100
            seq = (StudentProfile.objects
                   .filter(is_selected=True)
                   .exclude(pk=obj.pk)
                   .count() + 1)
            obj.unique_id = f"STVT{year_suffix}/{seq:02d}"
            obj.save(update_fields=["unique_id"])

            # 2. ensure FeeChallan row
            FeeChallan.objects.get_or_create(student=obj)

            # 3. notify student
            send_mail(
                "Selected for Summer Training – Challan coming soon",
                (
                    f"Dear {obj.student_name},\n\n"
                    "You have been verified for Summer Training.\n"
                    "An email with your fee challan link will arrive shortly.\n\n"
                    "Regards,\nTraining Centre"
                ),
                settings.DEFAULT_FROM_EMAIL,
                [obj.user.email],
                fail_silently=True,
            )

            self.message_user(
                request,
                f"{obj.student_name} verified; unique ID assigned & challan row created.",
                level=messages.SUCCESS,
            )


# ── FeeChallan admin: Generate & Send ───────────────
@admin.register(FeeChallan)
class FeeChallanAdmin(admin.ModelAdmin):
    list_display = ("student", "status", "created_on")
    list_filter  = ("status",)
    actions      = ["generate_and_send_challan"]

    def generate_and_send_challan(self, request, queryset):
        generated = 0
        for challan in queryset.filter(challan_pdf=""):
            profile = challan.student

            # HTML challan content
            html = render_to_string("studentpanel/challan.html", {
                "profile":  profile,
                "amount":   FEE_AMOUNT,
                "due_date": date.today() + timedelta(days=DUE_DAYS),
            })

            # Save as UTF‑8 bytes
            filename = f"challan_{profile.unique_id}.html"
            challan.challan_pdf.save(filename, ContentFile(html.encode("utf-8")))
            challan.status = "Pending"
            challan.save(update_fields=["challan_pdf", "status"])

            # dashboard link with ?tab=challan
            dash_url = request.build_absolute_uri("/dashboard/?tab=challan")

            # Email with button (HTML)
            body_html = render_to_string("studentpanel/email_challan.html", {
                "student": profile.student_name,
                "link":    dash_url,
            })

            send_mail(
                "Your Fee Challan is Ready",
                "",                                # plain text fall‑back
                settings.DEFAULT_FROM_EMAIL,
                [profile.user.email],
                html_message=body_html,
                fail_silently=True,
            )
            generated += 1

        self.message_user(
            request,
            f"{generated} challan(s) generated and emailed.",
            messages.SUCCESS,
        )

    generate_and_send_challan.short_description = "Generate & send challan (selected)"


# ── simple registrations ───────────────────────────
admin.site.register(Project)
admin.site.register(ProjectSelection)
admin.site.register(IDCard)
