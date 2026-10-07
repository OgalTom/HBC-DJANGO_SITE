from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Application, Article, Job

User = get_user_model()


class LoginForm(AuthenticationForm):
    """
    Custom login form that accepts email OR username in the 'username' field.
    """
    username = forms.CharField(
        label="Email or Username",
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "you@example.com",
            "autocomplete": "username",
            "autofocus": True,
        }),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "••••••••",
            "autocomplete": "current-password",
        }),
    )

    def clean_username(self):
        value = self.cleaned_data.get("username", "").strip()
        # If it looks like an email, resolve to the actual username
        if "@" in value:
            try:
                user = User.objects.get(email__iexact=value)
                return user.username
            except User.DoesNotExist:
                raise forms.ValidationError("No account found with that email.")
        return value


class RegisterForm(UserCreationForm):
    """
    Registration form for the custom User model.
    Uses email + phone_number (both required, both unique).
    """
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Jane",
            "autocomplete": "given-name",
        }),
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Doe",
            "autocomplete": "family-name",
        }),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-input",
            "placeholder": "you@example.com",
            "autocomplete": "email",
        }),
    )
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "+254 7XX XXX XXX",
            "autocomplete": "tel",
        }),
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Create a password",
            "autocomplete": "new-password",
        }),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Repeat your password",
            "autocomplete": "new-password",
        }),
    )

    class Meta:
        model = User
        fields = (
            "first_name", "last_name", "email",
            "phone_number", "password1", "password2",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data["phone_number"].strip()
        if User.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError("An account with this phone number already exists.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.phone_number = self.cleaned_data["phone_number"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        # Default username = email (unique by UserCreationForm's validation)
        user.username = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "country",
            "city",
            "passport_number",
            "cv_summary",
            "bio",
        )
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Jane"}),
            "last_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Doe"}),
            "email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "you@example.com"}),
            "phone_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "+254 7XX XXX XXX"}),
            "country": forms.TextInput(attrs={"class": "form-input", "placeholder": "Kenya"}),
            "city": forms.TextInput(attrs={"class": "form-input", "placeholder": "Nairobi"}),
            "passport_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "P1234567"}),
            "cv_summary": forms.Textarea(attrs={"class": "form-input", "rows": 5, "placeholder": "Brief CV summary / experience overview"}),
            "bio": forms.Textarea(attrs={"class": "form-input", "rows": 4, "placeholder": "Short bio or candidate profile statement"}),
        }


class PlatformStaffForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=20, required=True)
    role = forms.ChoiceField(choices=User.Role.choices)

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone_number", "role", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data["phone_number"].strip()
        if User.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError("An account with this phone number already exists.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        user.phone_number = self.cleaned_data["phone_number"].strip()
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        user.username = self.cleaned_data["email"].strip().lower()
        user.is_staff = True
        user.role = self.cleaned_data["role"]
        if commit:
            user.save()
        return user


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = (
            "title",
            "slug",
            "category",
            "excerpt",
            "body",
            "featured_image",
            "image_alt",
            "author_name",
            "read_time",
            "status",
            "published_at",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "A story headline"}),
            "slug": forms.TextInput(attrs={"class": "form-input", "placeholder": "article-slug"}),
            "category": forms.Select(attrs={"class": "form-input"}),
            "excerpt": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Short summary shown in article cards"}),
            "body": forms.Textarea(attrs={"class": "form-input", "rows": 10, "placeholder": "Write the full article content here"}),
            "featured_image": forms.URLInput(attrs={"class": "form-input", "placeholder": "https://example.com/article-image.jpg"}),
            "image_alt": forms.TextInput(attrs={"class": "form-input", "placeholder": "Descriptive alt text"}),
            "author_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "HBC Job Majuu"}),
            "read_time": forms.TextInput(attrs={"class": "form-input", "placeholder": "4 min read"}),
            "status": forms.Select(attrs={"class": "form-input"}),
            "published_at": forms.DateTimeInput(attrs={"class": "form-input", "type": "datetime-local"}),
        }


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = (
            "title",
            "country",
            "country_flag",
            "sector",
            "description_masked",
            "description_full",
            "salary_disclosed",
            "salary_range",
            "tier_2_fee",
            "tier_3_fee",
            "status",
            "visibility",
            "cover_image",
            "image_url",
            "image_alt",
        )
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Senior ICU Nurse"}),
            "country": forms.TextInput(attrs={"placeholder": "Kenya"}),
            "country_flag": forms.TextInput(attrs={"placeholder": "🇰🇪 (auto-generated if left blank)"}),
            "sector": forms.TextInput(attrs={"placeholder": "Healthcare"}),
            "description_masked": forms.Textarea(attrs={"rows": 3, "placeholder": "Short candidate-facing summary"}),
            "description_full": forms.Textarea(attrs={"rows": 7, "placeholder": "Full job description, experience requirements, and responsibilities"}),
            "salary_range": forms.TextInput(attrs={"placeholder": "KES 250,000 – 350,000"}),
            "tier_2_fee": forms.NumberInput(attrs={"step": "0.01"}),
            "tier_3_fee": forms.NumberInput(attrs={"step": "0.01"}),
            "cover_image": forms.URLInput(attrs={"placeholder": "https://example.com/job-cover-image.jpg"}),
            "image_url": forms.URLInput(attrs={"placeholder": "https://example.com/job-image.jpg"}),
            "image_alt": forms.TextInput(attrs={"placeholder": "Hospital nurse role in Nairobi"}),
        }


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = (
            "current_country",
            "city",
            "passport_number",
            "years_of_experience",
            "cover_letter",
            "visa_readiness",
        )
        widgets = {
            "current_country": forms.TextInput(attrs={"class": "form-input", "placeholder": "Kenya"}),
            "city": forms.TextInput(attrs={"class": "form-input", "placeholder": "Nairobi"}),
            "passport_number": forms.TextInput(attrs={"class": "form-input", "placeholder": "P1234567"}),
            "years_of_experience": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
            "cover_letter": forms.Textarea(attrs={"class": "form-input", "rows": 6, "placeholder": "Tell us about your background and why you are interested in this role."}),
            "visa_readiness": forms.Select(attrs={"class": "form-input"}),
        }


class PartnerAssignmentForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ("assigned_agent", "ats_stage", "document_status", "visa_readiness", "admin_notes")
        widgets = {
            "ats_stage": forms.Select(attrs={"class": "form-input"}),
            "document_status": forms.Select(attrs={"class": "form-input"}),
            "visa_readiness": forms.Select(attrs={"class": "form-input"}),
            "admin_notes": forms.Textarea(attrs={"class": "form-input", "rows": 5}),
        }


class ApplicantReviewForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ("ats_stage", "document_status", "visa_readiness", "admin_notes")
        widgets = {
            "ats_stage": forms.Select(attrs={"class": "form-input"}),
            "document_status": forms.Select(attrs={"class": "form-input"}),
            "visa_readiness": forms.Select(attrs={"class": "form-input"}),
            "admin_notes": forms.Textarea(attrs={"class": "form-input", "rows": 5}),
        }
