# studentpanel/forms.py
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import F
from .models import StudentProfile, Project

ALLOWED_LOR_TYPES = ["application/pdf", "image/jpeg"]
MAX_LOR_SIZE_MB   = 2


# ---------- Registration ----------
class RegistrationForm(forms.ModelForm):
    username     = forms.CharField(max_length=30, label="Username")
    email        = forms.EmailField(label="Email")
    password     = forms.CharField(widget=forms.PasswordInput)
    confirm_pass = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    class Meta:
        model  = StudentProfile
        fields = [
            "student_name", "father_name", "college", "course", "branch",
            "address", "mobile", "photo", "lor_file",
        ]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, f in self.fields.items():
            # Add form-control to all except file and checkbox
            if not isinstance(f.widget, (forms.FileInput, forms.CheckboxInput)):
                existing = f.widget.attrs.get("class", "")
                f.widget.attrs["class"] = (existing + " form-control").strip()
            # Add form-check-input to checkboxes for AdminLTE
            if isinstance(f.widget, forms.CheckboxInput):
                existing = f.widget.attrs.get("class", "")
                f.widget.attrs["class"] = (existing + " form-check-input").strip()

    def clean_username(self):
        u = self.cleaned_data["username"]
        if User.objects.filter(username=u).exists():
            raise ValidationError("Username already taken.")
        return u

    def clean_email(self):
        e = self.cleaned_data["email"]
        if User.objects.filter(email=e).exists():
            raise ValidationError("Email already in use.")
        return e

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("confirm_pass"):
            self.add_error("confirm_pass", "Passwords do not match.")
        return cleaned

    def clean_lor_file(self):
        file = self.cleaned_data["lor_file"]
        if file.content_type not in ALLOWED_LOR_TYPES:
            raise ValidationError("Only PDF or JPG allowed.")
        if file.size > MAX_LOR_SIZE_MB * 1024 * 1024:
            raise ValidationError("File too large (max 2 MB).")
        return file

    def save(self, commit=True):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["username"],
            password=data["password"],
            email=data["email"],
        )
        profile = super().save(commit=False)
        profile.user = user
        if commit:
            profile.save()
        return profile


# ---------- Project request (inline) ----------
class ProjectRequestForm(forms.Form):
    project_id = forms.ModelChoiceField(
        queryset=Project.objects.none(),
        widget=forms.RadioSelect,
        empty_label=None,
        label="Choose one project",
    )

    def __init__(self, branch, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project_id"].queryset = (
            Project.objects
            .filter(branch=branch)
            .annotate(available=F("slots") - F("slots_taken"))
            .filter(available__gt=0)
        )
