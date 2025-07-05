# studentpanel/forms.py
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import StudentProfile

ALLOWED_LOR_TYPES = ["application/pdf", "image/jpeg"]
MAX_LOR_SIZE_MB = 2

class RegistrationForm(forms.ModelForm):
    # ---------- User fields ----------
    username     = forms.CharField(max_length=30, label="Username")
    email        = forms.EmailField(label="Email")
    password     = forms.CharField(widget=forms.PasswordInput)
    confirm_pass = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    class Meta:
        model  = StudentProfile
        fields = [
            "student_name",
            "father_name",
            "college",
            "course",
            "branch",
            "address",
            "mobile",
            "photo",
            "lor_file",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    # ---------- add Bootstrap .form-control to inputs ----------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            # Skip file & checkbox widgets, everything else gets form-control
            if not isinstance(field.widget, (forms.FileInput, forms.CheckboxInput)):
                existing = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = (existing + " form-control").strip()

    # ---------- validation ----------
    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise ValidationError("Username already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email already in use.")
        return email

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

    # ---------- save ----------
    def save(self, commit=True):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["username"],
            password=data["password"],
            email=data["email"],
            first_name="",
            last_name="",
        )
        profile = super().save(commit=False)
        profile.user = user
        if commit:
            profile.save()
        return profile
