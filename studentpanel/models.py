from django.db import models
from django.contrib.auth.models import User
import os

# ───────────────────────────────
# File Upload Helpers
# ───────────────────────────────
def lor_upload_path(instance, filename):
    return os.path.join("lor", f"{instance.user.username}_{filename}")

def photo_upload_path(instance, filename):
    return os.path.join("photos", f"{instance.user.username}_{filename}")

# ───────────────────────────────
# Student Profile
# ───────────────────────────────
class StudentProfile(models.Model):
    user            = models.OneToOneField(User, on_delete=models.CASCADE)

    student_name    = models.CharField(max_length=100)
    father_name     = models.CharField(max_length=100)

    unique_id       = models.CharField(max_length=20, unique=True, blank=True)
    college         = models.CharField(max_length=150)
    course          = models.CharField(max_length=50)
    branch          = models.CharField(max_length=50)

    address         = models.TextField(help_text="Address with Pincode")
    mobile          = models.CharField(max_length=10, help_text="Only 10-digit mobile number")

    photo           = models.ImageField(upload_to=photo_upload_path, help_text="Upload photo (1MB max)")
    lor_file        = models.FileField(upload_to=lor_upload_path)

    is_selected     = models.BooleanField(default=False)
    payment_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student_name} ({self.unique_id or 'Unassigned'})"


# ───────────────────────────────
# Batch Slot Model (New)
# ───────────────────────────────

class BatchSlot(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    duration_weeks = models.IntegerField()

    def __str__(self):
        return f"{self.start_date} to {self.end_date} ({self.duration_weeks} weeks)"

# ───────────────────────────────
# Project Master
# ───────────────────────────────
# models.py
# studentpanel/models.py

class Project(models.Model):
    project_code = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    branch = models.CharField(max_length=50)
    teacher = models.CharField(max_length=100)
    slots = models.PositiveIntegerField()
    slots_taken = models.PositiveIntegerField(default=0)
    batch_slot = models.ForeignKey('BatchSlot', on_delete=models.CASCADE)
    duration_weeks = models.PositiveIntegerField()

    def save(self, *args, **kwargs):
        if self.batch_slot:
            self.duration_weeks = self.batch_slot.duration_weeks
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.project_code} - {self.title}"


# ───────────────────────────────
# Student’s Selected Project
# ───────────────────────────────
class ProjectSelection(models.Model):
    student     = models.OneToOneField(StudentProfile, on_delete=models.CASCADE)
    project     = models.ForeignKey(Project, on_delete=models.PROTECT)
    
    status = models.CharField(
        max_length=15,
        choices=[
            ('Pending', 'Pending'),
            ('Approved', 'Approved')
        ],
        default='Pending'
    )

    selected_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.student_name} → {self.project.title}"


# ───────────────────────────────
# Fee Challan
# ───────────────────────────────
class FeeChallan(models.Model):
    student        = models.OneToOneField(StudentProfile, on_delete=models.CASCADE)
    challan_pdf    = models.FileField(upload_to="challans/", blank=True, null=True)

    STATUS_CHOICES = [
        ("Pending",   "Pending"),
        ("Sent",      "Sent"),
        ("Submitted", "Submitted"),
        ("Verified",  "Verified"),
    ]
    status         = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")

    sent_on        = models.DateTimeField(null=True, blank=True)
    created_on     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Challan for {self.student.student_name} – {self.status}"


# ───────────────────────────────
# ID Slip / Admit Card
# ───────────────────────────────
class IDCard(models.Model):
    student    = models.OneToOneField(StudentProfile, on_delete=models.CASCADE)
    id_pdf     = models.FileField(upload_to='idcards/')
    issued_on  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ID Slip for {self.student.student_name}"


# ───────────────────────────────
# Certificate Model
# ───────────────────────────────
class Certificate(models.Model):
    student = models.OneToOneField(StudentProfile, on_delete=models.CASCADE)
    certificate_pdf = models.FileField(upload_to='certificates/', blank=True, null=True)
    serial_number = models.CharField(max_length=20, unique=True)
    is_verified = models.BooleanField(default=False)
    issued_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Certificate for {self.student.student_name}"


temp_dummy = models.CharField(max_length=10, null=True, blank=True)