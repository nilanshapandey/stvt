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

    address         = models.TextField()
    mobile          = models.CharField(max_length=15)

    photo           = models.ImageField(upload_to=photo_upload_path)
    lor_file        = models.FileField(upload_to=lor_upload_path)

    is_selected     = models.BooleanField(default=False)
    payment_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student_name} ({self.unique_id or 'Unassigned'})"

#--------------------------
# Fee Challan   (updated)
# ───────────────────────────────
class FeeChallan(models.Model):
    student        = models.OneToOneField(StudentProfile, on_delete=models.CASCADE)
    challan_pdf    = models.FileField(upload_to="challans/", blank=True, null=True)

    STATUS_CHOICES = [
        ("Pending",   "Pending"),   # created but not sent
        ("Sent",      "Sent"),      # e‑mail sent to student
        ("Submitted", "Submitted"), # student uploaded receipt
        ("Verified",  "Verified"),  # admin accepted payment
    ]
    status         = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")

    sent_on        = models.DateTimeField(null=True, blank=True)   # when e‑mail sent
    created_on     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Challan for {self.student.student_name} – {self.status}"


# ───────────────────────────────
# Project Master
# ───────────────────────────────
class Project(models.Model):
    branch          = models.CharField(max_length=50)
    duration_weeks  = models.PositiveIntegerField(choices=[(4, "4 Weeks"), (6, "6 Weeks")])
    title           = models.CharField(max_length=150)
    teacher         = models.CharField(max_length=100)
    start_date      = models.DateField()
    end_date        = models.DateField()
    slots           = models.PositiveIntegerField()
    slots_taken     = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.title} ({self.branch}, {self.duration_weeks}W)"

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
# ID Slip / Admit Card
# ───────────────────────────────
class IDCard(models.Model):
    student    = models.OneToOneField(StudentProfile, on_delete=models.CASCADE)
    id_pdf     = models.FileField(upload_to='idcards/')
    issued_on  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ID Slip for {self.student.student_name}"
# models.py



class Certificate(models.Model):
    student = models.OneToOneField(StudentProfile, on_delete=models.CASCADE)
    certificate_pdf = models.FileField(upload_to='certificates/', blank=True, null=True)
    serial_number = models.CharField(max_length=20, unique=True)
    is_verified = models.BooleanField(default=False)
    issued_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Certificate for {self.student.student_name}"
