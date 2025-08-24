# studentpanel/forms.py
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import F
from .models import StudentProfile, Project, BatchSlot
from .models import FeeChallan

# --------------- Registration Form ----------------
class RegistrationForm(forms.ModelForm):
    username     = forms.CharField(max_length=30, label="Username")
    email        = forms.EmailField(label="Email")
    password     = forms.CharField(widget=forms.PasswordInput)
    confirm_pass = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    class Meta:
        model = StudentProfile
        fields = [
            "student_name", "father_name", "college", "course", "branch",
            "address", "mobile", "photo",
        ]
        widgets = {
            "address": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Enter complete address with PIN code"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if not isinstance(field.widget, (forms.FileInput, forms.CheckboxInput)):
                field.widget.attrs["class"] = "form-control"
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
        self.fields['photo'].help_text = "Upload passport size photo (1MB to 5MB only)"

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
        pwd = cleaned.get("password")
        cpwd = cleaned.get("confirm_pass")
        if pwd and cpwd and pwd != cpwd:
            self.add_error("confirm_pass", "Passwords do not match.")
        return cleaned

    def clean_mobile(self):
        mob = self.cleaned_data["mobile"]
        if not mob.isdigit():
            raise ValidationError("Mobile number must contain digits only.")
        if len(mob) != 10:
            raise ValidationError("Mobile number must be 10 digits.")
        return mob

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo:
            if photo.size < 1 * 1024 * 1024:
                raise ValidationError("Image size must be at least 1MB.")
            if photo.size > 5 * 1024 * 1024:
                raise ValidationError("Image size must not exceed 5MB.")
        return photo

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

# --------------- Project Request Form ----------------
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






class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'project_code', 'title',  'incharge',
            'branch', 'batch_slot',
            'slots', 'slots_taken',
            'concerd_shop'
        ]




# --------------- Batch Slot Form ----------------
class BatchSlotForm(forms.Form):
    batch_slot = forms.ModelChoiceField(
        queryset=BatchSlot.objects.all(),
        label="Choose Batch Date",
        empty_label="Select date range",
        widget=forms.Select(attrs={"class": "form-control"})
    )

# forms.py
class TicketForm(forms.ModelForm):
    class Meta:
        model = FeeChallan
        fields = ["ticket_number"]